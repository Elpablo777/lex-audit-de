# Master-Architektur- & Ausführungsplan: LexAudit DE/EU

**Projekt:** Föderales Rechts-Audit- & Demokratie-Portal für Deutschland und die EU (Pilot-Bundesland: Niedersachsen, generisch skalierbar auf alle 16 Bundesländer)  
**Status:** Lebender Architektur- & Ausführungsplan (Stand: 27. November 2026)  
**Compliance-Anker:** § 5 / § 44b / §§ 87a ff. UrhG · § 2 Abs. 1 / § 3 RDG · VO (EU) 2024/1689 (EU AI Act Art. 6 Abs. 3/4, Art. 50) + Digital Omnibus VO 2026/1744 · DSGVO / ZDR  

---

## 1. Monorepo-Struktur & Docker-Compose-Topologie

```text
lex-audit-de/
├── AGENTS.md                           # Verbindliche Hausregeln für alle Agenten & Mitwirkenden
├── CONTRIBUTING.md                     # Open-Source-Einstieg, Code-Style, PR-Checkliste
├── LICENSE                             # MIT + Datenlizenz-Hinweise (§ 5 UrhG, ODbL v1.0, CC0, dl-de/by-2-0)
├── README.md                           # Projektüberblick, Schnellstart, Architektur & Demo
├── ROADMAP.md                          # Meilenstein-Planung Phase 0 bis Phase 5
├── STATUS.md                           # Aktueller Entwicklungs-, Test- & Verifikationsstand
├── opencode.json                       # OpenCode-Konfiguration (OpenRouter + de-eli-mcp + eu-sparql-mcp)
├── pyproject.toml                      # uv Workspace / Paket-Konfiguration (Python 3.12+)
├── docker-compose.yml                  # PostgreSQL 17 + pgvector, Neo4j 5 Community, API & Web
├── .env.example                        # Vorlage ohne Secrets
├── .opencode/
│   ├── agents/
│   │   ├── plan.md                     # Read-only Architekt & Legal-Spec-Prüfer
│   │   ├── build.md                    # Implementierer mit TDD & Citation-Gate
│   │   ├── legal-reviewer.md           # RDG-, AI-Act-, UrhG- & ZDR-Prüfagent
│   │   └── eval-auditor.md             # RAGAS-/CitationVerifier-Qualitätswächter
│   └── skills/
│       ├── citation-verification/SKILL.md
│       ├── rdg-compliance/SKILL.md
│       ├── z3-modeling/SKILL.md
│       └── open-source-handoff/SKILL.md
├── docs/
│   ├── architecture/
│   │   └── MASTERPLAN.md               # Dieses Dokument
│   ├── compliance/
│   │   └── eu-ai-act-assessment.md     # Art. 6(3)/6(4) & Art. 50 Dokumentation + RDG/UrhG/DSGVO
│   └── db/
│       ├── schema.sql                  # PostgreSQL 17 + pgvector DDL (inkl. hnsw.ef_search = 200)
│       └── neo4j_constraints.cypher    # Neo4j Constraints & Indizes für bitemporalen SAT-Graph
├── packages/
│   ├── core/                           # Schicht 2a: Schemas, Config, Guardrails, Dual-LLM, XML/QuantLaw-Parser, Storage
│   ├── graph/                          # Schicht 2b: GraphRepository (Neo4j / Apache AGE / InMemory), Bitemporal-Queries
│   ├── pipelines/                      # Schicht 1: Dagster Assets, Sensoren, 16-Länder StateLawConnector, OLDP/HUDOC
│   └── analyzer/                       # Schicht 3: Z3-SMT-Solver, ZfL-Extraktor, Stufenbau-Audit, Scorecard, CitationVerifier, Phase-5-Assistent
├── apps/
│   ├── api/                            # Schicht 5a: FastAPI REST + SSE-Streaming + OpenAPI
│   └── web/                            # Schicht 5b: Next.js + TypeScript strict + Sigma.js WebGL + React Flow + WCAG 2.2
├── tests/
│   ├── unit/                           # Unit- & Integrationstests (Parser, Z3, Graph, RDG, Guardrails, API)
│   ├── eval/                           # Schicht 4: Gold-Set (50+ -> 200 Fälle), RAGAS-Metriken & --strict-citations
│   └── fixtures/                       # Reproduzierbare amtliche XML/JSON-Testdaten (C-DBR, NeuRIS, RII, Nds. GVBl.)
└── .github/
    ├── workflows/ci.yml                # Ruff, Mypy, Pytest, Eval-Gate, ESLint, Vitest, Next Build
    ├── ISSUE_TEMPLATE/
    └── PULL_REQUEST_TEMPLATE.md
```

