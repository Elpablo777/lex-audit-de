# Compliance- & Risiko-Bewertung: EU AI Act, RDG, UrhG & DSGVO

**Stand:** 27. November 2026  
**System:** LexAudit DE/EU (Föderales Rechts-Audit- & Demokratie-Portal)  

---

## 1. EU AI Act (VO (EU) 2024/1689 + Digital Omnibus VO 2026/1744)

### 1.1 Dokumentation der Nicht-Hochrisiko-Bewertung (Art. 6 Abs. 3 & Abs. 4 KI-VO)
Gemäß Anhang III Nr. 8 der KI-Verordnung gelten KI-Systeme in der Rechtspflege und bei demokratischen Prozessen grundsätzlich nur dann als Hochrisiko-Systeme, wenn sie Justizbehörden bei der Sachverhalts- und Rechtsanwendung auf **konkrete Einzelfälle** unterstützen (Nr. 8a) oder das Wahlverhalten durch **personalisierte Beeinflussung / politisches Profiling** steuern (Nr. 8b).

Unter Anwendung der offiziellen Leitlinien der Europäischen Kommission und der Ausnahme nach **Art. 6 Abs. 3 KI-VO** erfüllt LexAudit DE/EU kein Hochrisiko-Profil, da alle folgenden technischen Invarianten im Code erzwungen werden:

1. **Keine Einzelfall-Rechtsanwendung durch Justiz oder Laien:** Alle öffentlichen Audit-Befunde, Konfliktkarten und der Bürger-Rechtskompass arbeiten ausschließlich auf **abstrakter Norm- und Systemebene** (Norm-zu-Norm- und Norm-zu-Leitsatz-Relationen).
2. **Kein Personen-Profiling und keine Wahlempfehlung:** Das System speichert keine Wählerprofile, berechnet keine individuellen Parteipräferenzen (kein Wahl-O-Mat-Scoring) und spielt kein politisches Micro-Targeting aus. Der Abgeordneten-Router ordnet ausschließlich sachlich nach **Wahlkreis/PLZ** und **zuständigem Fachausschuss** über die offene Abgeordnetenwatch API v2 (CC0 1.0).
3. **Rein vorbereitendes, transparentes Analysewerkzeug:** Sämtliche generierten Befunde durchlaufen vor Anzeige den deterministischen `CitationVerifier` und verlinken direkt auf die amtlichen Primärquellen (ELI, ECLI, `source_url`).

### 1.2 Transparenzpflichten nach Art. 50 KI-VO (geltend seit 02.08.2026)
Jede KI-gestützte Zusammenfassung, Konfliktanalyse, Formulierungshilfe und Assistenz-Antwort trägt im API-Payload (`ai_transparency_notice`) sowie sichtbar im Frontend die Pflichtkennzeichnung:
> **Hinweis nach Art. 50 KI-VO:** Diese Übersicht bzw. Textvorlage wurde unter Einsatz eines KI-gestützten Analyse- und Verifikationssystems auf Basis amtlicher Primärquellen erstellt und ersetzt keine eigenständige juristische Prüfung.

---

## 2. Rechtsdienstleistungsgesetz (§ 2 Abs. 1, § 3 RDG; § 3a UWG)

- **Abgrenzung:** Allgemeine, abstrakte Rechtsinformation, systematische Normvergleiche sowie rechtspolitische Petitions- und Abgeordneten-Vorlagen stellen **keine** erlaubnispflichtige Rechtsdienstleistung im konkreten Einzelfall dar (§ 2 Abs. 1 RDG).
- **Technischer Guardrail (`RDGComplianceGuard`):** Da bloße UI-Disclaimer einen RDG-Verstoß bei frei subsumierenden Chatbots nicht heilen (vgl. BGH *Smartlaw* I ZR 113/20 sowie OLG Hamm vom 12.05.2026 zur Haftungszurechnung von KI-Chatbot-Antworten), prüft der `RDGComplianceGuard` jede öffentliche Nutzeranfrage **vor** der Verarbeitung:
  - Erkennt er konkrete Einzelfall-Indikatoren („mein Fall“, „habe ich Anspruch“, „meine Kündigung“, „mein Bescheid“, „kann ich klagen“, konkrete Fristberechnung für persönliche Akten etc.), blockiert er die Subsumtion deterministisch und liefert ausschließlich abstrakten Systemkontext + Verweis auf Rechtsanwältinnen/Rechtsanwälte, Verbraucherzentralen oder öffentliche Rechtsantragsstellen.
- **Phase-5-Modus B (B2B-Copilot):** Ausschließlich als professionelles Recherche-Werkzeug für Volljuristinnen und Volljuristen unter berufsrechtlicher Aufsicht und Eigenverantwortung nach **§ 3 BRAO** vorgesehen.

---

## 3. Urheber-, Datenbank- und Text-and-Data-Mining-Recht (§ 5, § 44b, §§ 87a ff. UrhG; DNG)

1. **Gemeinfreie Primärquellen (§ 5 Abs. 1 UrhG):** Gesetze, Verordnungen, amtliche Leitsätze und Gerichtsentscheidungen aus NeuRIS, Gesetze-im-Internet, Rechtsprechung-im-Internet, BGBl (`recht.bund.de`), `verkuendung-niedersachsen.de`, EUR-Lex (`Beschluss 2011/833/EU`) und HUDOC werden bevorzugt angebunden.
2. **Offene Lizenzen mit Attribution:** Open Legal Data (`ODbL v1.0`), Abgeordnetenwatch (`CC0 1.0`), Bundestag DIP (`dl-de/by-2-0`).
3. **Schutz fremder Datenbankwerke (§§ 87a ff. UrhG) & § 44b UrhG:** Kein Massendownload und keine Übernahme redaktioneller Leitsätze aus `juris`, `beck-online` oder Wolters Kluwer `NI-VORIS`. Jeder Landesportal-Konnektor prüft zwingend `robots.txt` (maschinenlesbarer Nutzungsvorbehalt nach § 44b Abs. 3 UrhG) und nutzt bei verschlossenen Portalen statt Scraping den integrierten **DNG-Open-Data-Anfrage-Generator**.

---

## 4. Datenschutz & Zero-Data-Retention (DSGVO / Art. 10 DSGVO / Post-Dragos Nov 2026)

1. **PII-Filter vor Speicherung/Prompt:** Alle Gerichtstexte durchlaufen einen deterministischen PII-Sanitizer (Bereinigung verbliebener Klarnamen-/E-Mail-/IBAN-/Steuer-ID-Muster).
2. **Strikte Client-Trennung:**
   - `PublicLawLLMClient`: Ausschließlich für gemeinfreie §-5-UrhG-Rechtstexte (darf `:free` oder kostengünstige OpenRouter-Modelle nutzen).
   - `CitizenPrivacyLLMClient`: Für jegliche Bürgereingaben, Petitionsentwürfe oder Recherche-Anfragen — erzwingt `provider.zdr: true` im OpenRouter-Request oder lokales Ollama/LM Studio bzw. den deterministischen Offline-Pfad. Keine Secrets und kein unverschlüsseltes Prompt-Logging von Bürgereingaben.
