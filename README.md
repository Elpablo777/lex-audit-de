# LexAudit DE/EU — Föderales Rechts-Audit- & Demokratie-Portal

> **Gemeinnützige Open-Source-Plattform**, die Völkerrecht, EU-Recht, deutsches Bundesrecht, Landesrecht aller 16 Bundesländer (**Pilot: Niedersachsen**), Rechtsprechung und Parlamentsbegründungen in einem **bitemporalen Knowledge Graph** verknüpft, neuro-symbolisch auf Normwidersprüche und Schnittstellenbrüche prüft und faktengeprüfte Bürger-Erklärungen, Petitionen, Abgeordneten-Briefe und Normenkontroll-Dossiers bereitstellt.

[![CI Qualitäts- & Zitations-Gate](https://github.com/Elpablo777/lex-audit-de/actions/workflows/ci.yml/badge.svg)](https://github.com/Elpablo777/lex-audit-de/actions)
[![Lizenz: MIT](https://img.shields.io/badge/Lizenz-MIT-blue.svg)](LICENSE)

## Kernprinzipien & Architektur

1. **Zero-Token-First (Deterministische Ingestion):** Statt teurer LLM-Loops über tausende Roh-PDFs nutzt LexAudit strukturierte amtliche Datenquellen (**NeuRIS** `/v1/legislation` & `/v1/rechtsprechung`, **Gesetze-im-Internet XML**, **C-DBR**, **Rechtsprechung-im-Internet**, **BGBl**, **EUR-Lex CELLAR SPARQL**, **HUDOC**, **Bundestag DIP**, **verkuendung-niedersachsen.de**, **Open Legal Data**, **Abgeordnetenwatch API v2**, **FragDenStaat**).
2. **Bitemporaler Wissensgraph:** Abgebildet über `LegalAct` → `NormUnit` → `ComponentTemporalVersion` (`valid_from`, `valid_to`, `SUPERSEDES`) in PostgreSQL 17 + `pgvector` (`hnsw.ef_search = 200`) und Neo4j Community (bzw. Apache AGE / InMemory-Fallback).
3. **Neuro-Symbolische Analyse + Z3 SMT Solver:** Mathematische Gegenbeweise für komplexe Transferentzugsraten (> 80 % / > 100 % bei **SGB II / WoGG / Kinderzuschlag § 6a BKGG / EStG**) und Schwellenwerte (**§ 13a ErbStG**) kombiniert mit ZfL-Pflichtenanalyse und Stufenbau-Prüfung.
4. **Harte Zitations-Brandmauer (`CitationVerifier`):** Jeder KI-Befund wird deterministisch gegen den lokalen Volltextspiegel geprüft — nicht verifizierbare Aussagen (`REJECTED_UNVERIFIED`) erreichen niemals das Frontend.
5. **Rechtssicherheit & Barrierefreiheit:** Strikt RDG-konform (§ 2 Abs. 1 RDG), EU-AI-Act-Transparenz (Art. 50 & Art. 6 Abs. 3/4), Post-Dragos-ZDR-Trennung (`PublicLawLLMClient` vs. `CitizenPrivacyLLMClient`), WCAG 2.2 mit **1-Klick-HTML-Tabellen-Toggle** für jede WebGL-/React-Flow-Visualisierung.

## Schnellstart (Lokal & Open-Source-Einstieg)

```powershell
# 1. Konfiguration kopieren (funktioniert auch ohne API-Key im Offline-/Deterministisch-Modus!)
Copy-Item .env.example .env

# 2. Python-Workspace installieren (Python 3.12 via uv)
uv sync

# 3. Tests, Linter, Typecheck & Eval-Gate ausführen
uv run pytest
uv run pytest tests/eval/ --strict-citations
uv run ruff check .
uv run mypy packages apps

# 4. Optionale Infrastruktur (PostgreSQL 17 + pgvector & Neo4j) starten
docker compose up -d postgres neo4j

# 5. API & WebGL-Bürgerportal starten
uv run uvicorn lexaudit_api.main:app --host 127.0.0.1 --port 8000
pnpm --dir apps/web install
pnpm --dir apps/web dev
```

## Dokumentation für Mitwirkende & KI-Agenten

- [AGENTS.md](AGENTS.md) — Verbindliche Regeln, Befehle und Verbote (OpenCode / Antigravity / Claude Code / Codex)
- [STATUS.md](STATUS.md) — Aktueller Stand, implementierte Module & reale Testnachweise
- [ROADMAP.md](ROADMAP.md) — Meilensteine Phase 0–5 & offene Community-Ziele
- [docs/architecture/MASTERPLAN.md](docs/architecture/MASTERPLAN.md) — Vollständiger Bauplan, Datenmodell & Verträge
- [docs/compliance/eu-ai-act-assessment.md](docs/compliance/eu-ai-act-assessment.md) — EU AI Act, RDG, UrhG & DSGVO
- [CONTRIBUTING.md](CONTRIBUTING.md) — Leitfaden für Open-Source-Beiträge
