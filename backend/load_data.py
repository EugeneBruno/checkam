"""Import the locally scraped NAFDAC Greenbook dataset into SQLite."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.db import (
    DEFAULT_DB_PATH,
    get_connection,
    normalize_registration_number,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSON_PATH = (
    PROJECT_ROOT / "nafdac-scraper" / "output2" / "nafdac_products.json"
)
SOURCE_NAME = "NAFDAC Greenbook (local scraped dataset)"


def first_value(*values: Any) -> str | None:
    """Return the first non-empty value as text."""
    for value in values:
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def nested_name(record: dict[str, Any], key: str) -> str | None:
    value = record.get(key)
    if isinstance(value, dict):
        return first_value(value.get("name"), value.get("applicant_name"))
    return None


def map_record(record: dict[str, Any]) -> dict[str, Any]:
    nafdac_number = first_value(record.get("NAFDAC"), record.get("nafdac_number"))
    product_id = first_value(record.get("product_id"), record.get("id"))

    if not product_id:
        identity = json.dumps(record, sort_keys=True, ensure_ascii=False)
        product_id = "missing-id-" + hashlib.sha256(
            identity.encode("utf-8")
        ).hexdigest()[:20]

    return {
        "product_id": product_id,
        "nafdac_number": nafdac_number,
        "nafdac_normalized": normalize_registration_number(nafdac_number),
        "product_name": first_value(record.get("product_name"), record.get("name")),
        "applicant_name": first_value(
            record.get("applicant_name"),
            nested_name(record, "applicant"),
        ),
        "strength": first_value(record.get("strength")),
        "composition": first_value(record.get("composition")),
        "ingredient_name": first_value(
            record.get("ingredient_name"),
            nested_name(record, "ingredient"),
        ),
        "category_name": first_value(
            record.get("category_name"),
            nested_name(record, "product_category"),
        ),
        "status": first_value(record.get("status")),
        "approval_date": first_value(record.get("approval_date")),
        "expiry_date": first_value(record.get("expiry_date")),
    }


def import_dataset(
    json_path: Path = DEFAULT_JSON_PATH,
    db_path: Path = DEFAULT_DB_PATH,
) -> dict[str, int]:
    if not json_path.is_file():
        raise FileNotFoundError(f"Dataset not found: {json_path}")

    with json_path.open("r", encoding="utf-8-sig") as file:
        records = json.load(file)

    if not isinstance(records, list):
        raise ValueError("Expected the JSON dataset to contain a list of records.")

    started_at = datetime.now(timezone.utc).isoformat()
    retrieved_at = started_at
    counts = {"seen": len(records), "imported": 0, "versions_added": 0, "errors": 0}

    connection = get_connection(db_path)

    try:
        cursor = connection.execute(
            """
            INSERT INTO import_runs (source, started_at, records_seen)
            VALUES (?, ?, ?)
            """,
            (SOURCE_NAME, started_at, len(records)),
        )
        run_id = cursor.lastrowid

        for record in records:
            if not isinstance(record, dict):
                counts["errors"] += 1
                continue

            try:
                mapped = map_record(record)
                raw_json = json.dumps(
                    record, ensure_ascii=False, sort_keys=True, separators=(",", ":")
                )
                content_hash = hashlib.sha256(raw_json.encode("utf-8")).hexdigest()

                existing = connection.execute(
                    "SELECT content_hash FROM registry_records WHERE product_id = ?",
                    (mapped["product_id"],),
                ).fetchone()

                if existing is None or existing["content_hash"] != content_hash:
                    connection.execute(
                        """
                        INSERT OR IGNORE INTO registry_source_versions
                            (product_id, content_hash, source, retrieved_at, raw_json)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            mapped["product_id"],
                            content_hash,
                            SOURCE_NAME,
                            retrieved_at,
                            raw_json,
                        ),
                    )
                    if connection.execute("SELECT changes()").fetchone()[0]:
                        counts["versions_added"] += 1

                    connection.execute(
                        """
                        INSERT INTO registry_records (
                            product_id, nafdac_number, nafdac_normalized,
                            product_name, applicant_name, strength, composition,
                            ingredient_name, category_name, status, approval_date,
                            expiry_date, source, source_retrieved_at, raw_json,
                            content_hash
                        ) VALUES (
                            :product_id, :nafdac_number, :nafdac_normalized,
                            :product_name, :applicant_name, :strength, :composition,
                            :ingredient_name, :category_name, :status, :approval_date,
                            :expiry_date, :source, :source_retrieved_at, :raw_json,
                            :content_hash
                        )
                        ON CONFLICT(product_id) DO UPDATE SET
                            nafdac_number = excluded.nafdac_number,
                            nafdac_normalized = excluded.nafdac_normalized,
                            product_name = excluded.product_name,
                            applicant_name = excluded.applicant_name,
                            strength = excluded.strength,
                            composition = excluded.composition,
                            ingredient_name = excluded.ingredient_name,
                            category_name = excluded.category_name,
                            status = excluded.status,
                            approval_date = excluded.approval_date,
                            expiry_date = excluded.expiry_date,
                            source = excluded.source,
                            source_retrieved_at = excluded.source_retrieved_at,
                            raw_json = excluded.raw_json,
                            content_hash = excluded.content_hash
                        """,
                        {
                            **mapped,
                            "source": SOURCE_NAME,
                            "source_retrieved_at": retrieved_at,
                            "raw_json": raw_json,
                            "content_hash": content_hash,
                        },
                    )
                    counts["imported"] += 1

            except (sqlite3.Error, TypeError, ValueError) as error:
                counts["errors"] += 1
                print(f"Skipped record: {error}")

        connection.execute(
            """
            UPDATE import_runs
            SET finished_at = ?, records_imported = ?, versions_added = ?, errors = ?
            WHERE id = ?
            """,
            (
                datetime.now(timezone.utc).isoformat(),
                counts["imported"],
                counts["versions_added"],
                counts["errors"],
                run_id,
            ),
        )
        connection.commit()

    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    return counts


if __name__ == "__main__":
    print(f"Dataset: {DEFAULT_JSON_PATH}")
    print(f"Database: {DEFAULT_DB_PATH}")
    result = import_dataset()
    print("\nImport complete")
    print(f"Records seen:     {result['seen']}")
    print(f"Records imported: {result['imported']}")
    print(f"Versions added:   {result['versions_added']}")
    print(f"Errors:           {result['errors']}")
