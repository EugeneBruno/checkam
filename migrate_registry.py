
import json
import shutil
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from backend.db import DEFAULT_DB_PATH
from backend.load_data import map_greenbook_record

DB_PATH = Path(DEFAULT_DB_PATH)
ARCHIVE_TABLE = "registry_source_versions_legacy"


def main():
    if not DB_PATH.exists():
        raise SystemExit(f"Database not found: {DB_PATH}")

    # Refuse to overwrite an earlier archive.
    backup_path = DB_PATH.with_name(
        f"checkam_pre_migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sqlite3"
    )
    shutil.copy2(DB_PATH, backup_path)
    print(f"Backup created: {backup_path}")

    # Read all legacy rows before changing anything.
    read_conn = sqlite3.connect(str(DB_PATH))
    read_conn.row_factory = sqlite3.Row

    existing_tables = {
        row[0] for row in read_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }

    if ARCHIVE_TABLE in existing_tables:
        read_conn.close()
        raise SystemExit(
            f"{ARCHIVE_TABLE} already exists. Stopping to avoid overwriting it."
        )

    old_rows = read_conn.execute(
        """
        SELECT id, product_id, content_hash, source, retrieved_at, raw_json
        FROM registry_source_versions
        ORDER BY id
        """
    ).fetchall()
    read_conn.close()

    # Map historical JSON without writing to the database.
    mapped_rows = []
    skipped = []
    errors = []

    for row in old_rows:
        try:
            raw = json.loads(row["raw_json"])
            mapped = map_greenbook_record(raw)
            if mapped is None:
                skipped.append(row["id"])
                continue
            mapped_rows.append((row, mapped))
        except Exception as exc:
            errors.append((row["id"], str(exc)))

    if errors:
        print("Mapping errors found; no migration performed:")
        for item in errors[:10]:
            print(item)
        raise SystemExit(1)

    # Build one product row per identity, retaining the latest historical
    # version as the current product representation.
    products = {}
    for row, mapped in mapped_rows:
        identity = (
            mapped["country"],
            mapped["source"],
            mapped["reg_key"],
            mapped["product_name"],
        )
        products[identity] = (row, mapped)

    conn = sqlite3.connect(str(DB_PATH), timeout=30)
    conn.row_factory = sqlite3.Row

    try:
        conn.execute("PRAGMA busy_timeout = 30000")
        conn.execute("BEGIN IMMEDIATE")

        # Preserve the original table, IDs, raw JSON, hashes and timestamps.
        conn.execute(
            f"ALTER TABLE registry_source_versions RENAME TO {ARCHIVE_TABLE}"
        )

        conn.execute(
            """
            CREATE TABLE registry_source_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                country TEXT NOT NULL DEFAULT 'NG',
                source TEXT NOT NULL,
                reg_key TEXT NOT NULL,
                product_name TEXT,
                content_hash TEXT NOT NULL,
                retrieved_at TEXT NOT NULL,
                raw_json TEXT NOT NULL,
                UNIQUE(country, source, reg_key, product_name, content_hash)
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX idx_registry_versions_key
            ON registry_source_versions(country, reg_key)
            """
        )

        # Insert each product identity once.
        for identity, (row, mapped) in products.items():
            conn.execute(
                """
                INSERT INTO registry_products (
                    country, source, reg_no, reg_key, product_name,
                    product_type, active_ingredients, category, dosage_form,
                    route, strength, applicant, manufacturer, pack_size,
                    status, approval_date, expiry_date, detail_url, raw_json,
                    source_retrieved_at, content_hash
                )
                VALUES (
                    :country, :source, :reg_no, :reg_key, :product_name,
                    :product_type, :active_ingredients, :category, :dosage_form,
                    :route, :strength, :applicant, :manufacturer, :pack_size,
                    :status, :approval_date, :expiry_date, :detail_url, :raw_json,
                    :retrieved_at, :content_hash
                )
                ON CONFLICT(country, source, reg_key, product_name)
                DO UPDATE SET
                    reg_no = excluded.reg_no,
                    product_type = excluded.product_type,
                    active_ingredients = excluded.active_ingredients,
                    category = excluded.category,
                    dosage_form = excluded.dosage_form,
                    route = excluded.route,
                    strength = excluded.strength,
                    applicant = excluded.applicant,
                    manufacturer = excluded.manufacturer,
                    pack_size = excluded.pack_size,
                    status = excluded.status,
                    approval_date = excluded.approval_date,
                    expiry_date = excluded.expiry_date,
                    detail_url = excluded.detail_url,
                    raw_json = excluded.raw_json,
                    source_retrieved_at = excluded.source_retrieved_at,
                    content_hash = excluded.content_hash
                """,
                {
                    **mapped,
                    "raw_json": row["raw_json"],
                    "retrieved_at": row["retrieved_at"],
                    "content_hash": row["content_hash"],
                },
            )

        # Migrate every mappable historical version, not just the latest one.
        # Keep the original hash, timestamp and raw JSON exactly as stored.
        for row, mapped in mapped_rows:
            conn.execute(
                """
                INSERT INTO registry_source_versions (
                    country, source, reg_key, product_name,
                    content_hash, retrieved_at, raw_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(
                    country, source, reg_key, product_name, content_hash
                ) DO NOTHING
                """,
                (
                    mapped["country"],
                    mapped["source"],
                    mapped["reg_key"],
                    mapped["product_name"],
                    row["content_hash"],
                    row["retrieved_at"],
                    row["raw_json"],
                ),
            )

        # Validate inside the transaction before committing.
        product_count = conn.execute(
            "SELECT COUNT(*) FROM registry_products"
        ).fetchone()[0]
        version_count = conn.execute(
            "SELECT COUNT(*) FROM registry_source_versions"
        ).fetchone()[0]
        archive_count = conn.execute(
            f"SELECT COUNT(*) FROM {ARCHIVE_TABLE}"
        ).fetchone()[0]

        if archive_count != len(old_rows):
            raise RuntimeError(
                f"Archive count mismatch: expected {len(old_rows)}, got {archive_count}"
            )

       
            if product_count != len(products):
                raise RuntimeError(
                    f"Product count mismatch: expected {len(products)}, got {product_count}"
                )

            expected_versions = len({
                (
                    mapped["country"],
                    mapped["source"],
                    mapped["reg_key"],
                    mapped["product_name"],
                    row["content_hash"],
                )
                for row, mapped in mapped_rows
            })

            if version_count != expected_versions:
                raise RuntimeError(
                    f"Version count mismatch: expected {expected_versions}, got {version_count}"
                )

        # Some duplicate identity/hash combinations may collapse under the

        # Some duplicate identity/hash combinations may collapse under the
        # new uniqueness constraint. The legacy archive preserves every row.
        conn.commit()

        print("\nMigration committed.")
        print(f"Original legacy rows archived: {archive_count}")
        print(f"Mapped records: {len(mapped_rows)}")
        print(f"Unique product identities: {len(products)}")
        print(f"Products in registry_products: {product_count}")
        print(f"Versions in new table: {version_count}")
        print(f"Unmapped legacy rows retained: {len(skipped)}")
        print(f"Unmapped legacy IDs: {skipped}")
        print(f"Backup: {backup_path}")

    except Exception:
        conn.rollback()
        print("Migration failed; transaction rolled back.")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
