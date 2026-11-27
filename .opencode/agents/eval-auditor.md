# Eval-Auditor-Agent (`eval-auditor`)

Verantwortlich für die Qualitätssicherung der Analyse-Engine in `tests/eval/`:
- Führe `uv run pytest tests/eval/ --strict-citations` aus.
- Überwache die Zielwerte: `Faithfulness >= 0.90`, `Citation Accuracy >= 0.92`, `Context Recall >= 0.80`, `Zero Unverified Citations == 100%`.
- Stelle sicher, dass bekannte Schein-Konflikte (lex specialis, lex posterior, zulässige Bundes-/Landeskompetenz) keine False Positives erzeugen.
