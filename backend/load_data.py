
"""Load Greenbook, known-fake, SON and demo data into SQLite.

Run from the repository root:

    python -m backend.load_data greenbook PATH_TO_JSON
    python -m backend.load_data fakes PATH_TO_JSON
    python -m backend.load_data son PATH_TO_JSON
    python -m backend.load_data seed-demo
    python -m backend.load_data reset-demo
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.db import (
    DEFAULT_DB_PATH,
    connect,
    normalize_registration_number,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSON_PATH = (
    PROJECT_ROOT / "nafdac-scraper" / "output2" / "nafdac_products.json"
)
SOURCE_NAME = "nafdac_greenbook"
PLACEHOLDERS = {"", "na", "n/a", "nil", "none", "null", "-", "--"}


def clean(value: Any) -> str | None:
    if value is None:
        return None
    value = re.sub(r"\s+", " ", str(value)).strip()
    return None if value.casefold() in PLACEHOLDERS else value


def first_value(*values: Any) -> str | None:
    for value in values:
        result = clean(value)
        if result:
            return result
    return None


def reg_key(value: Any) -> str:
    return normalize_registration_number(value)


def clean_name(value: Any) -> str | None:
    value = clean(value)
    if not value:
        return None
    value = re.sub(r"\s*\$+\s*$", "", value.replace('"', "")).strip()
    return value or None


def load_json(path: str | Path) -> Any:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Input JSON file not found: {path}")
    with path.open("r", encoding="utf-8-sig") as file:
        return json.load(file)


def _pick(record: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in record:
            value = record[key]
            if isinstance(value, dict):
                value = first_value(value.get("name"), value.get("applicant_name"))
            if value is not None and str(value).strip():
                return value
    return None


def map_greenbook_record(record: dict[str, Any]) -> dict[str, Any] | None:
    """Map the scraped Greenbook record to the shared registry_products schema."""

    registration = first_value(
        _pick(record, "NRN", "NAFDAC", "nafdac_number", "nafdac_no",
              "registration_number", "Registration Number")
    )
    if not registration:
        return None

    category = first_value(
        _pick(record, "Product Category", "category", "category_name",
              "product_category")
    )
    ingredients = first_value(
        _pick(record, "Active Ingredients", "active_ingredients",
              "composition", "ingredient_name")
    )

    detail_id = first_value(_pick(record, "Detail ID", "detail_id", "id"))
    detail_url = first_value(_pick(record, "detail_url", "Detail URL"))
    if not detail_url and detail_id:
        detail_url = (
            "https://greenbook.nafdac.gov.ng/products/details/"
            f"{detail_id}"
        )

    mapped = {
        "country": "NG",
        "source": SOURCE_NAME,
        "reg_no": registration,
        "reg_key": reg_key(registration),
        "product_name": clean_name(
            _pick(record, "Product Name", "product_name", "name")
        ),
        "product_type": None,
        "active_ingredients": ingredients,
        "category": category,
        "dosage_form": first_value(
            _pick(record, "Form", "dosage_form", "dosage_form_name")
        ),
        "route": first_value(_pick(record, "ROA", "route")),
        "strength": first_value(
            _pick(record, "Strengths", "strength", "strengths")
        ),
        "applicant": first_value(
            _pick(record, "Applicant Name", "applicant",
                  "applicant_name", "registration_holder")
        ),
        "manufacturer": first_value(
            _pick(record, "Manufacturer", "manufacturer",
                  "manufacturer_name")
        ),
        "pack_size": first_value(
            _pick(record, "Pack Size", "pack_size", "quantity")
        ),
        "status": first_value(_pick(record, "Status", "status")),
        "approval_date": first_value(
            _pick(record, "Approval Date", "approval_date")
        ),
        "expiry_date": first_value(
            _pick(record, "Expiry Date", "expiry_date")
        ),
        "detail_url": detail_url,
    }

    mapped["status"] = (
        mapped["status"].casefold() if mapped["status"] else None
    )
    if category and "device" in category.casefold():
        mapped["product_type"] = ingredients
        mapped["active_ingredients"] = None

    return mapped


def load_greenbook(
    path: str | Path = DEFAULT_JSON_PATH,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> dict[str, int]:
    records = load_json(path)
    if not isinstance(records, list):
        raise ValueError("Expected Greenbook JSON to contain a list of records.")

    started_at = datetime.now(timezone.utc).isoformat()
    counts = {"seen": len(records), "imported": 0, "skipped": 0,
              "versions_added": 0, "errors": 0}

    connection = connect(db_path)
    try:
        cursor = connection.execute(
            """INSERT INTO import_runs (source, started_at, records_seen)
               VALUES (?, ?, ?)""",
            (SOURCE_NAME, started_at, len(records)),
        )
        run_id = cursor.lastrowid

        for record in records:
            if not isinstance(record, dict):
                counts["errors"] += 1
                continue

            try:
                mapped = map_greenbook_record(record)
                if mapped is None:
                    counts["skipped"] += 1
                    continue

                raw_json = json.dumps(
                    record, ensure_ascii=False, sort_keys=True
                )
                content_hash = hashlib.sha256(
                    raw_json.encode("utf-8")
                ).hexdigest()
                retrieved_at = datetime.now(timezone.utc).isoformat()

                existing = connection.execute(
                    """SELECT id, content_hash
                       FROM registry_products
                       WHERE country = ? AND source = ? AND reg_key = ?
                         AND product_name IS ?""",
                    (
                        mapped["country"],
                        mapped["source"],
                        mapped["reg_key"],
                        mapped["product_name"],
                    ),
                ).fetchone()

                values = {
                    **mapped,
                    "raw_json": raw_json,
                    "source_retrieved_at": retrieved_at,
                    "content_hash": content_hash,
                }

                if existing is not None and existing["content_hash"] == content_hash:
                    counts["skipped"] += 1
                    continue

                connection.execute(
                    """
                    INSERT INTO registry_source_versions (
                        country, source, reg_key, product_name,
                        content_hash, retrieved_at, raw_json
                    ) VALUES (
                        :country, :source, :reg_key, :product_name,
                        :content_hash, :source_retrieved_at, :raw_json
                    )
                    ON CONFLICT(
                        country, source, reg_key, product_name, content_hash
                    ) DO NOTHING
                    """,
                    values,
                )
                if connection.execute("SELECT changes()").fetchone()[0]:
                    counts["versions_added"] += 1

                if existing is None:
                    columns = list(values.keys())
                    connection.execute(
                        f"""
                        INSERT INTO registry_products (
                            {", ".join(columns)}
                        ) VALUES (
                            {", ".join(":" + column for column in columns)}
                        )
                        """,
                        values,
                    )
                else:
                    # Update the matching source record; preserve its row ID.
                    update_columns = [
                        column for column in values
                        if column not in {
                            "country", "source", "reg_key", "product_name"
                        }
                    ]
                    connection.execute(
                        f"""
                        UPDATE registry_products
                        SET {", ".join(f"{c} = :{c}" for c in update_columns)}
                        WHERE id = :existing_id
                        """,
                        {**values, "existing_id": existing["id"]},
                    )

                counts["imported"] += 1
            except Exception as exc:
                counts["errors"] += 1
                print(f"Error processing record: {exc}")

        connection.execute(
            """
            UPDATE import_runs
            SET finished_at = ?, records_imported = ?,
                versions_added = ?, errors = ?
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

    print(
        f"Greenbook: seen={counts['seen']}, "
        f"imported/updated={counts['imported']}, "
        f"skipped={counts['skipped']}, "
        f"versions_added={counts['versions_added']}, "
        f"errors={counts['errors']}"
    )
    return counts


