"""SQLite database schema and access for Check Am's NAFDAC registry."""

from __future__ import annotations

import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "checkam.sqlite3"

SCHEMA = """
CREATE TABLE IF NOT EXISTS registry_records (
    product_id TEXT PRIMARY KEY,
    nafdac_number TEXT,
    nafdac_normalized TEXT,
    product_name TEXT,
    applicant_name TEXT,
    strength TEXT,
    composition TEXT,
    ingredient_name TEXT,
    category_name TEXT,
    status TEXT,
    approval_date TEXT,
    expiry_date TEXT,
    source TEXT NOT NULL,
    source_retrieved_at TEXT NOT NULL,
    raw_json TEXT NOT NULL,
    content_hash TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_registry_nafdac
    ON registry_records(nafdac_normalized);
CREATE INDEX IF NOT EXISTS idx_registry_name
    ON registry_records(product_name);
CREATE INDEX IF NOT EXISTS idx_registry_status
    ON registry_records(status);

CREATE TABLE IF NOT EXISTS registry_source_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    source TEXT NOT NULL,
    retrieved_at TEXT NOT NULL,
    raw_json TEXT NOT NULL,
    UNIQUE(product_id, content_hash)
);

CREATE INDEX IF NOT EXISTS idx_registry_versions_product
    ON registry_source_versions(product_id);

CREATE TABLE IF NOT EXISTS import_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    records_seen INTEGER NOT NULL DEFAULT 0,
    records_imported INTEGER NOT NULL DEFAULT 0,
    versions_added INTEGER NOT NULL DEFAULT 0,
    errors INTEGER NOT NULL DEFAULT 0
);
"""


def normalize_registration_number(value: object) -> str:
    """Normalize whitespace and case without removing meaningful symbols."""
    if value is None:
        return ""
    return " ".join(str(value).strip().upper().split())


def get_connection(db_path: str | Path | None = None) -> sqlite3.Connection:
    """Open a SQLite connection and initialize the schema."""
    path = Path(db_path) if db_path is not None else DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(str(path), timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 30000")
    connection.executescript(SCHEMA)
    return connection


def init_db(db_path: str | Path | None = None) -> None:
    """Create the database schema."""
    with get_connection(db_path) as connection:
        connection.execute("PRAGMA journal_mode = WAL")
