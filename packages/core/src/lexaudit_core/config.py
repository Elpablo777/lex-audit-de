"""Zentrale Konfiguration und harte Budget-/Sicherheits-Grenzwerte für LexAudit DE/EU."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

AI_TRANSPARENCY_NOTICE_DE = (
    "Hinweis nach Art. 50 KI-VO (VO (EU) 2024/1689): Diese Auswertung bzw. Textvorlage "
    "wurde unter Einsatz eines KI-gestützten Analyse- und Zitationsverifikationssystems auf "
    "Basis amtlicher Primärquellen erstellt. Sie stellt allgemeine Rechts- und Systeminformation "
    "dar und ersetzt keine individuelle Rechtsberatung nach dem RDG."
)

BVERFG_2025_STATS = {
    "year": 2025,
    "total_filings": 4722,
    "resolved": 4916,
    "successful": 55,
    "success_rate": 0.0112,
    "ten_year_avg_rate": 0.0148,
    "kammer_total": 4710,
    "kammer_non_acceptance_no_reason": 3924,
    "kammer_non_acceptance_no_reason_rate": 0.8331,
    "direct_statute_complaints": 75,
    "direct_statute_share": 0.0159,
    "senate_decisions": 16,
    "nds_individual_constitutional_complaint": False,
}


class LexAuditSettings(BaseSettings):
    """Typsichere Laufzeitkonfiguration über Umgebungsvariablen oder `.env`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    env: Literal["development", "test", "production"] = Field(
        default="development", alias="LEXAUDIT_ENV"
    )
    offline_demo: bool = Field(default=False, alias="LEXAUDIT_OFFLINE_DEMO")

    database_url: str = Field(
        default="postgresql+psycopg://lexaudit:lexaudit_dev@127.0.0.1:5432/lexaudit",
        alias="DATABASE_URL",
    )
    sqlite_fallback_path: str = Field(
        default="data/lexaudit_local.sqlite3", alias="LEXAUDIT_SQLITE_PATH"
    )
    neo4j_uri: str = Field(default="bolt://127.0.0.1:7687", alias="NEO4J_URI")
    neo4j_user: str = Field(default="neo4j", alias="NEO4J_USER")
    neo4j_password: str = Field(default="lexaudit_neo4j_dev", alias="NEO4J_PASSWORD")
    graph_backend: Literal["auto", "neo4j", "age", "memory"] = Field(
        default="auto", alias="LEXAUDIT_GRAPH_BACKEND"
    )

    hnsw_ef_search: int = Field(default=200, ge=50, le=1000)
    embedding_provider: Literal["deterministic", "qwen3-4b", "bge-m3", "ollama"] = Field(
        default="deterministic", alias="LEXAUDIT_EMBEDDING_PROVIDER"
    )
    embedding_dim: int = Field(default=1024, alias="LEXAUDIT_EMBEDDING_DIM")
    ollama_base_url: str = Field(default="http://127.0.0.1:11434", alias="LEXAUDIT_OLLAMA_BASE_URL")

    openrouter_api_key: str = Field(default="", alias="OPENROUTER_API_KEY")
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1", alias="OPENROUTER_BASE_URL"
    )
    openrouter_free_model: str = Field(
        default="deepseek/deepseek-v4-flash:free", alias="OPENROUTER_FREE_MODEL"
    )
    openrouter_mid_model: str = Field(
        default="deepseek/deepseek-v4-pro", alias="OPENROUTER_MID_MODEL"
    )
    openrouter_frontier_model: str = Field(
        default="anthropic/claude-sonnet-5.5", alias="OPENROUTER_FRONTIER_MODEL"
    )
    openrouter_zdr_model: str = Field(
        default="anthropic/claude-sonnet-5.5", alias="OPENROUTER_ZDR_MODEL"
    )

    # Verbindliche Budget- & Sicherheits-Guardrails
    max_daily_usd: float = Field(default=5.00, ge=0.0, alias="LEXAUDIT_MAX_DAILY_USD")
    max_free_req_per_day: int = Field(
        default=950, ge=1, le=1000, alias="LEXAUDIT_MAX_FREE_REQ_PER_DAY"
    )
    max_free_req_per_min: int = Field(
        default=18, ge=1, le=20, alias="LEXAUDIT_MAX_FREE_REQ_PER_MIN"
    )
    max_citation_error_rate: float = Field(
        default=0.08, ge=0.0, le=1.0, alias="LEXAUDIT_MAX_CITATION_ERROR_RATE"
    )

    bundestag_dip_api_key: str = Field(default="", alias="BUNDESTAG_DIP_API_KEY")

    @model_validator(mode="after")
    def _ensure_safe_limits(self) -> LexAuditSettings:
        """Harte Obergrenze für :free-Rate-Limits im Code verankern."""
        if self.max_free_req_per_day > 950:
            self.max_free_req_per_day = 950
        if self.max_free_req_per_min > 18:
            self.max_free_req_per_min = 18
        return self


@lru_cache(maxsize=1)
def get_settings() -> LexAuditSettings:
    """Liefert gecachte Anwendungseinstellungen."""
    return LexAuditSettings()