def load_fakes(
    path: str | Path,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> None:
    records = load_json(path)
    if not isinstance(records, list):
        raise ValueError("Expected known-fakes JSON to contain a list.")

    connection = connect(db_path)
    try:
        for item in records:
            connection.execute(
                """INSERT INTO known_fakes
                   (product_name, reg_key, batch, note, source)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    clean(item.get("product_name")),
                    reg_key(item.get("nafdac_no")),
                    clean(item.get("batch")),
                    clean(item.get("note")),
                    clean(item.get("source")),
                ),
            )
        connection.commit()
    finally:
        connection.close()
    print(f"Known fakes loaded: {len(records)}")


def load_son(
    path: str | Path,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> None:
    records = load_json(path)
    if not isinstance(records, list):
        raise ValueError("Expected SON JSON to contain a list.")

    connection = connect(db_path)
    try:
        connection.execute("DELETE FROM son_certified")
        connection.executemany(
            """INSERT INTO son_certified
               (sector, company, address, product, state, search)
               VALUES (?, ?, ?, ?, ?, ?)""",
            [
                (
                    clean(item.get("sector")),
                    clean(item.get("company")),
                    clean(item.get("address")),
                    clean(item.get("product")),
                    clean(item.get("state")),
                    f"{item.get('company', '')} {item.get('product', '')}".casefold(),
                )
                for item in records
            ],
        )
        connection.commit()
    finally:
        connection.close()
    print(f"SON certified products loaded: {len(records)}")


DEMO_SCANS = [
    ("demo_1", "medical_device", "Accu-Chek",
     "Accu-Chek Softclix Lancet", "03-6090", "DEMO-SC2207",
     "2027-06", "Lagos"),
    ("demo_2", "medical_device", "Accu-Chek",
     "Accu-Chek Softclix Lancet", "03-6090", "DEMO-SC2207",
     "2027-06", "Ogun"),
    ("demo_3", "medical_device", "Always",
     "Always 3-In-1 Maxi Thick Sanitary Pads", "03-2099",
     "DEMO-AL5531", "2027-03", "Kano"),
]


def seed_demo(db_path: str | Path = DEFAULT_DB_PATH) -> None:
    connection = connect(db_path)
    try:
        for sid, category, brand, name, reg, batch, expiry, state in DEMO_SCANS:
            connection.execute(
                """
                INSERT OR REPLACE INTO scans (
                    id, category, brand, product_name, reg_key, batch,
                    expiry, state, verdict, trust_score, seeded, result_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'unknown', 50, 1, '{}')
                """,
                (sid, category, brand, name, reg_key(reg), batch, expiry, state),
            )
        connection.commit()
    finally:
        connection.close()
    print(f"Demo scans seeded: {len(DEMO_SCANS)}")


def reset_demo(db_path: str | Path = DEFAULT_DB_PATH) -> None:
    connection = connect(db_path)
    try:
        connection.execute("DELETE FROM scans WHERE seeded = 1 OR id LIKE 'demo_%'")
        connection.execute("DELETE FROM reports WHERE seeded = 1")
        connection.commit()
    finally:
        connection.close()
    print("Demo scans and reports removed.")


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return

    command = args[0]
    if command == "greenbook":
        load_greenbook(args[1] if len(args) > 1 else DEFAULT_JSON_PATH)
    elif command == "fakes" and len(args) > 1:
        load_fakes(args[1])
    elif command == "son" and len(args) > 1:
        load_son(args[1])
    elif command == "seed-demo":
        seed_demo()
    elif command == "reset-demo":
        reset_demo()
    else:
        print(__doc__)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
