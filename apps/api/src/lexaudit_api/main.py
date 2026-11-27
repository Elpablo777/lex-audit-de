"""FastAPI REST- und SSE-Backend für LexAudit DE/EU."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from datetime import date
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from lexaudit_analyzer.actions import LegislativeBriefingGenerator, PetitionGenerator
from lexaudit_analyzer.assistant import LegalResearchAssistant
from lexaudit_analyzer.pipeline import AuditPipeline
from lexaudit_analyzer.z3_models import (
    analyze_erbstg_cliff_z3,
    analyze_transfer_withdrawal_z3,
    simulate_erbstg_burden,
    simulate_household_curve,
)
from lexaudit_core.config import (
    AI_TRANSPARENCY_NOTICE_DE,
    BVERFG_2025_STATS,
    LexAuditSettings,
    get_settings,
)
from lexaudit_core.guardrails import RDGViolationBlockedError
from lexaudit_core.schemas import (
    AssistantQuery,
    AssistantResponse,
    ConflictFinding,
    LegislativeBriefing,
    PetitionDraft,
    PetitionTargetPortal,
)
from lexaudit_pipelines.connectors import (
    AbgeordnetenwatchConnector,
    EURLexSPARQLConnector,
    HUDOCConnector,
    NeuRISConnector,
    NiedersachsenVerkuendungConnector,
    OpenLegalDataConnector,
)
from lexaudit_pipelines.state_connectors import STATE_PORTAL_REGISTRY, DNGOpenDataRequestGenerator
from pydantic import BaseModel, ConfigDict, Field

from lexaudit_api.state import AppRuntime, create_runtime


class PetitionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    finding_id: str
    target_portal: PetitionTargetPortal = PetitionTargetPortal.BUNDESTAG_PETITION
    population_scope: int | None = Field(default=None, ge=100, le=100_000_000)
    custom_text: str | None = None


class DNGRequestPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recipient_authority: str | None = None


def create_app(
    settings: LexAuditSettings | None = None, *, in_memory: bool = False
) -> FastAPI:
    cfg = settings or get_settings()
    runtime_holder: dict[str, AppRuntime] = {}

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        runtime_holder["rt"] = create_runtime(cfg, in_memory=in_memory)
        yield

    app = FastAPI(
        title="LexAudit DE/EU API",
        version="0.1.0",
        description=(
            "Föderales Rechts-Audit- & Demokratie-Portal API (bitemporaler Wissensgraph, "
            "Z3 SMT Solver, CitationVerifier, Petitions- & Abgeordneten-Router)."
        ),
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:3000",
            "http://localhost:3000",
            "http://127.0.0.1:3001",
            "http://localhost:3001",
        ],
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
    )

    def _rt() -> AppRuntime:
        if "rt" not in runtime_holder:
            runtime_holder["rt"] = create_runtime(cfg, in_memory=in_memory)
        return runtime_holder["rt"]

    @app.get("/")
    def get_api_root() -> dict[str, str]:
        return {
            "service": "LexAudit DE/EU API",
            "status": "ok",
            "hinweis": "Dies ist das FastAPI-Backend. Die Web-Oberfläche läuft auf http://127.0.0.1:3000.",
            "portal_url": "http://127.0.0.1:3000",
            "docs_url": "/docs",
            "health_url": "/api/v1/health",
        }

    @app.get("/api/v1/health")
    def get_health() -> dict[str, Any]:
        rt = _rt()
        snap = rt.graph.snapshot(as_of=date(2026, 11, 27))
        return {
            "status": "ok",
            "corpus_stats": rt.corpus_stats,
            "graph_stats": snap.stats,
            "verified_findings_count": len(rt.storage.list_findings(include_rejected=False)),
            "bverfg_2025": BVERFG_2025_STATS,
            "ai_transparency_notice": AI_TRANSPARENCY_NOTICE_DE,
            "llm_mode": "openrouter-live" if rt.settings.openrouter_api_key else "deterministic-offline",
        }

    @app.get("/api/v1/findings", response_model=list[ConflictFinding])
    def list_findings(
        legal_domain: str | None = None,
        conflict_class: int | None = Query(default=None, ge=1, le=5),
    ) -> list[ConflictFinding]:
        rt = _rt()
        # Niemals REJECTED_UNVERIFIED ans Frontend ausliefern!
        items = rt.storage.list_findings(include_rejected=False)
        if legal_domain and legal_domain != "all":
            items = [f for f in items if f.legal_domain.lower() == legal_domain.lower()]
        if conflict_class is not None:
            items = [f for f in items if int(f.conflict_class) == conflict_class]
        return items

    @app.get("/api/v1/findings/{finding_id}")
    def get_finding_detail(finding_id: str) -> dict[str, Any]:
        rt = _rt()
        finding = rt.storage.get_finding(finding_id)
        if not finding or finding.verification_status.value != "VERIFIED":
            raise HTTPException(status_code=404, detail="Verifizierter Befund nicht gefunden.")
        norm_texts: list[dict[str, str]] = []
        for ref_id in finding.legal_chain_ids:
            lookup = rt.storage.lookup_full_text(ref_id, as_of=date(2026, 11, 27))
            if lookup:
                full_text, src_url, eli_or_ecli, status = lookup
                norm_texts.append(
                    {
                        "ref_id": ref_id,
                        "eli_or_ecli": eli_or_ecli,
                        "status": status,
                        "source_url": src_url,
                        "full_text": full_text,
                    }
                )
        briefing = LegislativeBriefingGenerator.build_briefing(
            finding, reference_date=date(2026, 11, 27)
        )
        return {
            "finding": finding.model_dump(mode="json"),
            "norm_texts": norm_texts,
            "briefing": briefing.model_dump(mode="json"),
        }

    @app.get("/api/v1/graph")
    def get_graph_snapshot(
        as_of: date | None = None,
        jurisdiction_level: str | None = None,
        legal_domain: str | None = None,
    ) -> dict[str, Any]:
        rt = _rt()
        findings = rt.storage.list_findings(include_rejected=False)
        conflict_ids = {nid for f in findings for nid in f.legal_chain_ids}
        snap = rt.graph.snapshot(
            as_of=as_of or date(2026, 11, 27),
            jurisdiction_level=jurisdiction_level,
            legal_domain=legal_domain,
            conflict_norm_ids=conflict_ids,
        )
        return snap.model_dump(mode="json")

    @app.post("/api/v1/audits/run")
    def trigger_audit_run() -> dict[str, Any]:
        rt = _rt()
        pipeline = AuditPipeline(storage=rt.storage, graph=rt.graph, settings=rt.settings)
        run, findings, events = pipeline.run_audit(as_of=date(2026, 11, 27), persist=True)
        rt.last_run = run
        rt.findings = findings
        return {
            "run": run.model_dump(mode="json"),
            "findings_count": len(findings),
            "events": [e.__dict__ for e in events],
        }

    @app.get("/api/v1/audits/stream")
    def stream_audit() -> StreamingResponse:
        rt = _rt()
        pipeline = AuditPipeline(storage=rt.storage, graph=rt.graph, settings=rt.settings)

        def _event_gen() -> Iterator[str]:
            for ev in pipeline.stream_audit_events(as_of=date(2026, 11, 27)):
                payload = json.dumps(ev.__dict__, ensure_ascii=False)
                yield f"event: audit\ndata: {payload}\n\n"

        return StreamingResponse(_event_gen(), media_type="text/event-stream")

    @app.get("/api/v1/z3/household")
    def simulate_household_z3(
        rent: float = Query(default=850.0, ge=200.0, le=2500.0),
        children: int = Query(default=2, ge=0, le=6),
        threshold_pct: float = Query(default=100.0, ge=50.0, le=120.0),
    ) -> dict[str, Any]:
        proof = analyze_transfer_withdrawal_z3(
            rent=rent, children=children, threshold_pct=threshold_pct
        )
        curve = [pt.__dict__ for pt in simulate_household_curve(rent=rent, children=children)]
        return {"z3_proof": proof.model_dump(mode="json"), "curve": curve}

    @app.get("/api/v1/z3/erbstg")
    def simulate_erbstg_z3(
        business_assets_mio: float = Query(default=120.0, ge=1.0, le=500.0),
        private_assets_mio: float = Query(default=2.0, ge=0.0, le=100.0),
    ) -> dict[str, Any]:
        proof = analyze_erbstg_cliff_z3(private_assets_mio=private_assets_mio)
        point = simulate_erbstg_burden(
            business_assets_mio, private_assets_mio=private_assets_mio
        )
        curve = [
            simulate_erbstg_burden(float(v), private_assets_mio=private_assets_mio)
            for v in [5, 15, 26, 35, 50, 75, 90, 120, 250]
        ]
        return {
            "z3_proof": proof.model_dump(mode="json"),
            "selected_point": point,
            "curve": curve,
        }

    @app.post("/api/v1/actions/petition", response_model=PetitionDraft)
    def generate_petition(req: PetitionRequest) -> PetitionDraft:
        rt = _rt()
        finding = rt.storage.get_finding(req.finding_id)
        if not finding:
            raise HTTPException(status_code=404, detail="Befund nicht gefunden.")
        return PetitionGenerator.build_from_finding(
            finding,
            target_portal=req.target_portal,
            population_scope=req.population_scope,
            custom_text=req.custom_text,
        )

    @app.get("/api/v1/actions/representatives")
    def route_representatives(
        postal_code: str = Query(default="30159", min_length=4, max_length=10),
        legal_domain: str = Query(default="Sozialrecht"),
        finding_id: str | None = None,
        live: bool = Query(default=False),
    ) -> dict[str, Any]:
        rt = _rt()
        connector = AbgeordnetenwatchConnector()
        reps = connector.lookup_representatives(
            postal_code=postal_code,
            legal_domain=legal_domain,
            offline=not live or rt.settings.offline_demo,
        )
        finding = rt.storage.get_finding(finding_id) if finding_id else None
        finding_summary = (
            finding.plain_language_summary
            if finding
            else "Systemische Normkollisionen im Bereich " + legal_domain
        )
        letter_template = (
            f"Sehr geehrte Damen und Herren Abgeordnete (Wahlkreis PLZ {postal_code}),\n\n"
            f"als Bürgerin bzw. Bürger wende ich mich mit einer sachlichen Anregung zum Bereich "
            f"{legal_domain} an Sie und die zuständigen Fachausschüsse.\n\n"
            f"Sachverhalt (auf Basis verifizierter amtlicher Quellen): {finding_summary}\n\n"
            f"Bitte prüfen Sie eine parlamentarische Initiative bzw. Ausschussberatung zur Behebung "
            f"dieser Regelungslücke.\n\n"
            f"Mit freundlichen Grüßen\n[Ihr Name / PLZ {postal_code}]\n\n"
            f"---\n{AI_TRANSPARENCY_NOTICE_DE}"
        )
        return {
            "postal_code": postal_code,
            "legal_domain": legal_domain,
            "representatives": reps,
            "letter_template": letter_template,
        }

    @app.get("/api/v1/actions/briefing/{finding_id}", response_model=LegislativeBriefing)
    def get_legislative_briefing(finding_id: str) -> LegislativeBriefing:
        rt = _rt()
        finding = rt.storage.get_finding(finding_id)
        if not finding:
            raise HTTPException(status_code=404, detail="Befund nicht gefunden.")
        return LegislativeBriefingGenerator.build_briefing(
            finding, reference_date=date(2026, 11, 27)
        )

    @app.get("/api/v1/states")
    def list_federal_states() -> list[dict[str, Any]]:
        return [desc.model_dump(mode="json") for desc in STATE_PORTAL_REGISTRY.values()]

    @app.post("/api/v1/states/{land_code}/dng-request")
    def create_dng_request(land_code: str, payload: DNGRequestPayload) -> dict[str, str]:
        code = land_code.upper()
        if code not in STATE_PORTAL_REGISTRY:
            raise HTTPException(status_code=404, detail="Unbekanntes Bundesland.")
        text = DNGOpenDataRequestGenerator.generate_dng_request(
            code, recipient_authority=payload.recipient_authority
        )
        return {"land_code": code, "dng_request_text": text}

    @app.get("/api/v1/sources/live-probe")
    def probe_live_sources() -> dict[str, Any]:
        """Prüft auf expliziten Aufruf die Erreichbarkeit der amtlichen Open-Data-Schnittstellen."""
        report: dict[str, Any] = {}
        try:
            items = NeuRISConnector().fetch_legislation(limit=1)
            report["neuris_legislation"] = {"ok": True, "sample": items[0].get("name") if items else ""}
        except Exception as exc:
            report["neuris_legislation"] = {"ok": False, "error": str(exc)}

        try:
            cases = NeuRISConnector().fetch_rechtsprechung(limit=1)
            report["neuris_rechtsprechung"] = {"ok": True, "sample": cases[0].get("headline") if cases else ""}
        except Exception as exc:
            report["neuris_rechtsprechung"] = {"ok": False, "error": str(exc)}

        try:
            ni = NiedersachsenVerkuendungConnector().search("Dünge", size=1)
            report["verkuendung_niedersachsen"] = {"ok": True, "count": len(ni)}
        except Exception as exc:
            report["verkuendung_niedersachsen"] = {"ok": False, "error": str(exc)}

        try:
            aw = AbgeordnetenwatchConnector().fetch_parliaments(limit=2)
            report["abgeordnetenwatch_v2"] = {"ok": True, "count": len(aw)}
        except Exception as exc:
            report["abgeordnetenwatch_v2"] = {"ok": False, "error": str(exc)}

        try:
            oldp = OpenLegalDataConnector().fetch_courts(limit=1)
            report["open_legal_data"] = {"ok": True, "sample": oldp[0].get("name") if oldp else ""}
        except Exception as exc:
            report["open_legal_data"] = {"ok": False, "error": str(exc)}

        try:
            eu = EURLexSPARQLConnector().fetch_works(limit=1)
            report["eurlex_sparql"] = {"ok": True, "sample": eu[0].get("celex") if eu else ""}
        except Exception as exc:
            report["eurlex_sparql"] = {"ok": False, "error": str(exc)}

        try:
            hudoc = HUDOCConnector().search_germany_judgments(limit=1)
            report["hudoc_egmr"] = {"ok": True, "sample": hudoc[0].get("docname") if hudoc else ""}
        except Exception as exc:
            report["hudoc_egmr"] = {"ok": False, "error": str(exc)}

        return report

    @app.post("/api/v1/assistant/query", response_model=AssistantResponse)
    def query_assistant(req: AssistantQuery) -> AssistantResponse:
        rt = _rt()
        assistant = LegalResearchAssistant(
            storage=rt.storage, graph=rt.graph, settings=rt.settings
        )
        try:
            return assistant.answer_query(req)
        except RDGViolationBlockedError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc

    return app


app = create_app()
