# Projektstatus (`STATUS.md`) — LexAudit DE/EU

> **Für Mitwirkende & KI-Agenten:** Diese Datei zeigt immer den **aktuellen, durch reale Befehle belegten Projektstand**. Bitte nach jedem abgeschlossenen Arbeitsschritt aktualisieren.

**Letztes Update:** 2026-11-27  
**Aktuelle Phase:** Phasen 0–5 abgeschlossen & end-to-end verifiziert (`v1.0` Baseline)

## Abgeschlossene Module (Phasen 0–5)
- **Phase 0 (Repo-Bootstrap, Governance & Guardrails):**
  - `AGENTS.md`, `opencode.json`, `.opencode/agents/*`, `.opencode/skills/*`, `CONTRIBUTING.md`, `ROADMAP.md`, `LICENSE`
  - `docs/architecture/MASTERPLAN.md`, `docs/compliance/eu-ai-act-assessment.md`, `docs/db/schema.sql`, `docs/db/neo4j_constraints.cypher`
  - `packages/core/src/lexaudit_core/`: `config.py`, `schemas.py` (Pydantic v2), `guardrails.py` (`BudgetAndRateLimitGuard`, `RDGComplianceGuard`, `PIISanitizer`), `llm_clients.py` (`PublicLawLLMClient`, `CitizenPrivacyLLMClient`)
- **Phase 1 (Zero-Token-Core, bitemporaler Graph & Dagster-Pipelines):**
  - Deterministische XML-/Normparser (`xml_parsers.py`, `reference_parser.py` mit `QuantLawReferenceParser`), Domain-Chunker (`embeddings.py`), SQLite+FTS5 & PostgreSQL/pgvector (`storage.py` inkl. `SET LOCAL hnsw.ef_search = 200` und Thread-Locking), Neo4j / Apache AGE / InMemory (`packages/graph/src/lexaudit_graph/repository.py`), Pilot-Korpus (`seed_corpus.py`), Dagster Assets & tägliche Sensoren (`packages/pipelines/src/lexaudit_pipelines/definitions.py`).
- **Phase 2 (Neuro-Symbolische Analyse-Engine, Z3 SMT & Eval-Gate):**
  - Symbolische Vorfilter & ZfL-Extraktor (`symbolic_filters.py`), Z3-Modelle mit per-Call-`z3.Context()` + Lock (`z3_models.py`: Pilot 1 SGB II/WoGG/KiZ/EStG & Pilot 2 § 13a/§ 13c/§ 28a ErbStG), `CitationVerifier` (`citation_verifier.py`), BVerfG-2025-Scorecard (`scorecard.py`), `AuditPipeline` (`pipeline.py`), 54-Fälle-Gold-Set & Eval-Gate (`tests/eval/test_eval_suite.py`).
- **Phase 3 (FastAPI-Backend & Barrierefreies Web-Portal):**
  - FastAPI + SSE-Streaming (`apps/api/src/lexaudit_api/{main,state}.py`) auf Port `8010` (ausgewichen wegen `Basic Memory` auf Port `8000`).
  - Next.js 15 / TypeScript `strict: true` Portal (`apps/web/`): Editorial Startseite `/`, Sigma.js WebGL-Rechtsgraph `/graph` mit Zeitreise & WCAG-2.2-HTML-Tabellen-Toggle, Befunddetails & React-Flow-Kausalbaum `/findings/[id]` (ebenfalls mit 1-Klick-HTML-Tabelle), interaktives Z3-Labor `/simulator`, Demokratie-Werkzeuge `/aktionen` (Bundestag/Landtag/openPetition + Abgeordnetenwatch + § 47 VwGO Dossier) und Dual-Mode-Assistent `/assistent`.
- **Phase 4 (Föderale Skalierung 16 Länder, OLDP & HUDOC):**
  - `StateLawConnector`-Registry für alle 16 Bundesländer (`state_connectors.py`) mit `RobotsTxtGuard` und `DNGOpenDataRequestGenerator` sowie Live-Konnektoren für NeuRIS (`/v1/legislation`, `/v1/rechtsprechung`; `/v1/case-law` explizit blockiert), Nds. Verkündungsplattform, DIP, Abgeordnetenwatch, OLDP, EUR-Lex SPARQL und HUDOC (`connectors.py`).
- **Phase 5 (Vernetzter Dual-Mode-Jura-Recherche-Assistent):**
  - Modus A („Öffentlicher Rechts-Kompass“, `RDGComplianceGuard`) und Modus B („Jura-Research-Copilot“, § 3 BRAO, erzwungenes ZDR/Offline-Routing + `CitationVerifier`) in `packages/analyzer/src/lexaudit_analyzer/assistant.py`.

## Verifizierte Prüfergebnisse (Stand 2026-11-27, nach letztem Code-Edit)
- **Python Linting (`uv run ruff check .`):** `All checks passed!` (0 Fehler)
- **Python Typechecking (`uv run mypy packages apps tests`):** `Success: no issues found in 40 source files`
- **Python Test- & Eval-Suite (`uv run pytest tests/unit tests/eval --strict-citations -v`):** `28 passed in 5.77s` (inkl. Thread-Safety-Tests für Z3, 16-Länder-Compliance und 54-Fälle-Gold-Set `--strict-citations`)
- **Frontend (`pnpm.cmd --dir apps/web lint && typecheck && test && build`):** ESLint 0 Fehler, `tsc --noEmit` 0 Fehler, Vitest `3 passed` (WCAG-Tabellen-Toggles + Z3-Simulator-Haushaltstabelle), Next.js `next build` `9/9` Routen erfolgreich gebaut
- **Docker-Infrastruktur (`docker compose ps`):** `lexaudit-postgres` (`pgvector/pgvector:pg17`, healthy) liefert `PostgresVectorStorageBackend.vector_search_norm_chunks` (3 Treffer inkl. `de:bund:gg:art_3`); `lexaudit-neo4j` (`neo4j:5.26-community`, healthy) liefert `59` Knoten / `42` Kanten via Cypher
- **Manuelle Browser-E2E-Prüfung (`http://127.0.0.1:3000` gegen FastAPI `:8010`):** Alle 6 Portalseiten (`/`, `/graph`, `/findings/[id]`, `/simulator`, `/aktionen`, `/assistent`) inklusive SSE-Live-Audit, WebGL/React-Flow WCAG-HTML-Tabellen-Umschaltung, interaktiver Z3-Haushaltskurve (>100 % Grenzbelastung & Live-Slider), Petitions-URL-Prüfung und RDG-Blockade ohne Konsolenfehler oder HTTP-4xx/5xx-Fehler bestanden. Live-Probe (`GET /api/v1/sources/live-probe`) aller 7 externen Open-Data-APIs erfolgreich.

## Bekannte Einschränkungen / Hinweise für Mitwirkende
- Ohne gesetzten `OPENROUTER_API_KEY` arbeitet die Plattform vollständig deterministisch im Offline-/Lokalmodus (`PublicLawLLMClient` / `CitizenPrivacyLLMClient`).
- Port `8010` ist als FastAPI-Standardport konfiguriert (siehe `.env.example`, `AGENTS.md`, `docker-compose.yml`), um Konflikte mit lokalen Diensten auf Port `8000` zu vermeiden.
- Für großskalige Massendaten-Importe (gesamter C-DBR-/CE-Korpus, GPU-Embeddings mit Qwen3-4B/BGE-M3) siehe die Community-Meilensteine in [ROADMAP.md](ROADMAP.md).
