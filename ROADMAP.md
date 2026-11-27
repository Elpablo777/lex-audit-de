# Roadmap — LexAudit DE/EU

Diese Roadmap dokumentiert alle Meilensteine gemäß [docs/architecture/MASTERPLAN.md](docs/architecture/MASTERPLAN.md) und dient externen Mitwirkenden als Orientierung für offene Erweiterungen.

- [x] **Phase 0: Repo-Bootstrap, Governance, Compliance & Guardrails**
  - Monorepo, `AGENTS.md`, `opencode.json`, `.opencode/`, `docker-compose.yml`, SQL-/Cypher-Schemas, `eu-ai-act-assessment.md`, Dual-LLM-Client + Budget-/Rate-Limiter, CI-Workflow.
- [x] **Phase 1: Zero-Token-Core & Pilot Bund + Niedersachsen**
  - Pydantic-v2-Schemas, LegalDocML.de / GII-XML / RII-XML / Formex-XML-Parser, `QuantLawReferenceParser`, Domain-Chunker & Embedding-Adapter, `StorageBackend` (`hnsw.ef_search = 200`), `GraphRepository` (Neo4j / Apache AGE / InMemory), Dagster Assets & tägliche Sensoren (NeuRIS, GII, RII, BGBl, `verkuendung-niedersachsen.de`, DIP, EUR-Lex SPARQL).
- [x] **Phase 2: Neuro-Symbolische Analyse-Engine, Z3 & Eval-Gate**
  - Stufe A Symbolische Vorfilter + Z3 Pilot 1 (SGB II / WoGG / KiZ § 6a BKGG / EStG) + Z3 Pilot 2 (§ 13a ErbStG), Stufe B ZfL-Pflichten-/Definitions-Extraktor, Stufe C Verfassungs-/EU-Stufenbau-Analyse, Stufe D `LeverageScorecard` + `CitationVerifier`, Gold-Set & RAGAS-Eval-Suite (`--strict-citations`).
- [x] **Phase 3: Bürgerportal, WebGL-Graph & Demokratie-Werkzeuge**
  - FastAPI + SSE-Streaming, Next.js Editorial-Portal (`strict: true`), Sigma.js + Graphology WebGL-Rechtsgraph, React Flow Kausalbaum, Z3-Interaktiv-Labor, 1-Klick-WCAG-HTML-Tabellen, Petitions-Assistent (`petition.bundestag.de` / Nds. Landtag / openPetition), Abgeordnetenwatch-Router, § 47 VwGO Dossier.
- [x] **Phase 4: Föderale Skalierung 16 Länder, OLDP & HUDOC**
  - `StateLawConnector`-Plugin-System für alle 16 Länder (`robots.txt`-Guard, DNG-Open-Data-Generator), Open Legal Data API/JSONL-Connector, HUDOC / HUDOC-EXEC Connector.
- [x] **Phase 5: Vernetzter Jura-Recherche-Assistent (Dual-Mode)**
  - Modus A („Öffentlicher Rechts-Kompass“, RDG-Guardrail), Modus B („Jura-Research-Copilot“, § 3 BRAO), ZDR-Schutz & CitationVerifier.

## Nächste Community-Meilensteine (Post-v1.0)
- [ ] Vollimport des C-DBR-Bulk-Korpus (6.136 Bundesgesetze) und der CE-Bundesgerichts-Korpora (~163.923 Urteile) mit lokalem Qwen3-Embedding-4B / BGE-M3 auf GPU-Server.
- [ ] Ausbau des Gold-Sets in `tests/eval/` von 54 kuratierten Prüffällen auf 200+ begutachtete Fälle durch juristische Reviewer.
- [ ] Automatisierte E-GVBl-PDF-Pipeline (mit Layout-Parsern, nicht naivem LLM-Loop) für alle noch fehlenden Landesverkündungsblätter.
- [ ] Mehrsprachige EU-Richtlinien-Alignment-Ansicht (DE / EN / FR aus EUR-Lex CELLAR Formex-XML).
