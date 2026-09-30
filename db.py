"""SQLite database access. The database itself is defined in database/schema.sql and
filled with 3 fake customers from database/seed.sql.

SQLite = a full SQL database in ONE file (kbc.db), built into Python - nothing to install.
Open kbc.db with a free viewer (e.g. "DB Browser for SQLite") to look inside.

Security rule used everywhere below: values are passed with "?" placeholders,
NEVER pasted into the SQL string with f-strings (that would allow SQL injection).
"""
import json
import sqlite3
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent
DB_PATH = ROOT / "kbc.db"
SCHEMA_FILE = ROOT / "database" / "schema.sql"
SEED_FILE = ROOT / "database" / "seed.sql"

EVENT_TABLES = ("transactions", "app_events", "context_events")  # fixed names, never user input


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # rows behave like dicts: row["name"]
    return conn


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def reset_db() -> None:
    """Delete kbc.db and rebuild it from the two .sql files."""
    DB_PATH.unlink(missing_ok=True)
    with connect() as conn:
        conn.executescript(SCHEMA_FILE.read_text(encoding="utf-8"))
        conn.executescript(SEED_FILE.read_text(encoding="utf-8"))


def ensure_db() -> None:
    if not DB_PATH.exists():
        reset_db()


def _rows(sql: str, params: tuple = ()) -> list[dict]:
    with connect() as conn:
        return [dict(r) for r in conn.execute(sql, params)]


# --- Input data -----------------------------------------------------------------
def get_customers() -> list[dict]:
    return _rows("SELECT * FROM customers ORDER BY id")


def get_customer(customer_id: str) -> dict | None:
    rows = _rows("SELECT * FROM customers WHERE id = ?", (customer_id,))
    return rows[0] if rows else None


def get_transactions(customer_id: str) -> list[dict]:
    """Only what the bank has already received (released = 1)."""
    return _rows(
        "SELECT t.ts, t.merchant, m.description, t.amount, t.currency, t.amount_eur, t.country "
        "FROM transactions t JOIN merchants m ON m.name = t.merchant "
        "WHERE t.customer_id = ? AND t.released = 1 ORDER BY t.ts", (customer_id,))


def get_app_events(customer_id: str) -> list[dict]:
    return _rows("SELECT ts, event, detail FROM app_events WHERE customer_id = ? AND released = 1 ORDER BY ts",
                 (customer_id,))


def get_context_events(customer_id: str) -> list[dict]:
    return _rows("SELECT ts, event, detail, country FROM context_events "
                 "WHERE customer_id = ? AND released = 1 ORDER BY ts", (customer_id,))


def data_version(customer_id: str) -> int:
    """Number of received events. Changes only when new data arrives."""
    with connect() as conn:
        return sum(conn.execute(f"SELECT COUNT(*) FROM {t} WHERE customer_id = ? AND released = 1",
                                (customer_id,)).fetchone()[0] for t in EVENT_TABLES)


def has_unreleased(customer_id: str) -> bool:
    with connect() as conn:
        return any(conn.execute(f"SELECT 1 FROM {t} WHERE customer_id = ? AND released = 0",
                                (customer_id,)).fetchone() for t in EVENT_TABLES)


def release_next_batch(customer_id: str) -> None:
    """Demo: simulate that new transactions / app actions / context signals arrive."""
    with connect() as conn:
        batches = [conn.execute(f"SELECT MIN(batch) FROM {t} WHERE customer_id = ? AND released = 0",
                                (customer_id,)).fetchone()[0] for t in EVENT_TABLES]
        batches = [b for b in batches if b is not None]
        if batches:
            for t in EVENT_TABLES:
                conn.execute(f"UPDATE {t} SET released = 1 WHERE customer_id = ? AND batch = ?",
                             (customer_id, min(batches)))


# --- Classification cache -------------------------------------------------------------
def get_classification(merchant: str) -> dict | None:
    rows = _rows("SELECT * FROM merchant_industries WHERE merchant = ?", (merchant,))
    return {**rows[0], "scores": json.loads(rows[0]["scores_json"])} if rows else None


def get_all_classifications() -> list[dict]:
    return [{**r, "scores": json.loads(r["scores_json"])}
            for r in _rows("SELECT * FROM merchant_industries ORDER BY merchant")]


def save_classification(merchant: str, scores: dict, reason: str, status: str, method: str) -> None:
    with connect() as conn:
        conn.execute("INSERT OR REPLACE INTO merchant_industries VALUES (?, ?, ?, ?, ?)",
                     (merchant, json.dumps(scores), reason, status, method))


# --- Living profile ----------------------------------------------------------------------
def save_intent_scores(customer_id: str, scores: dict[str, float], version: int) -> None:
    """Store a history row only when new data arrived (not on every page refresh)."""
    with connect() as conn:
        last = conn.execute("SELECT MAX(data_version) FROM intent_scores WHERE customer_id = ?",
                            (customer_id,)).fetchone()[0]
        if last != version:
            conn.executemany("INSERT INTO intent_scores (customer_id, intent, score, data_version, computed_at) "
                             "VALUES (?, ?, ?, ?, ?)",
                             [(customer_id, i, s, version, now()) for i, s in scores.items()])


def get_intent_history(customer_id: str) -> list[dict]:
    return _rows("SELECT intent, score, data_version FROM intent_scores WHERE customer_id = ? ORDER BY id",
                 (customer_id,))


# --- For You page, notifications, feedback -----------------------------------------------
def get_for_you_page(customer_id: str) -> dict | None:
    rows = _rows("SELECT * FROM for_you_page WHERE customer_id = ?", (customer_id,))
    return {"signature": rows[0]["signature"], "content": json.loads(rows[0]["content_json"])} if rows else None


def save_for_you_page(customer_id: str, signature: str, content: dict) -> None:
    with connect() as conn:
        conn.execute("INSERT OR REPLACE INTO for_you_page VALUES (?, ?, ?, ?)",
                     (customer_id, signature, json.dumps(content), now()))


def clear_for_you_page(customer_id: str) -> None:
    with connect() as conn:
        conn.execute("DELETE FROM for_you_page WHERE customer_id = ?", (customer_id,))


def notified_intents(customer_id: str) -> set[str]:
    rows = _rows("SELECT intents FROM notifications WHERE customer_id = ?", (customer_id,))
    return {i for r in rows for i in r["intents"].split(",")}


def save_notification(customer_id: str, intents: list[str], channel: str, moment: str, text: str) -> None:
    with connect() as conn:
        conn.execute("INSERT INTO notifications (customer_id, intents, channel, moment, text, created_at) "
                     "VALUES (?, ?, ?, ?, ?, ?)", (customer_id, ",".join(intents), channel, moment, text, now()))


def get_notifications(customer_id: str) -> list[dict]:
    return _rows("SELECT * FROM notifications WHERE customer_id = ? ORDER BY id DESC", (customer_id,))


def save_feedback(customer_id: str, widget_id: str, reaction: str) -> None:
    with connect() as conn:
        conn.execute("INSERT INTO feedback (customer_id, widget_id, reaction, created_at) VALUES (?, ?, ?, ?)",
                     (customer_id, widget_id, reaction, now()))


def dismissed_widgets(customer_id: str) -> set[str]:
    return {r["widget_id"] for r in _rows(
        "SELECT widget_id FROM feedback WHERE customer_id = ? AND reaction = 'not_for_me'", (customer_id,))}
