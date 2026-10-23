
"""Parse and import SON chemical and food sector Markdown registries."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.db import DEFAULT_DB_PATH, get_connection

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_SOURCES = {
    "chemical": PROJECT_ROOT / "data" / "CHEMICAL-PRODUCTS-SECTOR_compressed.md",
    "food": PROJECT_ROOT / "data" / "FOOD-PRODUCTS-SECTOR-_compressed-1.md",
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS son_products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sector TEXT NOT NULL,
    serial_number TEXT,
    company_name TEXT NOT NULL,
    address TEXT,
    product_name TEXT NOT NULL,
    state TEXT,
    source_file TEXT NOT NULL,
    source_row_hash TEXT NOT NULL,
    source_row TEXT NOT NULL,
    imported_at TEXT NOT NULL,
    UNIQUE(sector, source_row_hash, product_name)
);

CREATE INDEX IF NOT EXISTS idx_son_product_name
    ON son_products(product_name);
CREATE INDEX IF NOT EXISTS idx_son_company_name
    ON son_products(company_name);
CREATE INDEX IF NOT EXISTS idx_son_sector
    ON son_products(sector);

CREATE TABLE IF NOT EXISTS son_import_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sector TEXT NOT NULL,
    source_file TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    rows_seen INTEGER NOT NULL DEFAULT 0,
    rows_parsed INTEGER NOT NULL DEFAULT 0,
    products_imported INTEGER NOT NULL DEFAULT 0,
    errors INTEGER NOT NULL DEFAULT 0
);
"""


def clean_cell(value: str) -> str:
    """Convert HTML breaks and tags into normalized whitespace."""
    value = re.sub(r"<br\s*/?>", " ", value, flags=re.IGNORECASE)
    value = re.sub(r"<[^>]+>", "", value)
    value = value.replace("&amp;", "&")
    return " ".join(value.split()).strip(" |")


def split_markdown_row(line: str) -> list[str]:
    """Split a pipe-delimited Markdown table row."""
    return [
        clean_cell(cell)
        for cell in line.strip().strip("|").split("|")
    ]


def split_products(value: str) -> list[str]:
    """Split semicolon-separated product names, preserving order."""
    products: list[str] = []
    seen: set[str] = set()

    for part in value.split(";"):
        name = clean_cell(part).strip(" ;,")
        key = name.casefold()

        if name and key not in seen:
            products.append(name)
            seen.add(key)

    return products


