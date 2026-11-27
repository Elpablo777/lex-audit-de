"""Phase-0-Unit-Tests für Budget-Guardrails, RDG-Compliance, PII-Filter & Dual-LLM-ZDR."""

from __future__ import annotations

import pytest
from lexaudit_core.config import LexAuditSettings
from lexaudit_core.guardrails import (
    BudgetAndRateLimitGuard,
    BudgetLimitExceededError,
    CitationErrorRateExceededError,
    FreeQuotaExceededError,
    PIISanitizer,
    PrivacyZDRViolationError,
    RDGComplianceGuard,
)
from lexaudit_core.llm_clients import CitizenPrivacyLLMClient, PublicLawLLMClient


def test_budget_guard_blocks_above_daily_limit() -> None:
    settings = LexAuditSettings(LEXAUDIT_MAX_DAILY_USD=1.00)
    guard = BudgetAndRateLimitGuard(settings=settings)
    guard.record_paid_usage(0.95)
    with pytest.raises(BudgetLimitExceededError):
        guard.check_paid_budget(0.10)


def test_free_rate_limiter_enforces_daily_and_minute_caps() -> None:
    settings = LexAuditSettings(LEXAUDIT_MAX_FREE_REQ_PER_DAY=3, LEXAUDIT_MAX_FREE_REQ_PER_MIN=2)
    guard = BudgetAndRateLimitGuard(settings=settings)
    assert guard.acquire_free_slot(now_monotonic=100.0) == 0.0
    assert guard.acquire_free_slot(now_monotonic=101.0) == 0.0
    wait = guard.acquire_free_slot(now_monotonic=102.0)
    assert wait > 50.0
    with pytest.raises(FreeQuotaExceededError):
        guard.acquire_free_slot(now_monotonic=200.0)


def test_citation_error_rate_aborts_above_8_percent() -> None:
    guard = BudgetAndRateLimitGuard(settings=LexAuditSettings())
    assert guard.check_citation_error_rate(total=20, rejected=1) == pytest.approx(0.05)
    with pytest.raises(CitationErrorRateExceededError):
        guard.check_citation_error_rate(total=20, rejected=2)


def test_citizen_privacy_client_rejects_free_models_and_enforces_zdr() -> None:
    client = CitizenPrivacyLLMClient(settings=LexAuditSettings(LEXAUDIT_OFFLINE_DEMO=True))
    with pytest.raises(PrivacyZDRViolationError):
        client.build_zdr_request_payload(
            system_prompt="System",
            user_query="Abstrakte Normfrage",
            model="deepseek/deepseek-v4-flash:free",
        )

    payload = client.build_zdr_request_payload(
        system_prompt="System",
        user_query="Meine IBAN ist DE89 3704 0044 0532 0130 00.",
    )
    assert payload["provider"] == {"zdr": True, "allow_fallbacks": False}
    assert "[IBAN_ENTFERNT]" in payload["messages"][1]["content"]


def test_public_law_client_rejects_non_public_domain_inputs() -> None:
    client = PublicLawLLMClient(settings=LexAuditSettings(LEXAUDIT_OFFLINE_DEMO=True))
    with pytest.raises(PrivacyZDRViolationError):
        client.complete_public_norm_task(
            system_prompt="System",
            user_prompt="Vertrauliche Bürgereingabe",
            is_public_domain_norm=False,
        )


def test_rdg_guard_blocks_individual_case_subsumption_and_allows_abstract() -> None:
    blocked = RDGComplianceGuard.evaluate_query(
        "Habe ich in meinem konkreten Fall Anspruch auf Wohngeld trotz Teilzeit?"
    )
    assert blocked.allowed_abstract is False
    assert "RDG" in blocked.referral_text

    allowed = RDGComplianceGuard.evaluate_query(
        "Wie wirken § 11b SGB II und § 19 WoGG im Einkommensanrechnungssystem zusammen?"
    )
    assert allowed.allowed_abstract is True


def test_pii_sanitizer_masks_emails_phones_and_secrets() -> None:
    raw = "Kontakt: max@example.de, Tel +49 511 1234567, Key sk-or-v1-abc1234567890"
    cleaned = PIISanitizer.sanitize(raw)
    assert "max@example.de" not in cleaned
    assert "1234567" not in cleaned
    assert "sk-or-v1-" not in cleaned
