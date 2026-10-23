"""Compare scanned product details with local NAFDAC registry records."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any

from backend.db import DEFAULT_DB_PATH, get_connection, normalize_registration_number

NAME = "nafdac_registry"

APPLIES_TO = {
    "drug", "drugs", "medicine", "cosmetic", "food", "drink", "spirits", "water",
    "herbal", "herbals and nutraceuticals", "medical device",
    "medical devices", "veterinary", "vaccines and biologics",
}

CRITICAL = True


def _normalise_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"[^a-z0-9]+", " ", str(value).casefold()).strip()


def _value(product: dict, *keys: str) -> Any:
    identifiers = product.get("identifiers")
    if not isinstance(identifiers, dict):
        identifiers = {}

    for key in keys:
        value = identifiers.get(key)
        if value is None or not str(value).strip():
            value = product.get(key)
        if value is not None and str(value).strip():
            return value
    return None


def _evidence(result: str, detail: str, weight: float = 1.0) -> dict:
    return {
        "check": NAME,
        "result": result,
        "detail": detail,
        "source": "local_nafdac_registry",
        "weight": weight,
    }


def _db_path(ctx: Any) -> Path:
    if isinstance(ctx, dict) and ctx.get("db_path"):
        return Path(ctx["db_path"])
    return DEFAULT_DB_PATH


def _contains_match(left: str, right: str) -> bool:
    if not left or not right:
        return False
    return left == right or left in right or right in left


def run(product: dict, ctx: Any = None) -> dict:
    """Return registry evidence; this check does not prove physical authenticity."""
    if not isinstance(product, dict):
        return _evidence("unknown", "Invalid product input.", 0.0)

    number = normalize_registration_number(
        _value(product, "nafdac_no", "NAFDAC", "nafdac_number")
    )
    if not number:
        return _evidence(
            "unknown",
            "No NAFDAC registration number was supplied.",
            0.0,
        )

    name = _normalise_text(_value(product, "name", "product_name"))
    brand = _normalise_text(_value(product, "brand"))
    strength = _normalise_text(_value(product, "strength"))
    manufacturer = _normalise_text(
        _value(product, "manufacturer", "manufacturer_name", "applicant_name")
    )

    if not any((name, brand, strength, manufacturer)):
        return _evidence(
            "unknown",
            "A registration number was supplied, but no product details were available to compare.",
            0.0,
        )

    connection = None
    try:
        connection = get_connection(_db_path(ctx))
        rows = connection.execute(
            """
            SELECT nafdac_number, product_name, applicant_name, strength,
                   status, expiry_date
            FROM registry_records
            WHERE nafdac_normalized = ?
            ORDER BY product_id
            """,
            (number,),
        ).fetchall()
    except (sqlite3.Error, OSError) as error:
        return _evidence(
            "unknown",
            f"Local registry lookup failed ({type(error).__name__}).",
            0.0,
        )
    finally:
        if connection is not None:
            connection.close()

    if not rows:
        return _evidence(
            "unknown",
            f"Registration number {number} was not found in the local dataset. This alone does not establish counterfeiting.",
            0.0,
        )

    active_rows = [
        row for row in rows
        if _normalise_text(row["status"]) == "active"
    ]

    if not active_rows:
        statuses = sorted({str(row["status"] or "Unknown") for row in rows})
        return _evidence(
            "unknown",
            f"No matching record is marked Active. Recorded status: {', '.join(statuses)}. Verify with the official source.",
            0.5,
        )

    discrepancies = set()

    for row in active_rows:
        registered_name = _normalise_text(row["product_name"])
        registered_manufacturer = _normalise_text(row["applicant_name"])
        registered_strength = _normalise_text(row["strength"])

        name_matches = (
            not name
            or not registered_name
            or _contains_match(name, registered_name)
            or (brand and _contains_match(brand, registered_name))
        )
        manufacturer_matches = (
            not manufacturer
            or not registered_manufacturer
            or _contains_match(manufacturer, registered_manufacturer)
        )
        strength_matches = (
            not strength
            or not registered_strength
            or strength == registered_strength
        )

        if name_matches and manufacturer_matches and strength_matches:
            details = [
                f"Registration number {number} matches an Active local registry record."
            ]
            if row["product_name"]:
                details.append(f"Registered product: {row['product_name']}.")
            if row["applicant_name"]:
                details.append(f"Registered applicant: {row['applicant_name']}.")
            if row["expiry_date"]:
                details.append(
                    f"Registry record expiry date: {row['expiry_date']}."
                )
            details.append(
                "This local-record match is not independent proof of the physical product's authenticity."
            )
            return _evidence("pass", " ".join(details))

        reasons = []
        if not name_matches:
            reasons.append("product name/brand differs")
        if not manufacturer_matches:
            reasons.append("manufacturer/applicant differs")
        if not strength_matches:
            reasons.append("strength differs")
        discrepancies.add("; ".join(reasons))

    return _evidence(
        "fail",
        f"Registration number {number} exists in Active local records, but the submitted details conflict with all matching active records ({'; '.join(sorted(discrepancies))}). This is a discrepancy requiring further verification, not proof of counterfeiting.",
    )
