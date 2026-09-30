-- KBC For You - database schema (SQLite; the same SQL works on PostgreSQL)
-- "released = 0" rows are events the bank has NOT received yet: the demo button releases them.

-- ===== KBC data (input) =====================================================
CREATE TABLE customers (
    id                TEXT PRIMARY KEY,
    name              TEXT NOT NULL,
    age               INTEGER NOT NULL,
    gender            TEXT,                -- stored, but NEVER used to choose products
    occupation        TEXT,
    city              TEXT,
    language          TEXT NOT NULL,       -- 'nl' | 'fr' | 'en'
    children          INTEGER NOT NULL,
    monthly_income    REAL NOT NULL,
    preferred_channel TEXT NOT NULL,       -- 'app' | 'email'
    active_hour_start INTEGER NOT NULL,    -- when they usually use their phone / are reachable
    active_hour_end   INTEGER NOT NULL
);

CREATE TABLE merchants (
    name        TEXT PRIMARY KEY,
    description TEXT NOT NULL
);

-- Transactional data
CREATE TABLE transactions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id TEXT NOT NULL REFERENCES customers(id),
    ts          TEXT NOT NULL,             -- timestamp
    merchant    TEXT NOT NULL REFERENCES merchants(name),
    amount      REAL NOT NULL,             -- in the original currency
    currency    TEXT NOT NULL,
    amount_eur  REAL NOT NULL,
    country     TEXT NOT NULL,
    batch       INTEGER NOT NULL,
    released    INTEGER NOT NULL DEFAULT 0
);

-- Behavioral data: actions inside the KBC app
CREATE TABLE app_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id TEXT NOT NULL REFERENCES customers(id),
    ts          TEXT NOT NULL,
    event       TEXT NOT NULL,             -- e.g. 'viewed_child_savings', 'balance_check_month_end'
    detail      TEXT,
    batch       INTEGER NOT NULL,
    released    INTEGER NOT NULL DEFAULT 0
);

-- Contextual data: micro-moment triggers (location, time)
CREATE TABLE context_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id TEXT NOT NULL REFERENCES customers(id),
    ts          TEXT NOT NULL,
    event       TEXT NOT NULL,             -- e.g. 'airport_abroad'
    detail      TEXT,
    country     TEXT,
    batch       INTEGER NOT NULL,
    released    INTEGER NOT NULL DEFAULT 0
);

-- ===== What the Context Engine learns (output) ===============================
-- Classification cache: every company is classified ONCE, not once per customer
CREATE TABLE merchant_industries (
    merchant    TEXT PRIMARY KEY REFERENCES merchants(name),
    scores_json TEXT NOT NULL,             -- {"travel": 9, "construction": 0, ...}
    reason      TEXT,
    status      TEXT NOT NULL,             -- 'verified' | 'needs_review'
    method      TEXT NOT NULL              -- 'gemini' | 'keyword fallback'
);

-- The living profile: history of intent scores (a new row whenever new data arrived)
CREATE TABLE intent_scores (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id TEXT NOT NULL,
    intent      TEXT NOT NULL,
    score       REAL NOT NULL,
    data_version INTEGER NOT NULL,          -- how many events the engine had seen
    computed_at TEXT NOT NULL
);

-- Current For You page content (replaced when the situation changes)
CREATE TABLE for_you_page (
    customer_id TEXT PRIMARY KEY,
    signature   TEXT NOT NULL,             -- which intents it was built for (avoids new LLM calls)
    content_json TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE notifications (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id TEXT NOT NULL,
    intents     TEXT NOT NULL,
    channel     TEXT NOT NULL,
    moment      TEXT NOT NULL,
    text        TEXT NOT NULL,
    created_at  TEXT NOT NULL
);

CREATE TABLE feedback (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id TEXT NOT NULL,
    widget_id   TEXT NOT NULL,
    reaction    TEXT NOT NULL,             -- 'interested' | 'not_for_me' | 'used'
    created_at  TEXT NOT NULL
);
