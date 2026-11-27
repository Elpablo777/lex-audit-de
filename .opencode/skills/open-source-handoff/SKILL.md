---
name: open-source-handoff
description: Sicherstellen, dass externe Open-Source-Mitwirkende und KI-Agenten jederzeit sauber weiterarbeiten können.
---
1. Aktualisiere `STATUS.md` und `ROADMAP.md` nach jedem Meilenstein mit exakten, lokal ausgeführten Test- und Build-Ergebnissen.
2. Halte `.env.example`, `AGENTS.md`, `CONTRIBUTING.md` und `docs/architecture/MASTERPLAN.md` synchron zum tatsächlichen Code.
3. Stelle sicher, dass alle Unit- und Eval-Tests sowohl mit Docker (Postgres/Neo4j) als auch ohne externe Keys/Container reproduzierbar grün durchlaufen.
