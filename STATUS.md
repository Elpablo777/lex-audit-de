# Projektstatus (`STATUS.md`) — LexAudit DE/EU

> **Für Mitwirkende & KI-Agenten:** Diese Datei zeigt immer den **aktuellen, durch reale Befehle belegten Projektstand**. Bitte nach jedem abgeschlossenen Arbeitsschritt aktualisieren.

**Letztes Update:** 2026-11-27  
**Aktuelle Phase:** Phase 0 abgeschlossen — Phase 1 (Zero-Token-Core, bitemporaler Graph & Dagster-Pipelines) in Umsetzung

## Abgeschlossene Module
- **Phase 0 (Repo-Bootstrap, Governance & Guardrails):**
  - `AGENTS.md`, `opencode.json`, `.opencode/agents/*`, `.opencode/skills/*`
  - `docs/architecture/MASTERPLAN.md`, `docs/compliance/eu-ai-act-assessment.md`, `CONTRIBUTING.md`, `ROADMAP.md`
  - `docs/db/schema.sql` (PostgreSQL 17 + pgvector mit `norm_chunks`, `case_chunks`, HNSW-Indizes & `hnsw.ef_search = 200`), `docs/db/neo4j_constraints.cypher`
  - `docker-compose.yml` (`postgres`, `neo4j`, `api`, `web`) & `.github/workflows/ci.yml`
  - `packages/core` Phase-0-Kern: `config.py`, `schemas.py` (Pydantic v2), `guardrails.py` (`BudgetAndRateLimitGuard`, `RDGComplianceGuard`, `PIISanitizer`), `llm_clients.py` (`PublicLawLLMClient`, `CitizenPrivacyLLMClient`)

## Aktive Test- & Verifikationsnachweise
- `uv run ruff check .`: 0 Fehler
- `uv run mypy packages apps tests`: `Success: no issues found in 11 source files`
- `uv run pytest tests/unit/test_phase0_guardrails.py -v`: `7 passed in 0.43s`

## Bekannte Einschränkungen / Offene Punkte
- OpenRouter-Live-LLM-Calls erfordern einen gesetzten `OPENROUTER_API_KEY` (ohne Key arbeitet das System automatisch im deterministischen Offline-Modus).
- Phase 1–5 befinden sich im Aufbau.
