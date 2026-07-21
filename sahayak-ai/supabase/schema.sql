-- ===========================================================================
-- Sahayak AI — Supabase / PostgreSQL schema (DDL)
-- Run in the Supabase SQL editor. The backend uses these tables verbatim when
-- SUPABASE_URL + service key are configured; otherwise it runs fully in-memory.
-- Column shapes mirror backend/app/core/supabase_store.py 1:1.
-- ===========================================================================

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ---------------------------------------------------------------------------
-- Enumerations
-- ---------------------------------------------------------------------------
DO $$ BEGIN
  CREATE TYPE priority_level AS ENUM ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE task_status AS ENUM ('PENDING', 'IN_PROGRESS', 'COMPLETED');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE government_id_type AS ENUM ('Aadhaar', 'PAN', 'Ration Card', 'Voter ID');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- ---------------------------------------------------------------------------
-- Beneficiaries core table
-- PII: only a MASKED id + a dedup HASH are stored. The raw government ID number
-- is never persisted.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS beneficiaries (
    id                    TEXT PRIMARY KEY,
    org_id                TEXT NOT NULL DEFAULT 'default-org',
    name                  VARCHAR(255) NOT NULL,
    age                   INT,
    gender                VARCHAR(50),
    annual_income         NUMERIC(12, 2),
    state_location        VARCHAR(100),
    is_disabled           BOOLEAN DEFAULT FALSE,
    government_id_type    government_id_type,
    government_id_masked  TEXT,
    government_id_hash    TEXT,               -- SHA-256 of normalized id, for dedup
    medical_conditions    TEXT[] DEFAULT '{}',
    current_priority      priority_level DEFAULT 'MEDIUM',
    urgency               JSONB,              -- full UrgencyAssessment
    created_at            TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS beneficiaries_org_idx ON beneficiaries (org_id);
CREATE INDEX IF NOT EXISTS beneficiaries_gidhash_idx
    ON beneficiaries (org_id, government_id_hash);
CREATE INDEX IF NOT EXISTS beneficiaries_priority_idx
    ON beneficiaries (org_id, current_priority);

-- ---------------------------------------------------------------------------
-- Documents
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS documents (
    id              TEXT PRIMARY KEY,
    org_id          TEXT NOT NULL DEFAULT 'default-org',
    beneficiary_id  TEXT REFERENCES beneficiaries(id) ON DELETE CASCADE,
    file_name       VARCHAR(255) NOT NULL,
    file_url        TEXT NOT NULL,
    extracted_text  TEXT,
    parsed_metadata JSONB,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS documents_ben_idx ON documents (beneficiary_id);

-- ---------------------------------------------------------------------------
-- Tasks / timeline
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tasks (
    id              TEXT PRIMARY KEY,
    org_id          TEXT NOT NULL DEFAULT 'default-org',
    beneficiary_id  TEXT REFERENCES beneficiaries(id) ON DELETE CASCADE,
    title           VARCHAR(255) NOT NULL,
    description     TEXT,
    due_date        DATE,
    status          task_status DEFAULT 'PENDING',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS tasks_org_idx ON tasks (org_id, due_date, status);

-- ---------------------------------------------------------------------------
-- Welfare schemes master vector matrix (shared reference data, no org scope)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS welfare_schemes (
    id                            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title                         VARCHAR(255) NOT NULL,
    description                   TEXT NOT NULL,
    eligibility_criteria_summary  TEXT,
    category                      VARCHAR(100),
    eligibility_rules             JSONB,            -- structured rule scorer input
    scheme_vector_embedding       VECTOR(1536),     -- text-embedding-3-small
    created_at                    TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS welfare_schemes_embedding_idx
    ON welfare_schemes USING ivfflat (scheme_vector_embedding vector_cosine_ops)
    WITH (lists = 100);

-- ---------------------------------------------------------------------------
-- Semantic match function (cosine similarity via pgvector) — optional; the
-- backend can also score in-process. Handy for direct SQL / edge functions.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION match_welfare_schemes(
    query_embedding VECTOR(1536),
    match_threshold FLOAT DEFAULT 0.0,
    match_count     INT DEFAULT 6
)
RETURNS TABLE (id UUID, title VARCHAR, description TEXT, category VARCHAR, similarity FLOAT)
LANGUAGE sql STABLE AS $$
    SELECT ws.id, ws.title, ws.description, ws.category,
           1 - (ws.scheme_vector_embedding <=> query_embedding) AS similarity
    FROM welfare_schemes ws
    WHERE 1 - (ws.scheme_vector_embedding <=> query_embedding) > match_threshold
    ORDER BY ws.scheme_vector_embedding <=> query_embedding
    LIMIT match_count;
$$;

-- ---------------------------------------------------------------------------
-- Row-Level Security
-- NOTE: the backend connects with the service key (bypasses RLS) and enforces
-- org scoping in every query. These policies protect any direct client access
-- (e.g. the Supabase JS client) and scope rows to the caller's org_id claim.
-- ---------------------------------------------------------------------------
ALTER TABLE beneficiaries ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents     ENABLE ROW LEVEL SECURITY;
ALTER TABLE tasks         ENABLE ROW LEVEL SECURITY;
ALTER TABLE welfare_schemes ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS beneficiaries_org_isolation ON beneficiaries;
CREATE POLICY beneficiaries_org_isolation ON beneficiaries
    USING (org_id = COALESCE(auth.jwt() -> 'app_metadata' ->> 'org_id', 'default-org'));

DROP POLICY IF EXISTS documents_org_isolation ON documents;
CREATE POLICY documents_org_isolation ON documents
    USING (org_id = COALESCE(auth.jwt() -> 'app_metadata' ->> 'org_id', 'default-org'));

DROP POLICY IF EXISTS tasks_org_isolation ON tasks;
CREATE POLICY tasks_org_isolation ON tasks
    USING (org_id = COALESCE(auth.jwt() -> 'app_metadata' ->> 'org_id', 'default-org'));

DROP POLICY IF EXISTS welfare_schemes_read_all ON welfare_schemes;
CREATE POLICY welfare_schemes_read_all ON welfare_schemes
    FOR SELECT USING (auth.role() = 'authenticated');
