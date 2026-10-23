
"""SQLite database schema and access for Check Am."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

# Allow the database path to be configured without changing code.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = Path(
    os.environ.get(
        "CHECKAM_DB",
        str(PROJECT_ROOT / "data" / "checkam.sqlite3"),
    )
)
DB_PATH = str(DEFAULT_DB_PATH)

SCHEMA = """
CREATE TABLE IF NOT EXISTS registry_products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    country TEXT NOT NULL DEFAULT 'NG',
    source TEXT NOT NULL DEFAULT 'nafdac_greenbook',
    reg_no TEXT NOT NULL,
    reg_key TEXT NOT NULL,
    product_name TEXT,
    product_type TEXT,
    active_ingredients TEXT,
    category TEXT,
    dosage_form TEXT,
    route TEXT,
    strength TEXT,
    applicant TEXT,
    manufacturer TEXT,
    pack_size TEXT,
    status TEXT,
    approval_date TEXT,
    expiry_date TEXT,
    detail_url TEXT,
    confirmed_at TEXT,
    raw_json TEXT,
    source_retrieved_at TEXT,
    content_hash TEXT,
    UNIQUE (country, source, reg_key, product_name)
);

CREATE INDEX IF NOT EXISTS idx_registry_key
    ON registry_products(country, reg_key);

CREATE TABLE IF NOT EXISTS registry_source_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    country TEXT NOT NULL DEFAULT 'NG',
    source TEXT NOT NULL,
    reg_key TEXT NOT NULL,
    product_name TEXT,
    content_hash TEXT NOT NULL,
    retrieved_at TEXT NOT NULL,
    raw_json TEXT NOT NULL,
    UNIQUE(country, source, reg_key, product_name, content_hash)
);

CREATE INDEX IF NOT EXISTS idx_registry_versions_key
    ON registry_source_versions(country, reg_key);

CREATE TABLE IF NOT EXISTS import_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    started_at TEXT NOT NULL DEFAULT (datetime('now')),
    finished_at TEXT,
    records_seen INTEGER NOT NULL DEFAULT 0,
    records_imported INTEGER NOT NULL DEFAULT 0,
    versions_added INTEGER NOT NULL DEFAULT 0,
    errors INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS scans (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    country TEXT NOT NULL DEFAULT 'NG',
    category TEXT,
    brand TEXT,
    product_name TEXT,
    reg_key TEXT,
    batch TEXT,
    expiry TEXT,
    mfg_date TEXT,
    serial TEXT,
    state TEXT,
    market TEXT,
    verdict TEXT,
    trust_score INTEGER,
    seeded INTEGER NOT NULL DEFAULT 0,
    result_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_scans_batch ON scans(batch);
CREATE INDEX IF NOT EXISTS idx_scans_serial ON scans(serial);

CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    scan_id TEXT,
    brand TEXT,
    product_name TEXT,
    reg_key TEXT,
    batch TEXT,
    seller TEXT,
    state TEXT,
    market TEXT,
    note TEXT,
    reporter TEXT,
    seeded INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_reports_batch ON reports(batch);

CREATE TABLE IF NOT EXISTS known_fakes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name TEXT,
    reg_key TEXT,
    batch TEXT,
    note TEXT,
    source TEXT
);

CREATE INDEX IF NOT EXISTS idx_fakes_batch ON known_fakes(batch);

CREATE TABLE IF NOT EXISTS son_certified (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sector TEXT,
    company TEXT,
    address TEXT,
    product TEXT,
    state TEXT,
    search TEXT
);
"""


def normalize_registration_number(value: object) -> str:
    """Normalize whitespace and case without removing meaningful symbols."""
    if value is None:
        return ""
    return " ".join(str(value).strip().upper().split())


def connect(path: str | Path | None = None) -> sqlite3.Connection:
    """Open a connection and initialize the shared schema."""
    db_path = Path(path) if path is not None else DEFAULT_DB_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(str(db_path), timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 30000")
    connection.executescript(SCHEMA)
    return connection


def get_connection(
    db_path: str | Path | None = None,
) -> sqlite3.Connection:
    """Compatibility alias used by Bruno's registry implementation."""
    return connect(db_path)


def init_db(db_path: str | Path | None = None) -> None:
    """Create the schema and enable WAL journaling."""
    with connect(db_path) as connection:
        connection.execute("PRAGMA journal_mode = WAL")