### Docker-Compose-Topologie (`docker-compose.yml`)
- **`postgres`** (`pgvector/pgvector:pg17`, Port `127.0.0.1:5432`): Primär-Store für Metadaten, Volltextspiegel (`TSVector`), Embeddings (`norm_chunks`, `case_chunks` mit getrennten HNSW-Indizes und `hnsw.ef_search = 200`), Konfliktbefunde und Audit-Protokolle.
- **`neo4j`** (`neo4j:5-community`, Ports `127.0.0.1:7474`, `127.0.0.1:7687`): Bitemporaler Multi-Hop-Knowledge-Graph (4–6 Rechtsstufen) mit `LegalAct` → `NormUnit` → `ComponentTemporalVersion` → `CourtDecision` / `ParliamentaryDoc`.
- **`api`** (`apps/api`, Port `8000`, Profil `full`): FastAPI-Backend + SSE-Stream.
- **`web`** (`apps/web`, Port `3000`, Profil `full`): Next.js Editorial-/WebGL-Bürgerportal.

---

## 2. Datenbank- & Graph-Schema (Bitemporales SAT-Graph-Muster)

Vollständige DDL- und Cypher-Definitionen liegen unter:
- [schema.sql](file:///c:/Users/Pablo/Downloads/Jura%20System/docs/db/schema.sql)
- [neo4j_constraints.cypher](file:///c:/Users/Pablo/Downloads/Jura%20System/docs/db/neo4j_constraints.cypher)

### Kernprinzipien des Datenmodells
1. **Stabile Identität vs. zeitliche Fassungen (LRMoo / ELI SAT-Graph):**
   - `LegalAct` (z. B. `eli/bund/bgbl-1/2002/s4210`) und `NormUnit` (z. B. `de:bund:sgb2:§11b`) behalten dauerhaft dieselbe kanonische ID.
   - Änderungen erzeugen **immer** neue `ComponentTemporalVersion`-Einträge mit `valid_from`, `valid_to`, `promulgation_date`, `status` (`in_force`, `repealed`, `pending`, `expired`) und `text_hash` (SHA-256), verkettet via `SUPERSEDES`.
2. **Retrieval-Qualität (Skopek-2026-Kalibrierung):**
   - Getrennte Vektortabellen `norm_chunks` und `case_chunks` mit eigenen `vector_cosine_ops` HNSW-Indizes (`m = 16, ef_construction = 128`).
   - Vor jeder HNSW-Abfrage erzwingt der Storage-Adapter `SET LOCAL hnsw.ef_search = 200;`.
   - Chunking strikt entlang von `§`/Artikel-Grenzen (Urteile: Leitsatz als eigener Chunk, sonst ~1.000 Zeichen mit Kontext-Header `[Gesetz/Gericht | Datum | Aktenzeichen/Normstelle]`).
3. **Graph-Abstraktion (`GraphRepository`):**
   - Einheitliches Interface für `Neo4jGraphRepository` (Cypher), `ApacheAGEGraphRepository` (openCypher in PostgreSQL) und `InMemoryGraphRepository` (NetworkX für schnelle lokale Tests ohne Container).

---

## 3. Verbindliche Pydantic-v2-Datenverträge (`packages/core/src/lexaudit_core/schemas.py`)

Alle Schichten kommunizieren ausschließlich über strikte Pydantic-v2-Modelle:
- `LegalAct`: `act_id`, `eli_uri`, `title`, `short_title`, `jurisdiction_level` (`international`, `eu`, `bund`, `land`, `kommunal`), `land_code`, `norm_type` (`treaty`, `eu_regulation`, `eu_directive`, `constitution`, `formal_statute`, `ordinance`, `municipal_statute`, `admin_directive`), `promulgation_date`, `source_url`, `license`.
- `NormUnit`: `norm_id`, `act_id`, `eli_uri`, `designation` (`§ 13a`, `Art. 3 Abs. 1`), `heading`, `hierarchy_rank` (1–6 im Stufenbau), `legal_domain`, `status`.
- `ComponentTemporalVersion`: `version_id`, `norm_id`, `valid_from`, `valid_to`, `promulgation_date`, `status`, `text_hash`, `full_text`, `context_header`, `supersedes_version_id`.
- `CourtDecision`: `decision_id`, `ecli`, `court_level` (`egmr`, `eugh`, `bverfg`, `oberstes_bundesgericht`, `ovg_oberlandesgericht`, `fachgericht`), `court_name`, `decision_date`, `file_number`, `leitsatz`, `tenor`, `full_text`, `source_url`, `status_flags`.
- `ParliamentaryDoc`: `doc_id`, `issuer` (`bundestag`, `bundesrat`, `landtag_ni`, ...), `doc_number`, `title`, `summary`, `publication_date`, `source_url`.
- `LegalConcept`: `concept_id`, `term`, `domain`, `norm_id`, `definition_text`, `obligation_type` (`Pflicht_Muss`, `Pflicht_Soll`, `Ermessen_Kann`, `Befugnis`, `Definition`, `Ausnahme`).
- `CitationProof` (deterministisches Verifikationsschema des `CitationVerifier`):
  - `citation_id`, `norm_or_ecli_ref`, `eli_or_ecli`, `norm_location`, `as_of_date`, `source_url`, `quoted_excerpt`, `exact_match_in_mirror` (`bool`), `status_at_date` (`in_force`, `repealed`, `amended`, `unverified`), `verified` (`bool`), `rejection_reason`.
- `LeverageScorecard`:
  - `primary_lever` (`ovg_normenkontrolle_47_vwgo`, `fachgericht_vorlage_art100`, `bundestag_epetition`, `landtag_petition`, `abgeordneten_briefing`, `verfassungsbeschwerde_ultima_ratio`), `realistic_success_band`, `bverfg_reference_rate` (`0.0112`), `kammer_non_acceptance_rate` (`0.8331`), `nds_individual_constitutional_complaint_available` (`False`), `deadline_date`, `days_remaining`, `cost_risk_note`, `rationale`.
- `ConflictFinding`:
  - `finding_id`, `title`, `conflict_class` (Klassen 1–5 der Taxonomie), `severity`, `verification_status` (`VERIFIED`, `REJECTED_UNVERIFIED`), `plain_language_summary`, `legal_chain_ids`, `citations` (`list[CitationProof]`), `scorecard` (`LeverageScorecard`), `z3_counterexample`, `ai_transparency_notice` (Art. 50 KI-VO), `generated_by_tier`.
- `PetitionDraft`:
  - `target_portal` (`bundestag_petition`, `landtag_niedersachsen`, `openpetition`), `title`, `summary`, `request_text`, `legal_basis_refs`, `quorum_required`, `quorum_window_weeks`, `validation_passed`, `validation_errors` (harte Sperre bei externen URLs oder personenbezogenen Angriffen).

---

## 4. Konkreter 5-Phasen-Umsetzungsplan & Akzeptanzkriterien

| Phase | Umfang & Liefergegenstände | Akzeptanzkriterien |
|---|---|---|
| **Phase 0: Bootstrap & Guardrails** | Monorepo, `AGENTS.md`, `opencode.json`, `.opencode/`, `docker-compose.yml`, DDL/Cypher, CI, `eu-ai-act-assessment.md`, Dual-LLM-Client (`PublicLawLLMClient` / `CitizenPrivacyLLMClient`), Cost-Cap & Rate-Limiter | `uv sync`, `ruff`, `mypy`, Phase-0-Pytests grün, OpenRouter-Guardrails & RDG/AI-Act-Compliance dokumentiert und getestet |
| **Phase 1: Zero-Token-Core & Pilot Bund + NI** | XML/JSON-Parser (LegalDocML.de, GII-XML, RII-XML, Formex-XML), `QuantLawReferenceParser`, Domain-Chunker & Embedding-Adapter, `StorageBackend` (Postgres+pgvector `ef_search=200` & SQLite-Fallback), `GraphRepository` (Neo4j/AGE/InMemory), Dagster Assets & tägliche Sensoren (NeuRIS `/v1/legislation` & `/v1/rechtsprechung`, GII, RII, BGBl, `verkuendung-niedersachsen.de`, DIP, EUR-Lex SPARQL) | Deterministischer Graph-Aufbau mit 0 LLM-Tokens, SHA-256-Diff-Updates, `v1/case-law` blockiert, Live-API-Probes & Parser-Tests 100 % grün |
| **Phase 2: Neuro-Symbolische Analyse & Eval-Gate** | Stufe A Graph-/Symbol-Vorfilter + **Z3 SMT Solver** (Pilot 1: SGB II / WoGG / KiZ § 6a BKGG / EStG Transferentzugsrate; Pilot 2: § 13a ErbStG Schwellenwerte), Stufe B ZfL-Pflichten-&-Definitions-Extraktor, Stufe C Stufenbau-Audit + Full-Text-Lookup, Stufe D `LeverageScorecard` + `CitationVerifier`, `tests/eval/` Gold-Set (50+ Fälle, Ziel 200) | Z3 beweist reale Gegenbeispiele (>100 % Grenzbelastung, § 13a Sprungstellen), CitationVerifier blockt halluzinierte Referenzen (`REJECTED_UNVERIFIED`), Eval-Suite erreicht `Faithfulness >= 0.90`, `Citation Accuracy >= 0.92`, `Context Recall >= 0.80`, `Zero Unverified Citations == 100%` |
| **Phase 3: Bürgerportal, WebGL & Demokratie-Tools** | FastAPI (OpenAPI + SSE `/api/v1/audits/stream`), Next.js Editorial-Portal (`strict: true`), Sigma.js + Graphology WebGL-Netzwerk (Filter & Zeitreise), React Flow Konflikt-/Kausalbaum, interaktiver Z3-Slider, **1-Klick-Toggle zur WCAG-2.2-HTML-Tabelle**, Petitions-Assistent (`petition.bundestag.de` / Nds. Landtag / openPetition), Abgeordnetenwatch-Router, § 47 VwGO Dossier | `pnpm --dir apps/web lint && test && build` fehlerfrei, SSE live, WebGL & React Flow mit HTML-Tabellen-Toggle im Browser manuell geprüft |
| **Phase 4: Föderale Skalierung 16 Länder, OLDP & HUDOC** | `StateLawConnector`-Plugin-System (`VerkuendungsblattConnector`, `BsXXJurisConnector` für 9 Länder mit striktem `robots.txt`/§ 44b UrhG Guard, Einzeladapter BY/NRW/SN/BB/HB/SL + NI), DNG-Open-Data-Anfrage-Generator, Open Legal Data API/JSONL-Connector, HUDOC & HUDOC-EXEC Connector | Alle 16 Länder-Adapter registriert und mit `robots.txt`-Guard getestet, OLDP & HUDOC-Parser verifiziert |
| **Phase 5: Vernetzter Jura-Recherche-Assistent** | Dual-Mode-Assistent: Modus A „Öffentlicher Rechts-Kompass“ (abstrakt, RDG-konform, verweist Einzelfälle ab), Modus B „Jura-Research-Copilot“ (§ 3 BRAO Normketten-/Rechtsprechungs-Tiefe), strikt hinter `CitizenPrivacyLLMClient` (ZDR/lokal/offline) + `CitationVerifier` + Art.-50-Badge | RDG-Guardrail blockiert Einzelfall-Subsumtion deterministisch, Modus B liefert quellenverifizierte Normketten, Browser-E2E bestanden |

---

## 5. Budget- & Sicherheits-Guardrails (Hard-Limits im Code)

- `MAX_DAILY_USD = 5.00` (konfigurierbar über `LEXAUDIT_MAX_DAILY_USD`): Harter Budget-Unterbrecher pro UTC-Tag vor jedem kostenpflichtigen OpenRouter-Aufruf.
- `MAX_FREE_REQ_PER_DAY = 950` und `MAX_FREE_REQ_PER_MIN = 18` mit Exponential Backoff + Jitter (schützt das 1.000/Tag- und 20/Min-Kontingent inkl. Sicherheitsmarge für Fehlversuche).
- **Prompt-Caching:** Stabiler Verfassungs-Prüfschema-Präfix mit `session_id` für Sticky-Routing und `cache_control` (1h TTL) auf Tier-4b-Audits.
- **Zitations-Notbremse:** Überschreitet die Zitations-Fehlerquote in einem Batch `MAX_CITATION_ERROR_RATE = 0.08` (8 %), bricht der Pipeline-Lauf sofort mit `CitationErrorRateExceeded` ab, statt ungeprüfte Befunde zu persistieren.
- **Zero-Data-Retention (Post-Dragos Nov 2026):** `PublicLawLLMClient` akzeptiert **nur** gemeinfreie §-5-UrhG-Inhalte; `CitizenPrivacyLLMClient` lehnt `:free`-Slugs und nicht-ZDR-Provider technisch ab und erzwingt `provider.zdr: true`, lokales Ollama/LM Studio oder deterministischen Offline-Betrieb.

---

## 6. Kritische Schnittstellenrisiken & Vereinfachungsentscheidungen

1. **Vermeidung eines toten Endpunkts bei NeuRIS:** `/v1/case-law` liefert HTTP 410 Gone — alle Rechtsprechungsabfragen laufen über `/v1/rechtsprechung`.
2. **SSL-Zertifikatskette bei `recht.bund.de` auf Windows:** Python `urllib` auf Windows kann fehlende Intermediate-Zertifikate bei `recht.bund.de` bemängeln; der Connector nutzt daher `httpx` + `truststore` (System-Zertifikatsspeicher) bzw. Fallback auf NeuRIS `eli/bund/bgbl-1`.
3. **Verkündungsplattform Niedersachsen ist eine React-SPA:** `verkuendung-niedersachsen.de` lädt Treffer dynamisch via `POST /api/search` (Elasticsearch-Format); der Sensor spricht diesen JSON-Endpunkt direkt und respektiert dabei Crawl-Delays.
4. **Landesportale & § 87a / § 44b UrhG:** Statt aggressivem HTML-Scraping auf kommerziell betriebenen Portalen (NI-VORIS, juris `bsXX`) prüft jeder Konnektor zwingend `robots.txt` und stützt sich primär auf amtliche Verkündungsblätter sowie DNG-Open-Data-Anträge.
5. **Pragmatischer Dual-Runtime-Pfad:** Im Docker-Betrieb laufen PostgreSQL 17 + pgvector und Neo4j Community vollwertig; für CI, lokale Entwickler ohne laufenden Docker-Daemon und schnelle Tests steht ein 100 % vertragstreuer SQLite-FTS5-/NetworkX-Fallback bereit.

### Erster ausführbarer Arbeitsschritt (Sprint 1 / Phase 0)
Anlage von `pyproject.toml`, `packages/core` (Pydantic-v2-Schemas, Budget- & Rate-Limit-Guardrails, `PublicLawLLMClient` / `CitizenPrivacyLLMClient`), `docker-compose.yml`, `docs/db/schema.sql`, `docs/db/neo4j_constraints.cypher` und Verifikation über `uv run pytest tests/unit/test_phase0_guardrails.py`.
