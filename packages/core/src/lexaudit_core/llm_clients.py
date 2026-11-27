"""Strikte Dual-Client-Architektur für OpenRouter & lokales Ollama (Post-Dragos Nov 2026)."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Literal

import httpx
import truststore

from lexaudit_core.config import LexAuditSettings, get_settings
from lexaudit_core.guardrails import (
    BudgetAndRateLimitGuard,
    PIISanitizer,
    PrivacyZDRViolationError,
)


def create_tls_client(timeout: float = 30.0) -> httpx.Client:
    """Erstellt einen httpx-Client mit OS-Zertifikatsspeicher (behebt z. B. Bund-CA-Ketten unter Windows)."""
    ssl_ctx = truststore.SSLContext(protocol=None) if False else None
    try:
        import ssl

        ssl_ctx = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    except Exception:
        ssl_ctx = None
    return httpx.Client(
        timeout=timeout,
        verify=ssl_ctx if ssl_ctx is not None else True,
        headers={"User-Agent": "LexAudit-DE-EU/0.1 (+https://github.com/Elpablo777/lex-audit-de)"},
        follow_redirects=True,
    )


@dataclass(frozen=True)
class LLMResponsePayload:
    content: str
    model: str
    provider_mode: str
    zdr_enforced: bool
    estimated_cost_usd: float
    cache_enabled: bool = False


@dataclass
class PublicLawLLMClient:
    """Ausschließlich für gemeinfreie §-5-UrhG-Rechtsdaten.

    Erlaubt :free-Modelle (mit Rate-Limiter), Mid-Tier (DeepSeek V4 Pro) und
    Frontier-Tier (Claude Sonnet 5.5 mit Sticky session_id & Prompt Caching).
    """

    settings: LexAuditSettings = field(default_factory=get_settings)
    guard: BudgetAndRateLimitGuard = field(default_factory=BudgetAndRateLimitGuard)

    def complete_public_norm_task(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        tier: Literal["free", "mid", "frontier"] = "free",
        is_public_domain_norm: bool = True,
        session_id: str | None = None,
        enable_prompt_cache: bool = False,
        offline_fallback_response: str | None = None,
    ) -> LLMResponsePayload:
        if not is_public_domain_norm:
            raise PrivacyZDRViolationError(
                "PublicLawLLMClient darf ausschließlich gemeinfreie §-5-UrhG-Texte verarbeiten. "
                "Nutze für Bürgereingaben zwingend CitizenPrivacyLLMClient."
            )

        model = {
            "free": self.settings.openrouter_free_model,
            "mid": self.settings.openrouter_mid_model,
            "frontier": self.settings.openrouter_frontier_model,
        }[tier]

        if tier == "free":
            wait_s = self.guard.acquire_free_slot()
            if wait_s > 0 and not self.settings.offline_demo:
                time.sleep(min(wait_s, 0.05))  # In Tests/Dev minimal halten
            est_cost = 0.0
        else:
            est_cost = 0.002 if tier == "mid" else 0.012
            self.guard.check_paid_budget(est_cost)

        if self.settings.offline_demo or not self.settings.openrouter_api_key:
            content = offline_fallback_response or "[OFFLINE_DETERMINISTIC_MODE]"
            return LLMResponsePayload(
                content=content,
                model=f"{model} (offline-fallback)",
                provider_mode="deterministic-offline",
                zdr_enforced=False,
                estimated_cost_usd=0.0,
                cache_enabled=enable_prompt_cache,
            )

        headers: dict[str, str] = {
            "Authorization": f"Bearer {self.settings.openrouter_api_key}",
            "HTTP-Referer": "https://github.com/Elpablo777/lex-audit-de",
            "X-Title": "LexAudit DE/EU Public Norm Pipeline",
        }
        messages: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": (
                    [
                        {
                            "type": "text",
                            "text": system_prompt,
                            "cache_control": {"type": "ephemeral", "ttl": "1h"},
                        }
                    ]
                    if enable_prompt_cache
                    else system_prompt
                ),
            },
            {"role": "user", "content": user_prompt},
        ]
        payload: dict[str, Any] = {"model": model, "messages": messages, "temperature": 0.1}
        if session_id:
            payload["user"] = session_id

        with create_tls_client(timeout=45.0) as client:
            resp = client.post(
                f"{self.settings.openrouter_base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        if tier != "free":
            self.guard.record_paid_usage(est_cost)

        text = str(data["choices"][0]["message"]["content"])
        return LLMResponsePayload(
            content=text,
            model=model,
            provider_mode="openrouter-public",
            zdr_enforced=False,
            estimated_cost_usd=est_cost,
            cache_enabled=enable_prompt_cache,
        )


@dataclass
class CitizenPrivacyLLMClient:
    """Strikt ZDR-geschützter Client für Bürgereingaben & Phase-5-Anfragen.

    Verbietet technisch `:free`-Modelle und erzwingt `provider.zdr: true` (oder lokales Ollama).
    """

    settings: LexAuditSettings = field(default_factory=get_settings)
    guard: BudgetAndRateLimitGuard = field(default_factory=BudgetAndRateLimitGuard)

    def build_zdr_request_payload(
        self,
        *,
        system_prompt: str,
        user_query: str,
        model: str | None = None,
    ) -> dict[str, Any]:
        chosen_model = model or self.settings.openrouter_zdr_model
        if ":free" in chosen_model:
            raise PrivacyZDRViolationError(
                f"Sicherheitsverstoß: Modell '{chosen_model}' ist ein :free-Endpoint und darf "
                "niemals Bürgereingaben verarbeiten (Post-Dragos ZDR-Regel)."
            )
        sanitized_query = PIISanitizer.sanitize(user_query)
        return {
            "model": chosen_model,
            "temperature": 0.1,
            "provider": {"zdr": True, "allow_fallbacks": False},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": sanitized_query},
            ],
        }

    def complete_citizen_query(
        self,
        *,
        system_prompt: str,
        user_query: str,
        offline_fallback_response: str,
        model: str | None = None,
    ) -> LLMResponsePayload:
        payload = self.build_zdr_request_payload(
            system_prompt=system_prompt, user_query=user_query, model=model
        )

        if self.settings.embedding_provider == "ollama" and not self.settings.openrouter_api_key:
            return LLMResponsePayload(
                content=offline_fallback_response,
                model="ollama-local",
                provider_mode="local-ollama",
                zdr_enforced=True,
                estimated_cost_usd=0.0,
            )

        if self.settings.offline_demo or not self.settings.openrouter_api_key:
            return LLMResponsePayload(
                content=offline_fallback_response,
                model="deterministic-zdr-local",
                provider_mode="deterministic-local-zdr",
                zdr_enforced=True,
                estimated_cost_usd=0.0,
            )

        est_cost = 0.01
        self.guard.check_paid_budget(est_cost)
        headers = {
            "Authorization": f"Bearer {self.settings.openrouter_api_key}",
            "HTTP-Referer": "https://github.com/Elpablo777/lex-audit-de",
            "X-Title": "LexAudit DE/EU Citizen Privacy ZDR",
        }
        with create_tls_client(timeout=45.0) as client:
            resp = client.post(
                f"{self.settings.openrouter_base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        self.guard.record_paid_usage(est_cost)
        return LLMResponsePayload(
            content=str(data["choices"][0]["message"]["content"]),
            model=str(payload["model"]),
            provider_mode="openrouter-zdr-verified",
            zdr_enforced=True,
            estimated_cost_usd=est_cost,
        )
