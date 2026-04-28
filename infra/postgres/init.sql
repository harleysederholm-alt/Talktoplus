-- TALK TO+ BDaaS — PostgreSQL initialization
-- Multi-tenant schema with Row-Level Security (RLS).
-- Applied automatically by docker-entrypoint at first boot.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- --------------------------------------------------------------------
-- Tenants (no RLS — they are the boundary)
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tenants (
    id           TEXT PRIMARY KEY,
    name         TEXT NOT NULL,
    sector       TEXT NOT NULL,
    sector_hash  TEXT NOT NULL,
    description  TEXT,
    active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- --------------------------------------------------------------------
-- Users
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id              TEXT PRIMARY KEY,
    email           CITEXT UNIQUE NOT NULL,
    full_name       TEXT NOT NULL,
    password_hash   TEXT NOT NULL,
    role            TEXT NOT NULL,
    tenant_id       TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    locale          TEXT NOT NULL DEFAULT 'fi',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE EXTENSION IF NOT EXISTS citext;
CREATE INDEX IF NOT EXISTS users_tenant_idx ON users(tenant_id);

-- --------------------------------------------------------------------
-- Signals (RLS-protected by tenant_id)
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS signals (
    id                    TEXT PRIMARY KEY,
    tenant_id             TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    content               TEXT NOT NULL,
    source                TEXT NOT NULL DEFAULT 'manual',
    business_unit         TEXT NOT NULL,
    author                TEXT NOT NULL,
    submitted_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    status                TEXT NOT NULL DEFAULT 'pending',
    risk_level            TEXT,
    confidence            NUMERIC(3,2),
    summary               TEXT,
    execution_gaps        JSONB NOT NULL DEFAULT '[]'::jsonb,
    hidden_assumptions    JSONB NOT NULL DEFAULT '[]'::jsonb,
    facilitator_questions JSONB NOT NULL DEFAULT '[]'::jsonb,
    category              TEXT,
    validated_by          TEXT,
    validated_at          TIMESTAMPTZ,
    validation_note       TEXT,
    override_risk_level   TEXT,
    swarm_fragment_id     TEXT,
    action_card_id        TEXT
);
CREATE INDEX IF NOT EXISTS signals_tenant_time_idx ON signals(tenant_id, submitted_at DESC);
CREATE INDEX IF NOT EXISTS signals_status_idx ON signals(status);

ALTER TABLE signals ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_signals ON signals
    USING (tenant_id = current_setting('app.tenant_id', true));

-- --------------------------------------------------------------------
-- Action Cards
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS action_cards (
    id                   TEXT PRIMARY KEY,
    tenant_id            TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    signal_id            TEXT NOT NULL,
    title                TEXT NOT NULL,
    summary              TEXT NOT NULL,
    playbook             JSONB NOT NULL DEFAULT '[]'::jsonb,
    rag_context_used     JSONB NOT NULL DEFAULT '[]'::jsonb,
    swarm_patterns_used  JSONB NOT NULL DEFAULT '[]'::jsonb,
    impact_score         INTEGER,
    swarm_verified       BOOLEAN NOT NULL DEFAULT FALSE,
    swarm_verified_count INTEGER NOT NULL DEFAULT 0,
    status               TEXT NOT NULL DEFAULT 'pending_validation',
    facilitator          TEXT,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS cards_tenant_idx ON action_cards(tenant_id);
ALTER TABLE action_cards ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_cards ON action_cards
    USING (tenant_id = current_setting('app.tenant_id', true));

-- --------------------------------------------------------------------
-- Strategy Docs (vectors live in Qdrant)
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS strategy_docs (
    id          TEXT PRIMARY KEY,
    tenant_id   TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    title       TEXT NOT NULL,
    content     TEXT NOT NULL,
    chunks      INTEGER NOT NULL DEFAULT 1,
    uploaded_by TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE strategy_docs ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_docs ON strategy_docs
    USING (tenant_id = current_setting('app.tenant_id', true));

-- --------------------------------------------------------------------
-- Swarm Fragments (anonymous — no RLS, only sector_hash)
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS swarm_fragments (
    id              TEXT PRIMARY KEY,
    sector_hash     TEXT NOT NULL,
    sector_display  TEXT,
    risk_level      TEXT NOT NULL,
    confidence      NUMERIC(3,2),
    category        TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS frags_sector_time_idx ON swarm_fragments(sector_hash, created_at DESC);
CREATE INDEX IF NOT EXISTS frags_category_idx ON swarm_fragments(category);

-- --------------------------------------------------------------------
-- Audit log (immutable)
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_log (
    id          TEXT PRIMARY KEY,
    event       TEXT NOT NULL,
    user_id     TEXT,
    tenant_id   TEXT,
    payload     JSONB NOT NULL DEFAULT '{}'::jsonb,
    delivered   BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS audit_event_idx ON audit_log(event);
CREATE INDEX IF NOT EXISTS audit_undelivered_idx ON audit_log(delivered) WHERE delivered = FALSE;
