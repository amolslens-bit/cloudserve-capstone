"""SQLite decision log: one row per ticket decision (starter schema)."""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path("storage/decisions.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS decisions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id       TEXT NOT NULL,
    logged_at       TEXT NOT NULL,
    intent          TEXT,
    urgency         TEXT,
    confidence      REAL,
    retrieved_docs  TEXT,      -- JSON list of doc_ids
    route           TEXT,      -- auto_respond or escalate
    reason          TEXT,      -- why this route was taken
    model_used      TEXT,      -- primary or fallback model
    latency_ms      INTEGER
    customer_tier     TEXT,
    guardrails_run    INTEGER,   -- 1 = yes, 0 = no
    guardrail_result  TEXT,      -- JSON of each check's outcome
    steps             TEXT,      -- JSON list of steps performed
    prompt_version    TEXT
);
"""


def connect():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(SCHEMA)
    return conn


def log_decision(conn, ticket_id, **fields):
    fields["retrieved_docs"] = json.dumps(fields.get("retrieved_docs", []))
    fields["ticket_id"] = ticket_id
    fields["logged_at"] = datetime.now(timezone.utc).isoformat()
    cols = ", ".join(fields)
    marks = ", ".join("?" for _ in fields)
    conn.execute(f"INSERT INTO decisions ({cols}) VALUES ({marks})", list(fields.values()))
    conn.commit()


if __name__ == "__main__":
    conn = connect()
    log_decision(conn, "TEST-0001", intent="authentication_failure", urgency="high",
                 confidence=0.91, retrieved_docs=["DOC-AUTH-001"], route="auto_respond",
                 reason="confidence above threshold; doc found", model_used="nemotron",
                 latency_ms=850)
    for row in conn.execute("SELECT ticket_id, route, reason FROM decisions"):
        print(row)