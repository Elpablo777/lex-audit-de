"""Phase-2-Unit-Tests: Z3 SMT Solver, Symbolische Vorfilter, CitationVerifier, Scorecard & Petitionen."""

from __future__ import annotations

from datetime import date

import pytest
from lexaudit_analyzer.actions import LegislativeBriefingGenerator, PetitionGenerator
from lexaudit_analyzer.citation_verifier import CitationVerifier
from lexaudit_analyzer.pipeline import AuditPipeline
from lexaudit_analyzer.scorecard import compute_leverage_scorecard
from lexaudit_analyzer.symbolic_filters import ZfLExtractor, run_symbolic_prefilters
from lexaudit_analyzer.z3_models import (
    analyze_erbstg_cliff_z3,
    analyze_transfer_withdrawal_z3,
    simulate_household_curve,
)
from lexaudit_core.config import LexAuditSettings
from lexaudit_core.guardrails import (
    BudgetAndRateLimitGuard,
    CitationErrorRateExceededError,
)
from lexaudit_core.schemas import (
    CitationProof,
    ConflictClass,
    ConflictFinding,
    LeverType,
    NormType,
    PetitionTargetPortal,
    Severity,
    VerificationStatus,
)
from lexaudit_core.seed_corpus import load_pilot_corpus
from lexaudit_core.storage import SQLiteStorageBackend
from lexaudit_graph.repository import build_graph_from_storage


def test_z3_proves_social_transfer_trap_over_100_percent() -> None:
    proof = analyze_transfer_withdrawal_z3(rent=850.0, children=2, threshold_pct=100.0)
    assert proof.satisfiable is True
    assert float(proof.outputs["marginal_withdrawal_rate_pct"]) > 100.0

    curve = simulate_household_curve(rent=850.0, children=2)
    assert any(pt.marginal_withdrawal_rate_pct > 100.0 for pt in curve)
    assert all(pt.marginal_withdrawal_rate_pct >= 0.0 for pt in curve)


def test_z3_concurrent_thread_safety() -> None:
    from concurrent.futures import ThreadPoolExecutor

    def _run_pair(i: int) -> tuple[bool, bool]:
        p1 = analyze_transfer_withdrawal_z3(rent=800.0 + i * 10, children=2)
        p2 = analyze_erbstg_cliff_z3(private_assets_mio=2.0)
        return p1.satisfiable, p2.satisfiable

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(_run_pair, range(16)))
    assert all(a and b for a, b in results)


def test_z3_proves_erbstg_regressive_cliff() -> None:
    proof = analyze_erbstg_cliff_z3(private_assets_mio=2.0)
    assert proof.satisfiable is True
    assert float(proof.outputs["eff_rate_large_pct"]) < float(proof.outputs["eff_rate_mid_pct"])


def test_symbolic_prefilters_and_zfl_drift() -> None:
    storage = SQLiteStorageBackend(":memory:")
    load_pilot_corpus(storage)
    graph = build_graph_from_storage(storage)

    signals = run_symbolic_prefilters(storage, graph, reference_date=date(2026, 11, 27))
    kinds = {s.signal_kind for s in signals}
    assert "toter_verweis" in kinds
    assert "abgelaufene_befristung" in kinds

    zfl = ZfLExtractor()
    concepts = zfl.extract_concepts(storage)
    drifts = zfl.detect_definition_drift(concepts)
    assert any(d["term"] == "Einkommen" for d in drifts)


def test_citation_verifier_blocks_hallucinated_citations_and_aborts_above_8pct() -> None:
    storage = SQLiteStorageBackend(":memory:")
    load_pilot_corpus(storage)
    verifier = CitationVerifier(storage)

    fake_finding = ConflictFinding(
        finding_id="fake-1",
        title="Halluzinierter Normwiderspruch",
        conflict_class=ConflictClass.VERTIKALE_NORMKOLLISION,
        severity=Severity.HIGH,
        verification_status=VerificationStatus.VERIFIED,
        plain_language_summary="Falscher Befund",
        technical_legal_analysis="Nicht existierendes Zitat",
        citations=[
            CitationProof(
                citation_id="c-fake",
                norm_or_ecli_ref="de:bund:gg:art_999",
                eli_or_ecli="eli/fake",
                norm_location="Art. 999",
                as_of_date=date(2026, 11, 27),
                source_url="https://example.invalid",
                quoted_excerpt="Frei erfundenes Zitat ohne Spiegelbezug",
            )
        ],
        scorecard=compute_leverage_scorecard(
            conflict_class=ConflictClass.VERTIKALE_NORMKOLLISION,
            norm_type=NormType.FORMAL_STATUTE,
            jurisdiction_level="bund",
        ),
    )
    # Validator auf Modell oder Verifier erzwingt REJECTED_UNVERIFIED
    checked = verifier.verify_finding(fake_finding)
    assert checked.verification_status == VerificationStatus.REJECTED_UNVERIFIED

    guard = BudgetAndRateLimitGuard(settings=LexAuditSettings(LEXAUDIT_MAX_CITATION_ERROR_RATE=0.08))
    with pytest.raises(CitationErrorRateExceededError):
        verifier.verify_batch([fake_finding], guard=guard)


def test_full_audit_pipeline_verifies_all_pilot_findings() -> None:
    storage = SQLiteStorageBackend(":memory:")
    load_pilot_corpus(storage)
    graph = build_graph_from_storage(storage)
    pipeline = AuditPipeline(storage=storage, graph=graph)
    run, findings, events = pipeline.run_audit(as_of=date(2026, 11, 27))

    assert run.status == "completed"
    assert run.verified_count == 5
    assert run.rejected_count == 0
    assert all(f.verification_status == VerificationStatus.VERIFIED for f in findings)
    assert events[-1].progress_pct == 100

    # Niedersachsen-Befund muss § 47 VwGO (OVG Lüneburg) mit 1-Jahres-Frist priorisieren
    ni_finding = next(f for f in findings if f.finding_id == "finding-ni-nitrat-47vwgo")
    assert ni_finding.scorecard.primary_lever == LeverType.OVG_NORMENKONTROLLE_47_VWGO
    assert ni_finding.scorecard.nds_individual_constitutional_complaint_available is False
    assert ni_finding.scorecard.days_remaining is not None

    # Petition-Regelcheck (Bundestag verbietet URLs und Beleidigungen!)
    bad_pet = PetitionGenerator.build_from_finding(
        ni_finding,
        target_portal=PetitionTargetPortal.BUNDESTAG_PETITION,
        custom_text="Bitte prüfen Sie https://externe-seite.example und die korrupt Akteure.",
    )
    assert bad_pet.validation_passed is False
    assert len(bad_pet.validation_errors) >= 2

    good_pet = PetitionGenerator.build_from_finding(
        ni_finding, target_portal=PetitionTargetPortal.LANDTAG_NIEDERSACHSEN
    )
    assert good_pet.validation_passed is True
    assert good_pet.quorum_required == 5000
    assert PetitionGenerator.calculate_openpetition_quorum(10000) == 291 or (
        285 <= PetitionGenerator.calculate_openpetition_quorum(10000) <= 295
    )

    briefing = LegislativeBriefingGenerator.build_briefing(
        ni_finding, reference_date=date(2026, 11, 27)
    )
    assert "OVG Lüneburg" in briefing.markdown_dossier
    assert "Art. 50 KI-VO" in briefing.markdown_dossier
