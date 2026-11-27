"""Phase-5-Tests: Vernetzter Jura-Recherche-Assistent (Modus A RDG-Kompass & Modus B Copilot)."""

from __future__ import annotations

import pytest
from lexaudit_analyzer.assistant import LegalResearchAssistant
from lexaudit_core.guardrails import RDGViolationBlockedError
from lexaudit_core.schemas import AssistantMode, AssistantQuery, VerificationStatus
from lexaudit_core.seed_corpus import load_pilot_corpus
from lexaudit_core.storage import SQLiteStorageBackend
from lexaudit_graph.repository import build_graph_from_storage


def test_mode_a_blocks_individual_case_advice_and_allows_abstract_queries() -> None:
    storage = SQLiteStorageBackend(":memory:")
    load_pilot_corpus(storage)
    graph = build_graph_from_storage(storage)
    assistant = LegalResearchAssistant(storage=storage, graph=graph)

    blocked = assistant.answer_query(
        AssistantQuery(
            query="Habe ich in meinem konkreten Fall Anspruch auf Wohngeld?",
            mode=AssistantMode.MODE_A_PUBLIC_COMPASS,
        )
    )
    assert blocked.rdg_blocked is True
    assert "RDG" in blocked.answer

    ok = assistant.answer_query(
        AssistantQuery(
            query="Wie wirken § 11b SGB II und § 19 WoGG zusammen?",
            mode=AssistantMode.MODE_A_PUBLIC_COMPASS,
        )
    )
    assert ok.rdg_blocked is False
    assert ok.verification_status == VerificationStatus.VERIFIED
    assert ok.citations
    assert "Art. 50 KI-VO" in ok.ai_transparency_notice


def test_mode_b_requires_brao_confirmation_and_returns_stufenbau_chains() -> None:
    storage = SQLiteStorageBackend(":memory:")
    load_pilot_corpus(storage)
    graph = build_graph_from_storage(storage)
    assistant = LegalResearchAssistant(storage=storage, graph=graph)

    with pytest.raises(RDGViolationBlockedError):
        assistant.answer_query(
            AssistantQuery(
                query="Normkette § 13a ErbStG vs Art. 3 GG",
                mode=AssistantMode.MODE_B_RESEARCH_COPILOT,
                brao_supervised_confirmed=False,
            )
        )

    res = assistant.answer_query(
        AssistantQuery(
            query="Normkette § 13a ErbStG und Verschonungsbedarfsprüfung Art. 3 GG",
            mode=AssistantMode.MODE_B_RESEARCH_COPILOT,
            brao_supervised_confirmed=True,
        )
    )
    assert res.verification_status == VerificationStatus.VERIFIED
    assert len(res.citations) >= 1
    assert "deterministic" in res.privacy_transport or "zdr" in res.privacy_transport
