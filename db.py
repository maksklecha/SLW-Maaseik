"""SQLite database: the (fake) KBC data + everything the Context Engine learns.

SQLite = a full SQL database in ONE file (kbc.db). It is built into Python,
so there is nothing to install. The same SQL would work on PostgreSQL at KBC.

Security rule used everywhere below: values are passed with "?" placeholders,
NEVER pasted into the SQL string with f-strings (that would allow SQL injection).
"""
import json
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "kbc.db"
SEED_FILE = Path(__file__).parent / "data" / "seed.json"

SCHEMA = """
CREATE TABLE customers (
    id TEXT PRIMARY KEY, name TEXT, age INTEGER, gender TEXT, occupation TEXT, city TEXT,
    language TEXT, children INTEGER, preferred_channel TEXT,
    active_hour_start INTEGER, active_hour_end INTEGER
);
CREATE TABLE merchants (name TEXT PRIMARY KEY, description TEXT);
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id TEXT REFERENCES customers(id),
    date TEXT, merchant TEXT REFERENCES merchants(name), amount_eur REAL,
    batch INTEGER, released INTEGER DEFAULT 0      -- released = the bank has "received" it
);
-- Classification cache: each company is classified ONCE, not once per customer
CREATE TABLE merchant_industries (
    merchant TEXT PRIMARY KEY REFERENCES merchants(name),
    scores_json TEXT, reason TEXT,
    status TEXT,        -- 'verified' | 'needs_review'
    method TEXT         -- 'gemini' | 'keyword fallback'
);
-- The living profile: every run adds a row, so we keep the history
CREATE TABLE industry_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id TEXT, industry TEXT,
    score REAL, computed_at TEXT
);
CREATE TABLE recommendations (
    id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id TEXT, industry TEXT,
    payload_json TEXT, created_at TEXT
);
CREATE TABLE notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id TEXT, industry TEXT,
    channel TEXT, moment TEXT, text TEXT, created_at TEXT
);
"""


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # rows behave like dicts: row["name"]
    return conn


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def reset_db() -> None:
    """Delete the database and rebuild it from data/seed.json (only batch 0 released)."""
    DB_PATH.unlink(missing_ok=True)
    seed = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    with connect() as conn:
        conn.executescript(SCHEMA)
        conn.executemany("INSERT INTO merchants VALUES (?, ?)",
                         [(m["name"], m["description"]) for m in seed["merchants"]])
        for c in seed["customers"]:
            conn.execute(
                "INSERT INTO customers VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (c["id"], c["name"], c["age"], c["gender"], c["occupation"], c["city"], c["language"],
                 c["children"], c["preferred_channel"], c["active_hours"][0], c["active_hours"][1]),
            )
            conn.executemany(
                "INSERT INTO transactions (customer_id, date, merchant, amount_eur, batch, released) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                [(c["id"], t["date"], t["merchant"], t["amount_eur"], t["batch"], int(t["batch"] == 0))
                 for t in c["transactions"]],
            )


def ensure_db() -> None:
    if not DB_PATH.exists():
        reset_db()


# --- Reading ----------------------------------------------------------------
def get_customers() -> list[dict]:
    with connect() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM customers ORDER BY id")]


def get_customer(customer_id: str) -> dict | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM customers WHERE id = ?", (customer_id,)).fetchone()
    return dict(row) if row else None


def get_transactions(customer_id: str) -> list[dict]:
    """Only the transactions the bank has already received (released = 1)."""
    with connect() as conn:
        rows = conn.execute(
            "SELECT t.date, t.merchant, m.description, t.amount_eur FROM transactions t "
            "JOIN merchants m ON m.name = t.merchant "
            "WHERE t.customer_id = ? AND t.released = 1 ORDER BY t.date",
            (customer_id,),
        )
        return [dict(r) for r in rows]


def has_unreleased(customer_id: str) -> bool:
    with connect() as conn:
        return conn.execute("SELECT 1 FROM transactions WHERE customer_id = ? AND released = 0",
                            (customer_id,)).fetchone() is not None


def release_next_batch(customer_id: str) -> None:
    """Demo: simulate that new transactions arrive at the bank."""
    with connect() as conn:
        row = conn.execute("SELECT MIN(batch) AS b FROM transactions WHERE customer_id = ? AND released = 0",
                           (customer_id,)).fetchone()
        if row["b"] is not None:
            conn.execute("UPDATE transactions SET released = 1 WHERE customer_id = ? AND batch = ?",
                         (customer_id, row["b"]))


def get_classification(merchant: str) -> dict | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM merchant_industries WHERE merchant = ?", (merchant,)).fetchone()
    if not row:
        return None
    return {**dict(row), "scores": json.loads(row["scores_json"])}


def get_all_classifications() -> list[dict]:
    with connect() as conn:
        return [{**dict(r), "scores": json.loads(r["scores_json"])}
                for r in conn.execute("SELECT * FROM merchant_industries ORDER BY merchant")]


def get_score_history(customer_id: str) -> list[dict]:
    with connect() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT industry, score, computed_at FROM industry_scores WHERE customer_id = ? ORDER BY id",
            (customer_id,))]


def get_recommendations(customer_id: str) -> list[dict]:
    with connect() as conn:
        rows = conn.execute("SELECT industry, payload_json FROM recommendations WHERE customer_id = ? ORDER BY id",
                            (customer_id,))
        return [{"industry": r["industry"], **json.loads(r["payload_json"])} for r in rows]


def get_notifications(customer_id: str) -> list[dict]:
    with connect() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM notifications WHERE customer_id = ? ORDER BY id DESC", (customer_id,))]


# --- Writing ----------------------------------------------------------------
def save_classification(merchant: str, scores: dict, reason: str, status: str, method: str) -> None:
    with connect() as conn:
        conn.execute("INSERT OR REPLACE INTO merchant_industries VALUES (?, ?, ?, ?, ?)",
                     (merchant, json.dumps(scores), reason, status, method))


def save_scores(customer_id: str, scores: dict[str, float]) -> None:
    with connect() as conn:
        conn.executemany("INSERT INTO industry_scores (customer_id, industry, score, computed_at) VALUES (?, ?, ?, ?)",
                         [(customer_id, ind, s, now()) for ind, s in scores.items()])


def replace_recommendations(customer_id: str, updates: list[dict]) -> None:
    """The For You page always shows the CURRENT situation, so old cards are replaced."""
    with connect() as conn:
        conn.execute("DELETE FROM recommendations WHERE customer_id = ?", (customer_id,))
        conn.executemany("INSERT INTO recommendations (customer_id, industry, payload_json, created_at) "
                         "VALUES (?, ?, ?, ?)",
                         [(customer_id, u["industry"], json.dumps(u), now()) for u in updates])


def already_notified(customer_id: str, industry: str) -> bool:
    with connect() as conn:
        return conn.execute("SELECT 1 FROM notifications WHERE customer_id = ? AND industry = ?",
                            (customer_id, industry)).fetchone() is not None


def save_notification(customer_id: str, industry: str, channel: str, moment: str, text: str) -> None:
    with connect() as conn:
        conn.execute("INSERT INTO notifications (customer_id, industry, channel, moment, text, created_at) "
                     "VALUES (?, ?, ?, ?, ?, ?)", (customer_id, industry, channel, moment, text, now()))
