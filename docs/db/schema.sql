-- LexAudit DE/EU: PostgreSQL 17 + pgvector Schema (Bitemporaler Wissens- & Vektorkern)
-- Hinweis: Erfordert PostgreSQL 17+ mit Extension `vector` (pgvector >= 0.7).

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- 1. Rechtsakte (Stabile Normgeber-Identität, angelehnt an ELI/LRMoo)
CREATE TABLE IF NOT EXISTS legal_acts (
    act_id              TEXT PRIMARY KEY,
    eli_uri             TEXT UNIQUE,
    title               TEXT NOT NULL,
    short_title         TEXT NOT NULL DEFAULT '',
    jurisdiction_level  TEXT NOT NULL CHECK (jurisdiction_level IN ('international', 'eu', 'bund', 'land', 'kommunal')),
    land_code           TEXT,
    norm_type           TEXT NOT NULL CHECK (norm_type IN (
                            'treaty', 'eu_regulation', 'eu_directive', 'constitution',
                            'formal_statute', 'ordinance', 'municipal_statute', 'admin_directive'
                        )),
    hierarchy_rank      SMALLINT NOT NULL CHECK (hierarchy_rank BETWEEN 1 AND 6),
    promulgation_date   DATE,
    source_url          TEXT NOT NULL,
    license             TEXT NOT NULL DEFAULT '§ 5 UrhG gemeinfrei',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Einzelnormen (§ / Artikel) mit stabiler Identität
CREATE TABLE IF NOT EXISTS norm_units (
    norm_id             TEXT PRIMARY KEY,
    act_id              TEXT NOT NULL REFERENCES legal_acts(act_id) ON DELETE CASCADE,
    eli_uri             TEXT,
    designation         TEXT NOT NULL,
    heading             TEXT NOT NULL DEFAULT '',
    hierarchy_rank      SMALLINT NOT NULL CHECK (hierarchy_rank BETWEEN 1 AND 6),
    legal_domain        TEXT NOT NULL DEFAULT 'allgemein',
    status              TEXT NOT NULL DEFAULT 'in_force' CHECK (status IN ('in_force', 'repealed', 'pending', 'expired')),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3. Bitemporale Normfassungen (niemals überschreiben, stets neue Version anlegen!)
CREATE TABLE IF NOT EXISTS temporal_versions (
    version_id              TEXT PRIMARY KEY,
    norm_id                 TEXT NOT NULL REFERENCES norm_units(norm_id) ON DELETE CASCADE,
    valid_from              DATE NOT NULL,
    valid_to                DATE,
    promulgation_date       DATE,
    status                  TEXT NOT NULL CHECK (status IN ('in_force', 'repealed', 'pending', 'expired')),
    text_hash               CHAR(64) NOT NULL,
    full_text               TEXT NOT NULL,
    context_header          TEXT NOT NULL,
    supersedes_version_id   TEXT REFERENCES temporal_versions(version_id),
    tsv                     TSVECTOR GENERATED ALWAYS AS (
                                to_tsvector('german', coalesce(context_header, '') || ' ' || full_text)
                            ) STORED,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (norm_id, valid_from, text_hash)
);

CREATE INDEX IF NOT EXISTS idx_temporal_versions_norm_dates
    ON temporal_versions (norm_id, valid_from, valid_to);
CREATE INDEX IF NOT EXISTS idx_temporal_versions_tsv
    ON temporal_versions USING GIN (tsv);

-- 4. Gerichtsentscheidungen (Volltextspiegel + Leitsatz + Tenor)
CREATE TABLE IF NOT EXISTS court_decisions (
    decision_id         TEXT PRIMARY KEY,
    ecli                TEXT UNIQUE NOT NULL,
    court_level         TEXT NOT NULL CHECK (court_level IN (
                            'egmr', 'eugh', 'bverfg', 'oberstes_bundesgericht', 'ovg_oberlandesgericht', 'fachgericht'
                        )),
    court_name          TEXT NOT NULL,
    decision_date       DATE NOT NULL,
    file_number         TEXT NOT NULL,
    leitsatz            TEXT NOT NULL DEFAULT '',
    tenor               TEXT NOT NULL DEFAULT '',
    full_text           TEXT NOT NULL,
    source_url          TEXT NOT NULL,
    license             TEXT NOT NULL DEFAULT '§ 5 UrhG gemeinfrei',
    tsv                 TSVECTOR GENERATED ALWAYS AS (
                            to_tsvector('german', coalesce(leitsatz, '') || ' ' || coalesce(tenor, '') || ' ' || full_text)
                        ) STORED,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_court_decisions_tsv ON court_decisions USING GIN (tsv);
CREATE INDEX IF NOT EXISTS idx_court_decisions_date ON court_decisions (decision_date DESC);

-- 5. Separate Vektor-Tabellen (Skopek-2026-Pattern, Standard-Dim 1024 für BGE-M3 / Qwen3-4B-Adapter)
-- WICHTIG: Vor Vektor-Suchen zwingend ausführen: SET LOCAL hnsw.ef_search = 200;
CREATE TABLE IF NOT EXISTS norm_chunks (
    chunk_id            TEXT PRIMARY KEY,
    version_id          TEXT NOT NULL REFERENCES temporal_versions(version_id) ON DELETE CASCADE,
    norm_id             TEXT NOT NULL REFERENCES norm_units(norm_id) ON DELETE CASCADE,
    chunk_index         INTEGER NOT NULL,
    context_header      TEXT NOT NULL,
    content             TEXT NOT NULL,
    embedding           VECTOR(1024) NOT NULL,
    tsv                 TSVECTOR GENERATED ALWAYS AS (
                            to_tsvector('german', context_header || ' ' || content)
                        ) STORED
);

CREATE INDEX IF NOT EXISTS idx_norm_chunks_hnsw
    ON norm_chunks USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 128);
CREATE INDEX IF NOT EXISTS idx_norm_chunks_tsv ON norm_chunks USING GIN (tsv);

CREATE TABLE IF NOT EXISTS case_chunks (
    chunk_id            TEXT PRIMARY KEY,
    decision_id         TEXT NOT NULL REFERENCES court_decisions(decision_id) ON DELETE CASCADE,
    chunk_kind          TEXT NOT NULL CHECK (chunk_kind IN ('leitsatz', 'tenor', 'reasoning')),
    chunk_index         INTEGER NOT NULL,
    context_header      TEXT NOT NULL,
    content             TEXT NOT NULL,
    embedding           VECTOR(1024) NOT NULL,
    tsv                 TSVECTOR GENERATED ALWAYS AS (
                            to_tsvector('german', context_header || ' ' || content)
                        ) STORED
);

CREATE INDEX IF NOT EXISTS idx_case_chunks_hnsw
    ON case_chunks USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 128);
CREATE INDEX IF NOT EXISTS idx_case_chunks_tsv ON case_chunks USING GIN (tsv);

-- 6. Verifizierte Befunde & CitationProof-Audit-Spur
CREATE TABLE IF NOT EXISTS conflict_findings (
    finding_id          TEXT PRIMARY KEY,
    title               TEXT NOT NULL,
    conflict_class      SMALLINT NOT NULL CHECK (conflict_class BETWEEN 1 AND 5),
    severity            TEXT NOT NULL CHECK (severity IN ('critical', 'high', 'medium', 'low')),
    verification_status TEXT NOT NULL CHECK (verification_status IN ('VERIFIED', 'REJECTED_UNVERIFIED')),
    payload_json        JSONB NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audit_runs (
    run_id              TEXT PRIMARY KEY,
    started_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at         TIMESTAMPTZ,
    total_candidates    INTEGER NOT NULL DEFAULT 0,
    verified_count      INTEGER NOT NULL DEFAULT 0,
    rejected_count      INTEGER NOT NULL DEFAULT 0,
    citation_error_rate DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    estimated_cost_usd  DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    status              TEXT NOT NULL CHECK (status IN ('running', 'completed', 'aborted_guardrail', 'failed'))
);
