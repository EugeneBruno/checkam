"""SQLite storage: registry, scans, reports, known fakes."""
import os
import sqlite3

DB_PATH = os.environ.get("CHECKAM_DB", os.path.join(os.path.dirname(__file__), "checkam.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS registry_products (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    country            TEXT NOT NULL DEFAULT 'NG',
    source             TEXT NOT NULL DEFAULT 'nafdac_greenbook',
    reg_no             TEXT NOT NULL,
    reg_key            TEXT NOT NULL,
    product_name       TEXT,
    product_type       TEXT,
    active_ingredients TEXT,
    category           TEXT,
    dosage_form        TEXT,
    route              TEXT,
    strength           TEXT,
    applicant          TEXT,
    manufacturer       TEXT,
    pack_size          TEXT,
    status             TEXT,
    approval_date      TEXT,
    expiry_date        TEXT,
    detail_url         TEXT,
    confirmed_at       TEXT,              -- NAPAMS user confirmations
    UNIQUE (country, source, reg_key, product_name)
);
CREATE INDEX IF NOT EXISTS idx_registry_key ON registry_products (country, reg_key);

CREATE TABLE IF NOT EXISTS scans (
    id           TEXT PRIMARY KEY,
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    country      TEXT NOT NULL DEFAULT 'NG',
    category     TEXT,
    brand        TEXT,
    product_name TEXT,
    reg_key      TEXT,
    batch        TEXT,
    expiry       TEXT,
    mfg_date     TEXT,
    serial       TEXT,
    state        TEXT,
    market       TEXT,
    verdict      TEXT,
    trust_score  INTEGER,
    seeded       INTEGER NOT NULL DEFAULT 0, -- 1 = demo seed data
    result_json  TEXT
);
CREATE INDEX IF NOT EXISTS idx_scans_batch ON scans (batch);
CREATE INDEX IF NOT EXISTS idx_scans_serial ON scans (serial);

CREATE TABLE IF NOT EXISTS reports (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    scan_id      TEXT,
    brand        TEXT,
    product_name TEXT,
    reg_key      TEXT,
    batch        TEXT,
    seller       TEXT,
    state        TEXT,
    market       TEXT,
    note         TEXT,
    reporter     TEXT,                    -- 'user' or 'agent'
    seeded       INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_reports_batch ON reports (batch);

CREATE TABLE IF NOT EXISTS known_fakes (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name TEXT,
    reg_key      TEXT,
    batch        TEXT,
    note         TEXT,
    source       TEXT                     -- NAFDAC alert URL
);
CREATE INDEX IF NOT EXISTS idx_fakes_batch ON known_fakes (batch);

-- SON 2024-2029 List of Certified Products (MANCAP, locally made goods), all sectors
CREATE TABLE IF NOT EXISTS son_certified (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    sector   TEXT,
    company  TEXT,
    address  TEXT,
    product  TEXT,
    state    TEXT,
    search   TEXT                      -- lowercased company + product for lookups
);
"""


def connect(path: str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn
