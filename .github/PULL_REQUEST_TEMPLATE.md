## Zusammenfassung
Kurzbeschreibung der Änderung und des betroffenen Moduls.

## Pflicht-Checkliste vor Merge
- [ ] `uv run pytest` & `uv run pytest tests/eval/ --strict-citations` sind lokal grün
- [ ] `uv run ruff check .` & `uv run mypy packages apps` fehlerfrei
- [ ] Falls Frontend geändert: `pnpm --dir apps/web lint && test && build` fehlerfrei + WCAG-2.2-Tabellen-Toggle vorhanden
- [ ] RDG-Compliance, EU-AI-Act-Transparenz (Art. 50), `robots.txt`/§ 44b UrhG und ZDR-Trennung geprüft
- [ ] `STATUS.md` (und ggf. `ROADMAP.md`) aktualisiert
