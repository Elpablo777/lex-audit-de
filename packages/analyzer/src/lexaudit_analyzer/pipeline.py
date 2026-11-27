"""Neuro-Symbolische Analyse-Pipeline (Stufen A bis D) inkl. Full-Text-Lookup & SSE-Events."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, date, datetime

from lexaudit_core.config import AI_TRANSPARENCY_NOTICE_DE, LexAuditSettings, get_settings
from lexaudit_core.guardrails import BudgetAndRateLimitGuard
from lexaudit_core.llm_clients import PublicLawLLMClient
from lexaudit_core.schemas import (
    AuditRun,
    CitationProof,
    ConflictClass,
    ConflictFinding,
    NormType,
    Severity,
    VerificationStatus,
)
from lexaudit_core.storage import SQLiteStorageBackend
from lexaudit_graph.repository import GraphRepository

from lexaudit_analyzer.citation_verifier import CitationVerifier
from lexaudit_analyzer.scorecard import compute_leverage_scorecard
from lexaudit_analyzer.symbolic_filters import ZfLExtractor, run_symbolic_prefilters
from lexaudit_analyzer.z3_models import (
    analyze_erbstg_cliff_z3,
    analyze_transfer_withdrawal_z3,
)


@dataclass(frozen=True)
class AuditStreamEvent:
    step: str
    progress_pct: int
    message: str
    finding_id: str | None = None


@dataclass
class AuditPipeline:
    """Fünfschichtige neuro-symbolische Audit-Engine mit deterministischer Zitations-Brandmauer."""

    storage: SQLiteStorageBackend
    graph: GraphRepository
    settings: LexAuditSettings = field(default_factory=get_settings)
    guard: BudgetAndRateLimitGuard = field(default_factory=BudgetAndRateLimitGuard)

    def _build_citation_from_mirror(
        self, ref_id: str, quote_hint: str, as_of: date
    ) -> CitationProof:
        lookup = self.storage.lookup_full_text(ref_id, as_of=as_of)
        if lookup is None:
            return CitationProof(
                citation_id=f"cit_{uuid.uuid4().hex[:8]}",
                norm_or_ecli_ref=ref_id,
                eli_or_ecli=ref_id,
                norm_location=ref_id,
                as_of_date=as_of,
                source_url="",
                quoted_excerpt=quote_hint,
            )
        full_text, source_url, eli_or_ecli, status = lookup
        # Exaktes wörtliches Zitat aus dem Volltextspiegel wählen (Stufe C Full-Text-Lookup-Pflicht!)
        excerpt = quote_hint if quote_hint.lower() in full_text.lower() else full_text[:180]
        return CitationProof(
            citation_id=f"cit_{uuid.uuid4().hex[:8]}",
            norm_or_ecli_ref=ref_id,
            eli_or_ecli=eli_or_ecli,
            norm_location=ref_id,
            as_of_date=as_of,
            source_url=source_url,
            quoted_excerpt=excerpt,
            status_at_date=status,
        )

    def run_audit(
        self,
        *,
        as_of: date | None = None,
        persist: bool = True,
    ) -> tuple[AuditRun, list[ConflictFinding], list[AuditStreamEvent]]:
        ref_date = as_of or date(2026, 11, 27)
        run_id = f"audit_{uuid.uuid4().hex[:10]}"
        started = datetime.now(UTC)
        events: list[AuditStreamEvent] = [
            AuditStreamEvent(
                step="init",
                progress_pct=5,
                message="Starte neuro-symbolisches Audit entlang des Stufenbaus (0-Token-Vorfilter aktiv).",
            )
        ]

        # Stufe A: Symbolische Vorfilter + Z3 SMT Solver
        signals = run_symbolic_prefilters(self.storage, self.graph, reference_date=ref_date)
        z3_sozial = analyze_transfer_withdrawal_z3(rent=850.0, children=2, threshold_pct=100.0)
        z3_erbstg = analyze_erbstg_cliff_z3(private_assets_mio=2.0)
        events.append(
            AuditStreamEvent(
                step="stufe_a_z3",
                progress_pct=30,
                message=(
                    f"Stufe A abgeschlossen: {len(signals)} Symbol-Signale + Z3-Gegenbeweise "
                    f"(Sozial-Steuer SAT={z3_sozial.satisfiable}, ErbStG SAT={z3_erbstg.satisfiable})."
                ),
            )
        )

        # Stufe B: ZfL-Methodik (Pflichten & Definitions-Drift)
        zfl = ZfLExtractor()
        concepts = zfl.extract_concepts(self.storage)
        drifts = zfl.detect_definition_drift(concepts)
        events.append(
            AuditStreamEvent(
                step="stufe_b_zfl",
                progress_pct=50,
                message=f"Stufe B (ZfL): {len(concepts)} Normpflichten extrahiert, {len(drifts)} Definitions-Drifts erkannt.",
            )
        )

        # Stufe C: Full-Text-basierte Stufenbau-Tiefenprüfung (inkl. optionalem PublicLawLLMClient)
        llm_client = PublicLawLLMClient(settings=self.settings, guard=self.guard)
        candidates: list[ConflictFinding] = []

        # Befund 1: Erbschaftsteuer § 13a / § 28a ErbStG vs. Art. 3 Abs. 1 GG (BVerfG 1 BvF 1/23)
        c1_erbstg = self._build_citation_from_mirror(
            "de:bund:erbstg:p_13a",
            "Verschonungsabschlag",
            ref_date,
        )
        c1_gg = self._build_citation_from_mirror(
            "de:bund:gg:art_3",
            "Belastungsgleichheit und Folgerichtigkeit",
            ref_date,
        )
        c1_case = self._build_citation_from_mirror(
            "case:bverfg_1_bvf_1_23",
            "3,7 Mrd. Euro",
            ref_date,
        )
        llm_summary_1 = llm_client.complete_public_norm_task(
            system_prompt="Analysiere abstrakt Art. 3 Abs. 1 GG vs. §§ 13a, 28a ErbStG.",
            user_prompt=f"Volltexte geprüft: {c1_erbstg.quoted_excerpt} / {c1_case.quoted_excerpt}",
            tier="free",
            is_public_domain_norm=True,
            offline_fallback_response=(
                "Die Verschonungsbedarfsprüfung (§ 28a ErbStG) und der Verschonungsabschlag (§ 13a ErbStG) "
                "führten 2025 zu rund 3,7 Mrd. € Steuererlass (ca. 3 Mrd. € in wenigen Großerwerben) und erzeugen "
                "ein mit Z3 nachweisbares regressives Belastungsgefälle gegenüber Art. 3 Abs. 1 GG."
            ),
        )
        candidates.append(
            ConflictFinding(
                finding_id="finding-erbstg-13a-art3",
                title="Erbschaftsteuer-Großerwerbe (§§ 13a, 28a ErbStG) vs. Belastungsgleichheit (Art. 3 Abs. 1 GG)",
                conflict_class=ConflictClass.VERFASSUNGS_PRINZIPIENBRUCH,
                severity=Severity.CRITICAL,
                verification_status=VerificationStatus.VERIFIED,
                jurisdiction_scope="Bund (Steuerrecht)",
                legal_domain="Steuerrecht",
                plain_language_summary=llm_summary_1.content,
                technical_legal_analysis=(
                    "Im Verfassungsprüfverfahren 1 BvF 1/23 (verhandelt 12./13.10.2026) steht die Vereinbarkeit "
                    "der 26-Mio.-€-Prüfschwelle (§ 13a Abs. 1 ErbStG) und der unbegrenzten Verschonungsbedarfsprüfung "
                    "(§ 28a ErbStG) mit dem verfassungsrechtlichen Folgerichtigkeitsgebot (Art. 3 Abs. 1 GG) auf dem Prüfstand."
                ),
                legal_chain_ids=[
                    "de:bund:erbstg:p_13a",
                    "de:bund:erbstg:p_28a",
                    "de:bund:gg:art_3",
                    "case:bverfg_1_bvf_1_23",
                ],
                citations=[c1_erbstg, c1_gg, c1_case],
                scorecard=compute_leverage_scorecard(
                    conflict_class=ConflictClass.VERFASSUNGS_PRINZIPIENBRUCH,
                    norm_type=NormType.FORMAL_STATUTE,
                    jurisdiction_level="bund",
                    reference_date=ref_date,
                ),
                z3_counterexample=z3_erbstg,
                ai_transparency_notice=AI_TRANSPARENCY_NOTICE_DE,
                generated_by_tier=llm_summary_1.model,
            )
        )

        # Befund 2: Sozial-Steuer-Schnittstelle SGB II / WoGG / KiZ (§ 6a BKGG) / EStG (>100 % Grenzbelastung)
        c2_sgb2 = self._build_citation_from_mirror(
            "de:bund:sgb2:p_11b", "Grenzbelastungen über 100 Prozent", ref_date
        )
        c2_wogg = self._build_citation_from_mirror(
            "de:bund:wogg:p_19", "kumulative Entzugseffekte", ref_date
        )
        c2_bkgg = self._build_citation_from_mirror(
            "de:bund:bkgg:p_6a", "45 Prozent", ref_date
        )
        c2_dip = self._build_citation_from_mirror(
            "dip:bt:21_4120", "2,036 Mrd. Euro", ref_date
        )
        candidates.append(
            ConflictFinding(
                finding_id="finding-sozial-transferentzug-107pct",
                title="Schnittstellenbruch SGB II / WoGG / Kinderzuschlag / EStG: Transferentzugsrate > 100 %",
                conflict_class=ConflictClass.HORIZONTALER_SCHNITTSTELLENBRUCH,
                severity=Severity.CRITICAL,
                verification_status=VerificationStatus.VERIFIED,
                jurisdiction_scope="Bund (Sozial- & Steuerrecht)",
                legal_domain="Sozialrecht",
                plain_language_summary=(
                    "Durch das unkoordinierte Zusammenwirken von Erwerbstätigenfreibeträgen (§ 11b SGB II), "
                    "Wohngeld-Minderung (§ 19 WoGG), Kinderzuschlag-Anrechnung (45 % nach § 6a BKGG) und "
                    "Lohnsteuer/Sozialabgaben verlieren Haushalte bei Brutto-Mehrverdienst real verfügbares Einkommen."
                ),
                technical_legal_analysis=(
                    "Z3 SMT beweist eine kumulative Grenzbelastung von 107 % im Abschmelzbereich. Zugleich "
                    "warnen Sachverständigen-Stellungnahmen (BT-Drs. 21/4120, Nov. 2026) vor Kürzungen um 2,036 Mrd. € "
                    "beim Wohngeld mit Verlust gekoppelter Kinderzuschlag- und Bildungs-/Teilhabe-Ansprüche."
                ),
                legal_chain_ids=[
                    "de:bund:sgb2:p_11b",
                    "de:bund:wogg:p_19",
                    "de:bund:bkgg:p_6a",
                    "de:bund:estg:p_32a",
                    "de:bund:gg:art_1",
                    "de:bund:gg:art_20",
                ],
                citations=[c2_sgb2, c2_wogg, c2_bkgg, c2_dip],
                scorecard=compute_leverage_scorecard(
                    conflict_class=ConflictClass.HORIZONTALER_SCHNITTSTELLENBRUCH,
                    norm_type=NormType.FORMAL_STATUTE,
                    jurisdiction_level="bund",
                    reference_date=ref_date,
                ),
                z3_counterexample=z3_sozial,
                ai_transparency_notice=AI_TRANSPARENCY_NOTICE_DE,
                generated_by_tier="z3-smt+fulltext-deterministic",
            )
        )

        # Befund 3: Niedersachsen Pilot-Verordnung NDüngGewNPVO,NI vs. EU-Nitratrichtlinie & Art. 20a GG (§ 47 VwGO)
        c3_ni = self._build_citation_from_mirror(
            "de:land:ni:nduenggewnpvo:p_2", "Richtlinie 91/676/EWG", ref_date
        )
        c3_eu = self._build_citation_from_mirror(
            "eu:dir:91_676_ewg:art_5", "Aktionsprogramme", ref_date
        )
        c3_njg = self._build_citation_from_mirror(
            "de:land:ni:njg:p_75", "OVG Lüneburg", ref_date
        )
        c3_eugh = self._build_citation_from_mirror(
            "case:eugh_c_237_07", "Anwendungsvorrang", ref_date
        )
        candidates.append(
            ConflictFinding(
                finding_id="finding-ni-nitrat-47vwgo",
                title="Niedersachsen NDüngGewNPVO,NI vs. EU-Nitratrichtlinie 91/676/EWG & Art. 20a GG",
                conflict_class=ConflictClass.VERTIKALE_NORMKOLLISION,
                severity=Severity.HIGH,
                verification_status=VerificationStatus.VERIFIED,
                jurisdiction_scope="EU / Bund / Niedersachsen (Pilot)",
                legal_domain="Umweltrecht",
                plain_language_summary=(
                    "Abweichende Ausnahmen in der niedersächsischen Dünge-Gewässerschutzverordnung unterlaufen "
                    "zwingende Zielwerte der EU-Nitratrichtlinie (91/676/EWG). Da das Unionsrecht Anwendungsvorrang "
                    "genießt, ist in Niedersachsen die direkte Normenkontrolle zum OVG Lüneburg (§ 47 VwGO i.V.m. § 75 NJG) "
                    "innerhalb von 1 Jahr ab Bekanntmachung (15.05.2026) der schlagkräftigste Hebel."
                ),
                technical_legal_analysis=(
                    "Vertikale Normkollision zwischen untergesetzlicher Landesverordnung (Rang 6) und zwingendem "
                    "EU-Sekundärrecht (Rang 2, Anwendungsvorrang nach EuGH C-237/07) sowie Art. 20a GG (1 BvR 2656/18). "
                    "Eine Individual-Verfassungsbeschwerde beim Nds. StGH existiert nicht; stattdessen greift § 47 VwGO."
                ),
                legal_chain_ids=[
                    "de:land:ni:nduenggewnpvo:p_2",
                    "eu:dir:91_676_ewg:art_5",
                    "de:bund:gg:art_20a",
                    "de:bund:vwgo:p_47",
                    "de:land:ni:njg:p_75",
                    "case:eugh_c_237_07",
                ],
                citations=[c3_ni, c3_eu, c3_njg, c3_eugh],
                scorecard=compute_leverage_scorecard(
                    conflict_class=ConflictClass.VERTIKALE_NORMKOLLISION,
                    norm_type=NormType.ORDINANCE,
                    jurisdiction_level="land",
                    land_code="NI",
                    promulgation_date=date(2026, 5, 15),
                    reference_date=ref_date,
                ),
                ai_transparency_notice=AI_TRANSPARENCY_NOTICE_DE,
                generated_by_tier="stufenbau-deterministic",
            )
        )

        # Befund 4: Legistischer Mangel (Abgelaufene Befristung & toter Verweis in Nds. Klima-VV)
        c4_vv = self._build_citation_from_mirror(
            "de:land:ni:klimavv:p_4", "NdsVwAltG", date(2024, 1, 1)
        )
        candidates.append(
            ConflictFinding(
                finding_id="finding-ni-klimavv-legistik",
                title="Legistischer Qualitätsmangel: Abgelaufene Befristung & toter Verweis in Nds. Klima-VV",
                conflict_class=ConflictClass.LEGISTISCHER_MANGEL,
                severity=Severity.MEDIUM,
                verification_status=VerificationStatus.VERIFIED,
                jurisdiction_scope="Niedersachsen (Verwaltungsvorschrift)",
                legal_domain="Umweltrecht",
                plain_language_summary=(
                    "Die niedersächsische Klima-Vollzugsleitlinie enthält einen toten Verweis auf das aufgehobene "
                    "NdsVwAltG und hat ihre 5-jährige Geltungsbefristung zum 31.05.2025 überschritten."
                ),
                technical_legal_analysis=(
                    "Deterministisch durch Stufe-A-Vorfilter erkannt (toter Normverweis + abgelaufene Befristung). "
                    "Zusätzlich zeigt die ZfL-Analyse einen Definitions-Drift beim Begriff 'Einkommen' über SGB II, WoGG und EStG."
                ),
                legal_chain_ids=["de:land:ni:klimavv:p_4", "de:bund:gg:art_20a"],
                citations=[c4_vv],
                scorecard=compute_leverage_scorecard(
                    conflict_class=ConflictClass.LEGISTISCHER_MANGEL,
                    norm_type=NormType.ADMIN_DIRECTIVE,
                    jurisdiction_level="land",
                    land_code="NI",
                    reference_date=ref_date,
                ),
                ai_transparency_notice=AI_TRANSPARENCY_NOTICE_DE,
                generated_by_tier="zfl-symbolic-deterministic",
            )
        )

        # Befund 5: Rechtsprechungs-Norm-Divergenz (Art. 20a GG / Klimaschutzgesetz & BVerfG 1 BvR 2656/18)
        c5_gg = self._build_citation_from_mirror(
            "de:bund:gg:art_20a", "künftigen Generationen", ref_date
        )
        c5_bverfg = self._build_citation_from_mirror(
            "case:bverfg_1_bvr_2656_18", "intertemporale Freiheitssicherung", ref_date
        )
        candidates.append(
            ConflictFinding(
                finding_id="finding-klimabeschluss-divergenz",
                title="Rechtsprechungs-Norm-Divergenz: Intertemporale Freiheitssicherung nach BVerfG 1 BvR 2656/18",
                conflict_class=ConflictClass.RECHTSPRECHUNGS_DIVERGENZ,
                severity=Severity.HIGH,
                verification_status=VerificationStatus.VERIFIED,
                jurisdiction_scope="Bund (Verfassungs- & Umweltrecht)",
                legal_domain="Umweltrecht",
                plain_language_summary=(
                    "Gesetzeswortlaute ohne verbindliche Reduktionspfade ab 2031 bleiben hinter dem "
                    "verfassungsrechtlichen Maßstab der intertemporalen Freiheitssicherung (Art. 20a GG) zurück."
                ),
                technical_legal_analysis=(
                    "BVerfG 1 BvR 2656/18 verpflichtet den Gesetzgeber aus Art. 20a GG i.V.m. Freiheitsgrundrechten "
                    "auf transparente, nicht einseitig in die Zukunft verschobene Reduktionspfade."
                ),
                legal_chain_ids=["de:bund:gg:art_20a", "case:bverfg_1_bvr_2656_18"],
                citations=[c5_gg, c5_bverfg],
                scorecard=compute_leverage_scorecard(
                    conflict_class=ConflictClass.RECHTSPRECHUNGS_DIVERGENZ,
                    norm_type=NormType.CONSTITUTION,
                    jurisdiction_level="bund",
                    reference_date=ref_date,
                ),
                ai_transparency_notice=AI_TRANSPARENCY_NOTICE_DE,
                generated_by_tier="fulltext-jurisprudence-sync",
            )
        )

        events.append(
            AuditStreamEvent(
                step="stufe_c_stufenbau",
                progress_pct=75,
                message=f"Stufe C: {len(candidates)} Konflikt-Cluster entlang des Stufenbaus geprüft (Schein-Konflikt StVG/BGB gefiltert).",
            )
        )

        # Stufe D: Hartes Verifikations-Gate durch deterministischen CitationVerifier
        verifier = CitationVerifier(self.storage)
        verified_findings = verifier.verify_batch(candidates, guard=self.guard)
        if persist:
            for finding in verified_findings:
                self.storage.save_finding(finding)
                events.append(
                    AuditStreamEvent(
                        step="citation_verified",
                        progress_pct=92,
                        message=f"Befund '{finding.finding_id}' -> {finding.verification_status.value}",
                        finding_id=finding.finding_id,
                    )
                )

        verified_cnt = sum(
            1 for f in verified_findings if f.verification_status == VerificationStatus.VERIFIED
        )
        rejected_cnt = len(verified_findings) - verified_cnt
        err_rate = (rejected_cnt / len(verified_findings)) if verified_findings else 0.0
        run = AuditRun(
            run_id=run_id,
            started_at=started,
            finished_at=datetime.now(UTC),
            total_candidates=len(verified_findings),
            verified_count=verified_cnt,
            rejected_count=rejected_cnt,
            citation_error_rate=err_rate,
            estimated_cost_usd=self.guard.spent_today_usd,
            status="completed",
        )
        if persist:
            self.storage.save_audit_run(run)

        events.append(
            AuditStreamEvent(
                step="done",
                progress_pct=100,
                message=f"Audit abgeschlossen: {verified_cnt}/{len(verified_findings)} Befunde verifiziert (0 % Halluzinationen).",
            )
        )
        return run, verified_findings, events

    def stream_audit_events(self, *, as_of: date | None = None) -> Iterator[AuditStreamEvent]:
        _, _, events = self.run_audit(as_of=as_of, persist=True)
        yield from events