def parse_markdown_file(
    path: Path,
    sector: str,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Parse food and chemical SON Markdown table rows."""
    path = Path(path)

    if not path.is_file():
        raise FileNotFoundError(f"SON source file not found: {path}")

    parsed: list[dict[str, Any]] = []
    stats = {
        "rows_seen": 0,
        "rows_parsed": 0,
        "errors": 0,
        "rows_skipped": 0,
    }

    with path.open("r", encoding="utf-8-sig") as file:
        for raw_line in file:
            line = raw_line.strip()

            # Skip headings, page numbers, separators, and non-table lines.
            if not line.startswith("|") or not re.match(r"^\|\s*\d+", line):
                continue

            stats["rows_seen"] += 1
            cells = split_markdown_row(line)

            if len(cells) < 3:
                stats["errors"] += 1
                continue

            # The first cell can be "1" or "6 AVANTI INDUSTRIES LIMITED".
            match = re.match(r"^(\d+)\s*(.*)$", cells[0])
            if not match:
                stats["errors"] += 1
                continue

            serial, first_value = match.groups()
            first_value = first_value.strip()


            if sector.casefold() == "food":
                if len(cells) >= 5:
                    # Standard food layout:
                    # serial | company | address | product | state
                    company = first_value or cells[1]
                    address = cells[2] or None
                    product_cell = cells[3]
                    state = cells[4]

                elif len(cells) == 4:
                    # Compact layout:
                    # serial + company | address | product | state
                    company = first_value or cells[1]
                    address = None
                    product_cell = cells[2]
                    state = cells[3]

                    if not company:
                        stats["errors"] += 1
                        continue
                elif len(cells) == 3:
                     # Malformed row: state may have been merged into the
                    company = first_value
                    address = cells[1] or None
                    product_cell = cells[2]
                    state = None

                    match_state = re.search(
                        r"\s+(Oyo)\s*$",
                        product_cell,
                        flags=re.IGNORECASE,
                    )
                    if match_state:
                        state = match_state.group(1).title()
                        product_cell = product_cell[:match_state.start()].strip()

                    else:
                        stats["errors"] += 1
                        continue
                    if not company or not product_cell:
                        stats["errors"] += 1
                        continue

            elif sector.casefold() == "chemical":
                # Standard chemical row:
                # serial | company + address | product | state
                #
                # Some rows instead have:
                # serial + company | address | product | state
                if len(cells) == 4:
                    if first_value:
                        company = first_value
                        address = cells[1] or None
                    else:
                        company = cells[1]
                        address = None

                    product_cell = cells[2]
                    state = cells[3]

                elif len(cells) >= 5:
                    # A five-column row may use the food-style layout.
                    company = first_value or cells[1]
                    address = cells[2] or None
                    product_cell = cells[3]
                    state = cells[4]
                else:
                    stats["errors"] += 1
                    continue

            else:
                raise ValueError(
                    f"Unsupported SON sector {sector!r}; "
                    "expected 'chemical' or 'food'."
                )

            if not company or not product_cell:
                stats["rows_skipped"] += 1
                continue

            products = split_products(product_cell)
            if not products:
                stats["rows_skipped"] += 1
                continue

            row_hash = hashlib.sha256(
                line.encode("utf-8")
            ).hexdigest()

            for product in products:
                parsed.append({
                    "sector": sector.casefold(),
                    "serial_number": serial,
                    "company_name": company,
                    "address": address,
                    "product_name": product,
                    "state": state or None,
                    "source_file": path.name,
                    "source_row_hash": row_hash,
                    "source_row": line,
                })

            stats["rows_parsed"] += 1

    return parsed, stats


def import_son_data(
    sources: dict[str, Path] | None = None,
    db_path: Path = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    """Import SON Markdown records into SQLite; safe to rerun."""
    sources = sources or DEFAULT_SOURCES
    connection = get_connection(db_path)

    summary: dict[str, Any] = {
        "sectors": {},
        "totals": {
            "rows_seen": 0,
            "rows_parsed": 0,
            "products_found": 0,
            "products_imported": 0,
            "errors": 0,
        },
    }

    try:
        connection.executescript(SCHEMA)

        for sector, source_path in sources.items():
            path = Path(source_path)
            started = datetime.now(timezone.utc).isoformat()
            records, stats = parse_markdown_file(path, sector)
            imported = 0
            errors = stats["errors"]

            cursor = connection.execute(
                """
                INSERT INTO son_import_runs (
                    sector, source_file, started_at,
                    rows_seen, rows_parsed, errors
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    sector,
                    path.name,
                    started,
                    stats["rows_seen"],
                    stats["rows_parsed"],
                    errors,
                ),
            )
            run_id = cursor.lastrowid

            try:
                for record in records:
                    try:
                        cursor = connection.execute(
                            """
                            INSERT OR IGNORE INTO son_products (
                                sector, serial_number, company_name,
                                address, product_name, state,
                                source_file, source_row_hash,
                                source_row, imported_at
                            )
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                record["sector"],
                                record["serial_number"],
                                record["company_name"],
                                record["address"],
                                record["product_name"],
                                record["state"],
                                record["source_file"],
                                record["source_row_hash"],
                                record["source_row"],
                                started,
                            ),
                        )
                        imported += max(cursor.rowcount, 0)
                    except sqlite3.Error:
                        errors += 1

                finished = datetime.now(timezone.utc).isoformat()
                connection.execute(
                    """
                    UPDATE son_import_runs
                    SET finished_at = ?, products_imported = ?, errors = ?
                    WHERE id = ?
                    """,
                    (finished, imported, errors, run_id),
                )
                connection.commit()

            except Exception:
                connection.rollback()
                raise

            summary["sectors"][sector] = {
                **stats,
                "products_found": len(records),
                "products_imported": imported,
                "errors": errors,
                "source_file": str(path),
            }

            summary["totals"]["rows_seen"] += stats["rows_seen"]
            summary["totals"]["rows_parsed"] += stats["rows_parsed"]
            summary["totals"]["products_found"] += len(records)
            summary["totals"]["products_imported"] += imported
            summary["totals"]["errors"] += errors

        return summary

    finally:
        connection.close()


if __name__ == "__main__":
    print(json.dumps(import_son_data(), indent=2))
