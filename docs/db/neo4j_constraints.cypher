// LexAudit DE/EU: Neo4j 5 Community Constraints & Indizes für bitemporalen SAT-Graph

CREATE CONSTRAINT legal_act_id_unique IF NOT EXISTS
FOR (a:LegalAct) REQUIRE a.act_id IS UNIQUE;

CREATE CONSTRAINT norm_unit_id_unique IF NOT EXISTS
FOR (n:NormUnit) REQUIRE n.norm_id IS UNIQUE;

CREATE CONSTRAINT temporal_version_id_unique IF NOT EXISTS
FOR (v:ComponentTemporalVersion) REQUIRE v.version_id IS UNIQUE;

CREATE CONSTRAINT court_decision_ecli_unique IF NOT EXISTS
FOR (d:CourtDecision) REQUIRE d.ecli IS UNIQUE;

CREATE CONSTRAINT parliamentary_doc_id_unique IF NOT EXISTS
FOR (p:ParliamentaryDoc) REQUIRE p.doc_id IS UNIQUE;

CREATE CONSTRAINT legal_concept_id_unique IF NOT EXISTS
FOR (c:LegalConcept) REQUIRE c.concept_id IS UNIQUE;

CREATE CONSTRAINT conflict_finding_id_unique IF NOT EXISTS
FOR (f:ConflictFinding) REQUIRE f.finding_id IS UNIQUE;

CREATE INDEX norm_unit_domain_idx IF NOT EXISTS
FOR (n:NormUnit) ON (n.legal_domain);

CREATE INDEX temporal_version_dates_idx IF NOT EXISTS
FOR (v:ComponentTemporalVersion) ON (v.valid_from, v.valid_to, v.status);

CREATE INDEX court_decision_date_idx IF NOT EXISTS
FOR (d:CourtDecision) ON (d.decision_date);
