"""Harte Sicherheits-, Budget-, RDG- und Datenschutz-Guardrails für LexAudit DE/EU."""

from __future__ import annotations

import re
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime

from lexaudit_core.config import LexAuditSettings, get_settings


class BudgetLimitExceededError(RuntimeError):
    """Wird ausgelöst, wenn MAX_DAILY_USD überschritten würde."""


class FreeQuotaExceededError(RuntimeError):
    """Wird ausgelöst, wenn das tägliche :free-Kontingent erschöpft ist."""


class CitationErrorRateExceededError(RuntimeError):
    """Notbremse bei > 8 % nicht verifizierbaren Zitationen in einem Audit-Batch."""


class RDGViolationBlockedError(PermissionError):
    """Wird bei unerlaubter Einzelfall-Rechtsberatung ausgelöst."""


class PrivacyZDRViolationError(PermissionError):
    """Wird ausgelöst, wenn sensible Eingaben an nicht-ZDR- oder :free-Provider geleitet würden."""


@dataclass
class BudgetAndRateLimitGuard:
    """Überwacht tägliche Token-Kosten, :free-Anfragelimits und die Zitations-Fehlerquote."""

    settings: LexAuditSettings = field(default_factory=get_settings)
    spent_today_usd: float = 0.0
    free_requests_today: int = 0
    _current_utc_day: str = field(default_factory=lambda: datetime.now(UTC).strftime("%Y-%m-%d"))
    _minute_window: deque[float] = field(default_factory=deque)

    def _rollover_if_new_day(self) -> None:
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        if today != self._current_utc_day:
            self._current_utc_day = today
            self.spent_today_usd = 0.0
            self.free_requests_today = 0

    def check_paid_budget(self, estimated_cost_usd: float) -> None:
        self._rollover_if_new_day()
        if self.spent_today_usd + estimated_cost_usd > self.settings.max_daily_usd:
            raise BudgetLimitExceededError(
                f"Tagesbudget MAX_DAILY_USD ({self.settings.max_daily_usd:.2f} USD) erreicht: "
                f"aktuell {self.spent_today_usd:.4f} + geschätzt {estimated_cost_usd:.4f} USD."
            )

    def record_paid_usage(self, actual_cost_usd: float) -> None:
        self._rollover_if_new_day()
        self.spent_today_usd += max(0.0, actual_cost_usd)

    def acquire_free_slot(self, now_monotonic: float | None = None) -> float:
        """Prüft Tages- (950) und Minutenlimit (18 req/min) und gibt erforderliche Wartezeit zurück."""
        self._rollover_if_new_day()
        if self.free_requests_today >= self.settings.max_free_req_per_day:
            raise FreeQuotaExceededError(
                f"Tageslimit MAX_FREE_REQ_PER_DAY={self.settings.max_free_req_per_day} erreicht."
            )
        now = time.monotonic() if now_monotonic is None else now_monotonic
        while self._minute_window and (now - self._minute_window[0]) >= 60.0:
            self._minute_window.popleft()

        wait_seconds = 0.0
        if len(self._minute_window) >= self.settings.max_free_req_per_min:
            oldest = self._minute_window[0]
            wait_seconds = max(0.0, 60.0 - (now - oldest) + 0.05)

        self._minute_window.append(now + wait_seconds)
        self.free_requests_today += 1
        return wait_seconds

    @staticmethod
    def exponential_backoff_seconds(attempt: int, base: float = 1.5, cap: float = 30.0) -> float:
        return float(min(cap, base * (2 ** max(0, attempt))))

    def check_citation_error_rate(self, total: int, rejected: int) -> float:
        if total <= 0:
            return 0.0
        rate = rejected / total
        if rate > self.settings.max_citation_error_rate:
            raise CitationErrorRateExceededError(
                f"Zitations-Fehlerquote {rate:.1%} überschreitet Schwellenwert "
                f"{self.settings.max_citation_error_rate:.1%} ({rejected}/{total}). Lauf abgebrochen."
            )
        return rate


class PIISanitizer:
    """Deterministischer PII-Filter vor externen Prompts und in Urteilsspiegeln (Art. 10 / DSGVO)."""

    _PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
        (re.compile(r"\bDE\d{2}\s?(?:\d{4}\s?){4}\d{2}\b", re.IGNORECASE), "[IBAN_ENTFERNT]"),
        (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "[EMAIL_ENTFERNT]"),
        (
            re.compile(r"(?:(?<!\w)\+49|\b0)\s?[1-9]\d{1,4}[\s/-]?\d{3,10}(?:[\s/-]?\d{2,6})?\b"),
            "[TELEFON_ENTFERNT]",
        ),
        (re.compile(r"\b\d{2}\s?\d{3}\s?\d{3}\s?\d{3}\b"), "[STEUER_ID_ENTFERNT]"),
        (re.compile(r"\bsk-or-v1-[A-Za-z0-9_-]{10,}\b"), "[SECRET_ENTFERNT]"),
    )

    @classmethod
    def sanitize(cls, text: str) -> str:
        cleaned = text
        for pattern, replacement in cls._PATTERNS:
            cleaned = pattern.sub(replacement, cleaned)
        return cleaned


@dataclass(frozen=True)
class RDGDecision:
    allowed_abstract: bool
    reason: str | None
    referral_text: str


class RDGComplianceGuard:
    """Blockiert konkrete Einzelfall-Rechtsberatung für Laien nach § 2 Abs. 1, § 3 RDG."""

    _INDIVIDUAL_CASE_PATTERNS: tuple[re.Pattern[str], ...] = (
        re.compile(
            r"(?i)\b(habe\s+ich|steht\s+mir|kann\s+ich|muss\s+ich|darf\s+ich)\b"
            r".{0,90}\b(anspruch|recht|klagen|widerspruch|einspruch|erfolg|chancen|geld|wohngeld|bürgergeld)\b"
        ),
        re.compile(
            r"(?i)\b(in\s+meinem\s+(?:konkreten\s+)?fall|mein(?:en|em|er|es)?\s+(?:steuer)?(?:bescheid|vertrag|vermieter|arbeitgeber|finanzamt|jobcenter|erbe)|meine[rn]?\s+(?:kündigung|klage|steuererklärung|frist))\b"
        ),
        re.compile(r"(?i)\b(wie\s+soll\s+ich\s+(?:jetzt\s+)?vorgehen|prüfe\s+meinen\s+fall|berate\s+mich)\b"),
    )

    REFERRAL_NOTICE = (
        "RDG-Schutzhinweis (§ 2 Abs. 1 RDG): LexAudit DE/EU leistet ausschließlich allgemeine, "
        "abstrakte Norm- und Systeminformation. Eine rechtliche Prüfung oder Erfolgsprognose "
        "für Ihren konkreten persönlichen Einzelfall ist gesetzlich zugelassenen Rechtsanwältinnen "
        "und Rechtsanwälten, Verbraucherzentralen oder öffentlichen Rechtsantragsstellen vorbehalten."
    )

    @classmethod
    def evaluate_query(cls, query: str) -> RDGDecision:
        normalized = query.strip()
        for pattern in cls._INDIVIDUAL_CASE_PATTERNS:
            if pattern.search(normalized):
                return RDGDecision(
                    allowed_abstract=False,
                    reason=(
                        "Erkannte Einzelfall-Subsumtionsanfrage (persönlicher Anspruch, "
                        "konkreter Bescheid oder individuelle Klageaussicht)."
                    ),
                    referral_text=cls.REFERRAL_NOTICE,
                )
        return RDGDecision(allowed_abstract=True, reason=None, referral_text="")
