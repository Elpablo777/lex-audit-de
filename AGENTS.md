# AGENTS.md — LexAudit DE/EU (Föderales Rechts-Audit- & Demokratie-Portal)

> Dieses Dokument gilt als verbindliche Arbeitsgrundlage für **alle** menschlichen Mitwirkenden und KI-Coding-Agenten (OpenCode, Antigravity, Claude Code, Codex, Cursor). Jede neue Session startet mit dem Lesen dieser Datei und von `STATUS.md` sowie `docs/architecture/MASTERPLAN.md`.

## Projektmission
Gemeinnützige Open-Source-Rechtsplattform für Deutschland und die EU (Pilot-Bundesland: **Niedersachsen**, generisch skalierbar auf **alle 16 Bundesländer**). Das System verknüpft Völkerrecht, EU-Recht, Bundesrecht, Landesrecht, Rechtsprechung und Parlamentsbegründungen in einem **bitemporalen Knowledge Graph**, identifiziert maschinell und reproduzierbar Normwidersprüche, Schnittstellenbrüche und verfassungsrechtliche Risiken und liefert faktengeprüfte Bürger-Erklärungen, Petitionen, Abgeordneten-Dossiers und Normenkontroll-Briefings.

## Verbindliche Befehle (Authoritative Commands)

- **Python-Umgebung (Python 3.12 via uv):** `uv sync`
- **Tests & Linting (Python):** `uv run pytest; uv run ruff check .; uv run mypy packages apps`
- **Eval-Suite (RAGAS-/Citation-Gate):** `uv run pytest tests/eval/ --strict-citations`
- **Frontend (WebGL/Next.js):** `pnpm --dir apps/web install; pnpm --dir apps/web lint; pnpm --dir apps/web test; pnpm --dir apps/web build`
- **Infrastruktur lokal (PostgreSQL + pgvector + Neo4j):** `docker compose up -d postgres neo4j`
- **FastAPI-Backend lokal:** `uv run uvicorn lexaudit_api.main:app --host 127.0.0.1 --port 8000 --reload`
- **Dagster Dev-Server:** `uv run dagster dev -m lexaudit_pipelines.definitions`

*(Hinweis für Windows PowerShell 5.1: Statt `&&` Befehle mit `;` oder `if ($LASTEXITCODE -eq 0)` verketten.)*

## Architektur-Grenzen & Konventionen

1. **Zero-Token-First:** Gesetzesstrukturen (§/Abs./Satz), bitemporale Fassungen (`valid_from`, `valid_to`), ELI/ECLI-IDs und Norm-Querverweise werden deterministisch aus XML/JSON/SPARQL und Regel-Parsern (`QuantLawReferenceParser`) erzeugt — niemals durch LLM-Loops über Roh-PDFs.
2. **Strenge Zitationspflicht (`CitationVerifier`):** Jeder gespeicherte Befund benötigt maschinenprüfbare Primärquellen (`eli_uri` oder `ecli`, exakte Normstelle, Stand-Datum, `source_url`, verifizierbare Zitat-Substrings). Kein LLM-Output darf ohne bestandenen `CitationVerifier`-Check persistiert oder im Frontend angezeigt werden (`REJECTED_UNVERIFIED`).
3. **Bitemporale Historie:** Historische Normfassungen niemals überschreiben; immer neue `ComponentTemporalVersion`-Knoten anlegen und über `SUPERSEDES` verketten.
4. **Tiered OpenRouter Routing & ZDR:** Massen-Extraktion gemeinfreier Normen (§ 5 UrhG) über `PublicLawLLMClient` (günstige/optionale `:free`-Modelle mit hartem Rate-Limiter: max. 18 req/min, max. 950 req/Tag); Bürgereingaben und vertrauliche Anfragen ausschließlich über `CitizenPrivacyLLMClient` mit erzwungenem `provider.zdr: true` oder lokalem Ollama/LM Studio (oder deterministischem Offline-Modus ohne Secrets-Leak).
5. **Code-Qualität & Inklusion:** Python 3.12+ mit strikten Pydantic-v2-Schemas; TypeScript `strict: true` im Frontend; **WCAG 2.2** (zu jeder WebGL-/Canvas-/SVG-Grafik gehört ein 1-Klick-Toggle zur vollständigen semantischen HTML-Tabelle).
6. **Lebende Projekt-Doku:** Nach jedem Meilenstein oder Architektur-Update sind `STATUS.md` und `ROADMAP.md` aktuell zu halten, damit externe Open-Source-Mitwirkende nahtlos weiterarbeiten können.

## Strikte Verbote (DON'T)

- **KEIN RDG-Verstoß (§ 2 Abs. 1 RDG):** Niemals einen freien Einzelfall-Rechtsberatungs-Chatbot für Laien bauen. Alle Bürger-Funktionen bleiben strikt abstrakt-normativ oder erzeugen standardisierte politische Eingaben. Konkrete Einzelfall-Subsumtion wird technisch durch den `RDGComplianceGuard` abgewiesen.
- **KEIN EU-AI-Act-Hochrisiko (VO (EU) 2024/1689 + Digital Omnibus VO 2026/1744):** Kein Nutzer-Profiling, keine personalisierten Wahlempfehlungen, keine individuelle Urteilsprognose. Jede KI-Analyse trägt einen sichtbaren Art.-50-Transparenzhinweis.
- **KEIN Scraping geschützter Datenbanken:** Niemals `juris`, `beck-online` oder `NI-VORIS` (Wolters Kluwer) unter Umgehung von `robots.txt` oder § 87a/§ 44b UrhG massenhaft scrapen. Ausschließlich amtliche Open-Data-APIs und Verkündungsblätter sowie offen lizenzierte Korpora (z. B. OLDP mit ODbL-Attribution) nutzen.
- **KEIN `/v1/case-law` bei NeuRIS:** Dieser Endpunkt wurde im Oktober 2026 mit HTTP 410 entfernt; ausschließlich `/v1/legislation` und `/v1/rechtsprechung` nutzen.
- **KEINE PII/Secrets an nicht-ZDR-Provider:** Niemals Bürgereingaben oder `.env`-Inhalte an `:free`-Modelle oder nicht-ZDR-Endpoints senden.
- **KEIN PDF-Massenloop in n8n:** Bulk-Ingestion läuft ausschließlich über Dagster mit SHA-256-Hash-Diff.
- **KEINE ungeprüften Live-Migrationen:** Destruktive DB-Migrationen nur kontrolliert und mit explizitem Schema-Version-Check.
