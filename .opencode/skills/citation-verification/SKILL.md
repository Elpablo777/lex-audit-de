---
name: citation-verification
description: Deterministische Zitations-Brandmauer gegen juristische Halluzinationen in LexAudit DE/EU.
---
1. Lade stets den vollständigen Norm- oder Urteilstext aus dem lokalen Volltextspiegel (`StorageBackend`), niemals nur Vektor-Snippets.
2. Übergebe jeden generierten `ConflictFinding`- oder Assistenz-Output an `CitationVerifier.verify_finding(...)`.
3. Prüfe Existenz, Stichtags-Gültigkeit (`ComponentTemporalVersion`) und exakte Substring-Treffer der Zitate.
4. Kennzeichne fehlgeschlagene Outputs hart als `REJECTED_UNVERIFIED` und blockiere die Persistierung bzw. Frontend-Ausgabe.
5. Brich den Batch-Lauf ab, sobald `citation_error_rate > 0.08`.
