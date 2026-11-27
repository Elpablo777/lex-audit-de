"""Phase 5: Vernetzter Jura-Recherche-Assistent (Modus A Bürger-Kompass & Modus B B2B-Copilot § 3 BRAO)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date

from lexaudit_core.config import AI_TRANSPARENCY_NOTICE_DE, LexAuditSettings, get_settings
from lexaudit_core.guardrails import (
    BudgetAndRateLimitGuard,
    RDGComplianceGuard,
    RDGViolationBlockedError,
)
from lexaudit_core.llm_clients import CitizenPrivacyLLMClient
from lexaudit_core.schemas import (
    AssistantMode,
    AssistantQuery,
    AssistantResponse,
    CitationProof,
    VerificationStatus,
)
from lexaudit_core.storage import SQLiteStorageBackend
from lexaudit_graph.repository import GraphRepository

from lexaudit_analyzer.citation_verifier import CitationVerifier


@dataclass
class LegalResearchAssistant:
    """Dual-Mode GraphRAG-Assistent mit striktem RDG-Guardrail, ZDR & CitationVerifier."""

    storage: SQLiteStorageBackend
    graph: GraphRepository
    settings: LexAuditSettings = field(default_factory=get_settings)
    guard: BudgetAndRateLimitGuard = field(default_factory=BudgetAndRateLimitGuard)

    def answer_query(self, request: AssistantQuery) -> AssistantResponse:
        ref_date = request.as_of_date or date(2026, 11, 27)

        # Modus A (Öffentlicher Bürger-Rechtskompass): harter RDG-Guardrail vor jeder Verarbeitung!
        if request.mode == AssistantMode.MODE_A_PUBLIC_COMPASS:
            rdg = RDGComplianceGuard.evaluate_query(request.query)
            if not rdg.allowed_abstract:
                return AssistantResponse(
                    mode=request.mode,
                    rdg_blocked=True,
                    rdg_reason=rdg.reason,
                    answer=(
                        f"{rdg.referral_text}\n\n"
                        "Sie können jedoch abstrakte Normzusammenhänge (z. B. ‚Wie wirken § 11b SGB II und "
                        "§ 19 WoGG systemisch zusammen?‘) oder verifizierte Konfliktfelder abfragen."
                    ),
                    citations=[],
                    verification_status=VerificationStatus.VERIFIED,
                    privacy_transport="rdg-local-guardrail",
                    ai_transparency_notice=AI_TRANSPARENCY_NOTICE_DE,
                )
        elif not request.brao_supervised_confirmed:
            raise RDGViolationBlockedError(
                "Modus B (Jura-Research-Copilot) setzt bestätigte anwaltliche bzw. volljuristische "
                "Eigenverantwortung nach § 3 BRAO voraus."
            )

        # Hybrid-Retrieval aus lokalem Volltextspiegel + Graph-Kontext
        hits = self.storage.hybrid_search(request.query, limit=4)
        verifier = CitationVerifier(self.storage)
        verified_citations: list[CitationProof] = []
        fulltext_snippets: list[str] = []

        for h in hits:
            ref_id = h.parent_id.split("@")[0] if hasattr(h, "parent_id") else h.item_id.split("@")[0]
            lookup = self.storage.lookup_full_text(ref_id, as_of=ref_date)
            if not lookup:
                continue
            full_text, src_url, eli_or_ecli, status = lookup
            proof = verifier.verify_citation(
                CitationProof(
                    citation_id=f"asst_{uuid.uuid4().hex[:8]}",
                    norm_or_ecli_ref=ref_id,
                    eli_or_ecli=eli_or_ecli,
                    norm_location=ref_id,
                    as_of_date=ref_date,
                    source_url=src_url,
                    quoted_excerpt=full_text[:140],
                    status_at_date=status,
                )
            )
            if proof.verified and all(p.norm_or_ecli_ref != proof.norm_or_ecli_ref for p in verified_citations):
                verified_citations.append(proof)
                fulltext_snippets.append(f"{ref_id} ({eli_or_ecli}): {full_text[:320]}")

        # Fallback falls sehr generische Anfrage -> Kernnorm aus dem Spiegel zitieren
        if not verified_citations:
            fallback_ref = "de:bund:gg:art_3"
            lookup = self.storage.lookup_full_text(fallback_ref, as_of=ref_date)
            if lookup:
                ft, src, eli, st = lookup
                proof = verifier.verify_citation(
                    CitationProof(
                        citation_id=f"asst_{uuid.uuid4().hex[:8]}",
                        norm_or_ecli_ref=fallback_ref,
                        eli_or_ecli=eli,
                        norm_location=fallback_ref,
                        as_of_date=ref_date,
                        source_url=src,
                        quoted_excerpt=ft[:120],
                        status_at_date=st,
                    )
                )
                if proof.verified:
                    verified_citations.append(proof)
                    fulltext_snippets.append(f"{fallback_ref}: {ft[:280]}")

        graph_paths: list[str] = []
        if request.mode == AssistantMode.MODE_B_RESEARCH_COPILOT and verified_citations:
            for c in verified_citations[:2]:
                paths = self.graph.trace_stufenbau(c.norm_or_ecli_ref, max_hops=4)
                for p in paths[:2]:
                    graph_paths.append(" -> ".join(p))

        stufenbau_info = (
            "\n\nStufenbau-Normketten (§ 3 BRAO Copilot):\n- " + "\n- ".join(graph_paths)
            if graph_paths
            else ""
        )
        fallback_answer = (
            "Abstrakte Systemauskunft auf Basis deterministisch verifizierter Primärquellen:\n\n"
            + "\n\n".join(fulltext_snippets)
            + stufenbau_info
        )

        # Strikt ZDR-geschützte Verarbeitung über CitizenPrivacyLLMClient!
        privacy_client = CitizenPrivacyLLMClient(settings=self.settings, guard=self.guard)
        llm_out = privacy_client.complete_citizen_query(
            system_prompt=(
                "Beantworte abstrakt auf Basis der geprüften Normtexte; keine Einzelfall-Rechtsberatung."
            ),
            user_query=f"Frage: {request.query}\nKontext:\n{fallback_answer}",
            offline_fallback_response=fallback_answer,
        )

        all_verified = bool(verified_citations) and all(c.verified for c in verified_citations)
        return AssistantResponse(
            mode=request.mode,
            rdg_blocked=False,
            answer=llm_out.content,
            citations=verified_citations,
            verification_status=(
                VerificationStatus.VERIFIED if all_verified else VerificationStatus.REJECTED_UNVERIFIED
            ),
            privacy_transport=llm_out.provider_mode,
            ai_transparency_notice=AI_TRANSPARENCY_NOTICE_DE,
        )
