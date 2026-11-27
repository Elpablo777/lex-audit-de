# Mitwirken an LexAudit DE/EU (Contributing Guide)

Herzlich willkommen! **LexAudit DE/EU** ist ein gemeinnütziges Open-Source-Civic-Tech-Projekt. Jede Verbesserung an Parsern, Landesrecht-Adaptern, Z3-Regelmodellen, RAGAS-Eval-Fällen, UI-Barrierefreiheit oder Dokumentation ist willkommen.

## Schnellstart für Entwicklerinnen & Entwickler

1. **Voraussetzungen:** Python 3.12 (`uv`), Node.js 22+ (`pnpm`), optional Docker Desktop (für PostgreSQL 17 + pgvector und Neo4j Community).
2. **Umgebung einrichten:**
   ```powershell
   Copy-Item .env.example .env
   uv sync
   pnpm --dir apps/web install
   ```
3. **Tests & Qualitäts-Gates ausführen (ohne laufendes Docker oder OpenRouter-Key möglich):**
   ```powershell
   uv run pytest
   uv run pytest tests/eval/ --strict-citations
   uv run ruff check .
   uv run mypy packages apps
   pnpm --dir apps/web lint
   pnpm --dir apps/web typecheck
   pnpm --dir apps/web test
   pnpm --dir apps/web build
   pnpm --dir apps/web audit
   ```
4. **Mit Docker-Infrastruktur lokal starten:**
   ```powershell
   docker compose up -d postgres neo4j
   # Startet FastAPI (:8010) automatisch mit, falls noch kein Backend läuft:
   pnpm --dir apps/web start
   # Oder getrennt in zwei Terminals:
   uv run uvicorn lexaudit_api.main:app --host 127.0.0.1 --port 8010
   pnpm --dir apps/web dev:web
   ```

## Verbindliche Regeln vor jedem Pull Request

1. **Lies zuerst `AGENTS.md` und `STATUS.md`.**
2. **Kein LLM ohne `CitationVerifier`:** Neue Analysemodule müssen jede Norm- und Urteilsreferenz gegen `CitationVerifier` prüfen.
3. **Zero-Token-First:** Struktur-, Datums-, ELI/ECLI- und Zitationsextraktion erfolgt deterministisch.
4. **Rechts-Leitplanken wahren:** Keine Einzelfall-Rechtsberatung für Laien (§ 2 RDG), kein Personen-Profiling / keine Wahlempfehlung (EU AI Act), kein Scraping gegen `robots.txt` / § 87a UrhG, keine PII an nicht-ZDR-Provider.
5. **Barrierefreiheit (WCAG 2.2):** Jede neue WebGL-, Chart- oder Diagramm-Komponente im Frontend braucht zwingend einen 1-Klick-Toggle zur semantischen HTML-Tabelle.
6. **Gold-Set-Erweiterung:** Neue Konfliktklassen oder Z3-Modelle bringen mindestens 3 positive und 1 Schein-Konflikt-Testfall in `tests/eval/` mit.
7. **Status-Update:** Aktualisiere bei größeren Änderungen `STATUS.md` und relevante Abschnitte in `docs/`.
