---
name: z3-modeling
description: Formale Übersetzung quantitativer deutscher Rechtsnormen in Z3-SMT-Constraints für mathematische Gegenbeweise.
---
1. Übersetze numerische Einkommens-, Vermögens-, Freibetrags- und Transferformeln in lineare/stückweise-lineare Z3-Real/Int-Constraints (`z3.Optimize` / `z3.Solver`).
2. Dokumentiere pro Parameter den genauen Paragraphen (z. B. § 11b SGB II, § 19 WoGG, § 6a BKGG, § 13a ErbStG).
3. Liefere bei `sat` stets ein reproduzierbares Gegenbeispiel mit konkreten Eingabe- und Zwischenwerten sowie Grenzbelastungsquote.
4. Decke Schein-Konflikte durch realistische Vergleichsfälle in den Tests ab.
