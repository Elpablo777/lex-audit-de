"""Automatisierte Eval-Suite (RAGAS-/DeepEval-Metriken & CitationVerifier-Gate) über 50+ Gold-Fälle."""

from __future__ import annotations

from datetime import date

import pytest
from lexaudit_analyzer.citation_verifier import CitationVerifier
from lexaudit_analyzer.pipeline import AuditPipeline
from lexaudit_analyzer.scorecard import compute_leverage_scorecard
from lexaudit_core.guardrails import RDGComplianceGuard
from lexaudit_core.schemas import (
    CitationProof,
    ConflictClass,
    ConflictFinding,
    NormType,
    Severity,
    VerificationStatus,
)
from lexaudit_core.seed_corpus import load_pilot_corpus
from lexaudit_core.storage import SQLiteStorageBackend
from lexaudit_graph.repository import build_graph_from_storage

from tests.eval.gold_set import GOLD_EVAL_CASES


def test_eval_gold_set_meets_ragas_and_citation_thresholds(pytestconfig: pytest.Config) -> None:
    strict = bool(pytestconfig.getoption("--strict-citations"))
    storage = SQLiteStorageBackend(":memory:")
    load_pilot_corpus(storage)
    graph = build_graph_from_storage(storage)
    verifier = CitationVerifier(storage)

    # 1. Pipeline-Befunde evaluieren
    pipeline = AuditPipeline(storage=storage, graph=graph)
    run, findings, _ = pipeline.run_audit(as_of=date(2026, 11, 27))
    assert run.verified_count >= 5
    assert run.rejected_count == 0

    # Schein-Konflikt StVG/BGB darf NICHT als Konfliktbefund markiert sein
    finding_titles = " ".join(f.title for f in findings)
    assert "StVG" not in finding_titles

    # 2. Context Recall & Citation Accuracy auf allen Retrieval-Gold-Fällen messen
    retrieval_cases = [c for c in GOLD_EVAL_CASES if c.expected_norm_ids]
    recall_hits = 0
    citation_total = 0
    citation_verified = 0

    for case in retrieval_cases:
        hits = storage.hybrid_search(case.query, limit=6)
        hit_ids = {h.item_id.split("@")[0] for h in hits}
        if any(exp in hit_ids for exp in case.expected_norm_ids):
            recall_hits += 1

        for exp_id in case.expected_norm_ids:
            lookup = storage.lookup_full_text(exp_id, as_of=date(2026, 11, 27))
            citation_total += 1
            if lookup:
                ft, src, eli, st = lookup
                proof = verifier.verify_citation(
                    CitationProof(
                        citation_id=f"eval_{case.case_id}",
                        norm_or_ecli_ref=exp_id,
                        eli_or_ecli=eli,
                        norm_location=exp_id,
                        as_of_date=date(2026, 11, 27),
                        source_url=src,
                        quoted_excerpt=ft[:80],
                        status_at_date=st,
                    )
                )
                if proof.verified:
                    citation_verified += 1

    # 3. RDG-Proben prüfen
    rdg_cases = [c for c in GOLD_EVAL_CASES if c.must_block_rdg]
    rdg_blocked_ok = sum(
        1 for c in rdg_cases if not RDGComplianceGuard.evaluate_query(c.query).allowed_abstract
    )
    assert rdg_blocked_ok == len(rdg_cases)

    # 4. Halluzinations-Proben prüfen (müssen zu 100 % REJECTED_UNVERIFIED sein!)
    hall_cases = [c for c in GOLD_EVAL_CASES if c.is_hallucination_probe]
    unverified_leaks = 0
    for hc in hall_cases:
        probe = ConflictFinding(
            finding_id=f"probe_{hc.case_id}",
            title="Halluzinations-Test",
            conflict_class=ConflictClass.VERTIKALE_NORMKOLLISION,
            severity=Severity.LOW,
            verification_status=VerificationStatus.VERIFIED,
            plain_language_summary="Probe",
            technical_legal_analysis="Probe",
            citations=[
                CitationProof(
                    citation_id=f"cit_{hc.case_id}",
                    norm_or_ecli_ref=hc.fake_ref,
                    eli_or_ecli="eli/invalid",
                    norm_location=hc.fake_ref,
                    as_of_date=date(2026, 11, 27),
                    source_url="https://invalid.example",
                    quoted_excerpt="Dieser erfundene Satz steht in keinem deutschen Gesetzbuch.",
                )
            ],
            scorecard=compute_leverage_scorecard(
                conflict_class=ConflictClass.VERTIKALE_NORMKOLLISION,
                norm_type=NormType.FORMAL_STATUTE,
                jurisdiction_level="bund",
            ),
        )
        res = verifier.verify_finding(probe)
        if res.verification_status != VerificationStatus.REJECTED_UNVERIFIED:
            unverified_leaks += 1

    context_recall = recall_hits / len(retrieval_cases)
    citation_accuracy = citation_verified / citation_total
    faithfulness = 1.0 - (unverified_leaks / len(hall_cases))
    zero_unverified_rate = 1.0 if (unverified_leaks == 0 and run.rejected_count == 0) else 0.0

    assert len(GOLD_EVAL_CASES) >= 50
    assert faithfulness >= 0.90, f"Faithfulness {faithfulness:.2f} < 0.90"
    assert citation_accuracy >= 0.92, f"Citation Accuracy {citation_accuracy:.2f} < 0.92"
    assert context_recall >= 0.80, f"Context Recall {context_recall:.2f} < 0.80"
    if strict:
        assert zero_unverified_rate == 1.0, "Strict-Citations-Gate verletzt!"
