---
name: rdg-compliance
description: Technische Absicherung gegen unerlaubte Einzelfall-Rechtsberatung (§ 2 Abs. 1 RDG) und EU-AI-Act-Hochrisikoeinstufung.
---
1. Leite jede öffentliche Nutzeranfrage zuerst durch `RDGComplianceGuard.evaluate_query(...)`.
2. Erkenne Einzelfall-Subsumtionsmuster („mein Fall“, „habe ich Anspruch“, „meine Kündigung“, „kann ich klagen“) und blockiere die Einzelfallprüfung deterministisch.
3. Antworte bei Blockierung mit sachlichem Verweis auf Rechtsanwältinnen/Rechtsanwälte, Verbraucherzentralen oder öffentliche Beratungsstellen — niemals mit einer Erfolgsprognose für den Einzelfall.
4. Hänge an jede Ausgabe den Art.-50-KI-Transparenzhinweis an.
