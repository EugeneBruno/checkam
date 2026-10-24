
"""NAFDAC registry fit: check whether a registration number matches a product."""

from __future__ import annotations

import re
from typing import Any

NAME = "registry_fit"

APPLIES_TO = {
    "drug", "drugs", "medicine", "cosmetic", "food", "drink",
    "spirits", "water", "herbal", "herbals and nutraceuticals",
    "medical_device", "medical device", "medical devices",
    "veterinary", "vaccines and biologics",
}

# Categories we currently treat as covered by the imported snapshot.
# Expand this only after confirming coverage in the source dataset.
SNAPSHOT_COVERED_CATEGORIES = {
    "drug",
    "drugs",
    "medicine",
    "veterinary",
    "vaccines and biologics",
    "herbal",
    "herbals and nutraceuticals",
}


CRITICAL = True

NAPAMS_URL = "https://registration.nafdac.gov.ng/Home/VerifyProduct"


def _normalise_text(value: Any) -> str:
    """Normalize text for comparison without changing stored source data."""
    if value is None:
        return ""
    return re.sub(r"[^a-z0-9]+", " ", str(value).casefold()).strip()


def _reg_key(value: Any) -> str:
    """Normalize whitespace and case while preserving meaningful punctuation."""
    if value is None:
        return ""
    return " ".join(str(value).strip().upper().split())


def _value(product: dict, *keys: str) -> Any:
    """Read product fields, supporting the agreed identifiers structure."""
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


def _evidence(
    result: str,
    detail: str,
    source: str = "NAFDAC Greenbook local snapshot",
    weight: float = 0.0,
) -> dict:
    """Use the shared checks result interface."""
    from checks import result as make_result

    return make_result(
        NAME,
        result,
        detail,
        source,
        weight=weight,
    )


def _contains_match(left: str, right: str) -> bool:
    if not left or not right:
        return False
    return left == right or left in right or right in left


def _source_label(row: Any) -> str:
    source = row["source"] or "nafdac_greenbook"
    if source == "napams_user_confirmed":
        confirmed_at = row["confirmed_at"] or ""
        return f"NAPAMS user-confirmed record ({confirmed_at[:10]})".strip()
    return "NAFDAC Greenbook local snapshot"


def run(product: dict, ctx: Any = None) -> dict:
    """Return registry evidence; a record match cannot prove physical authenticity."""
    if not isinstance(product, dict):
        return _evidence("unknown", "Invalid product input.")

    printed_number = _value(
        product, "nafdac_no", "NAFDAC", "nafdac_number"
    )
    number = _reg_key(printed_number)

    
    if not number:
        # Search the local registry by name when OCR misses the number.
        # A name match is a candidate, not proof of authenticity.
        if not isinstance(ctx, dict) or ctx.get("conn") is None:
            return _evidence(
                "unknown",
                "No NAFDAC number was read and the local registry is unavailable.",
            )

        brand = str(product.get("brand") or "").strip()
        name = str(
            product.get("name") or product.get("product_name") or ""
        ).strip()

        if not (brand or name):
            return _evidence(
                "unknown",
                "No NAFDAC number or usable product name was detected.",
            )

        try:
            candidates = ctx["conn"].execute(
                """
                SELECT reg_no, product_name, category, status,
                       applicant, manufacturer
                FROM registry_products
                WHERE country = ?
                  AND source = 'nafdac_greenbook'
                  AND product_name IS NOT NULL
                  AND LOWER(product_name) LIKE ?
                LIMIT 50
                """,
                (ctx.get("country", "NG"), f"%{name.casefold()}%"),
            ).fetchall() if name else []
        except Exception:
            candidates = []

        claimed_brand = _normalise_text(brand)
        matches = []

        for row in candidates:
            registered_name = _normalise_text(row["product_name"])
            if not registered_name:
                continue

            # Require the product name to match, and check the brand
            # separately when one was detected.
            name_match = _contains_match(
                _normalise_text(name), registered_name
            )
            brand_match = (
                not claimed_brand or claimed_brand in registered_name
            )

            if name_match and brand_match:
                matches.append(row)

        if len(matches) == 1:
            match = matches[0]
            ctx["registry_candidate"] = {
                "product_name": match["product_name"],
                "registration_number": match["reg_no"],
                "manufacturer": match["manufacturer"] or match["applicant"],
                "status": match["status"],
                "source": "NAFDAC Greenbook local snapshot",
                "match_status": "candidate_only",
            }
            return _evidence(
                "unknown",
                (
                    f"Possible local registry match: "
                    f"'{match['product_name']}' "
                    f"(registration {match['reg_no']}). "
                    "The registration number was not read from the "
                    "package, so this match is not confirmed."
                ),
                weight=0,
            )

        if matches:
            return _evidence(
                "unknown",
                f"Found {len(matches)} possible local product matches. "
                "A readable registration number or clearer product photo is needed.",
                weight=0,
            )

        return _evidence(
            "unknown",
            "No NAFDAC number was read and no sufficiently clear local name match was found.",
            weight=0,
        )


    if not isinstance(ctx, dict) or ctx.get("conn") is None:
        return _evidence(
            "unknown",
            "Registry database connection is unavailable.",
        )

    connection = ctx["conn"]
    country = ctx.get("country", "NG")

    try:
        rows = connection.execute(
            """
            SELECT *
            FROM registry_products
            WHERE country = ? AND reg_key = ?
            """,
            (country, number),
        ).fetchall()
    except Exception as exc:
        return _evidence(
            "unknown",
            f"Local registry lookup failed ({type(exc).__name__}).",
        )

    if not rows:
        ctx.setdefault("flags", []).append("confirm_on_napams")
        return _evidence(
            "unknown",
            (
                f"Registration number {printed_number} was not found in "
                "the local Greenbook dataset. This does not establish "
                "that the product is counterfeit. A secondary NAPAMS "
                "verification is needed."
            ),
            NAPAMS_URL,
        )

    claimed_name = " ".join(
        str(value).strip()
        for value in (
            product.get("brand"),
            product.get("name") or product.get("product_name"),
            product.get("variant"),
        )
        if value and str(value).strip()
    )

    claimed_name_normalized = _normalise_text(claimed_name)
    claimed_strength = _normalise_text(product.get("strength"))
    claimed_manufacturer = _normalise_text(
        _value(product, "manufacturer", "manufacturer_name", "applicant")
    )

    def similarity_key(row: Any) -> tuple[int, int]:
        registered_name = _normalise_text(row["product_name"])
        exact_or_contained = (
            bool(claimed_name_normalized)
            and bool(registered_name)
            and (
                claimed_name_normalized == registered_name
                or claimed_name_normalized in registered_name
                or registered_name in claimed_name_normalized
            )
        )
        return (int(exact_or_contained), int(bool(registered_name)))

    best = max(rows, key=similarity_key)
    source = best["detail_url"] or _source_label(best)

    registered_name = _normalise_text(best["product_name"])
    registered_manufacturer = _normalise_text(best["applicant"])
    registered_strength = _normalise_text(best["strength"])

    name_matches = (
        not claimed_name_normalized
        or not registered_name
        or _contains_match(claimed_name_normalized, registered_name)
        or _contains_match(registered_name, claimed_name_normalized)
    )

    manufacturer_matches = (
        not claimed_manufacturer
        or not registered_manufacturer
        or _contains_match(claimed_manufacturer, registered_manufacturer)
        or _contains_match(registered_manufacturer, claimed_manufacturer)
    )

    strength_matches = (
        not claimed_strength
        or not registered_strength
        or claimed_strength == registered_strength
    )

    if not name_matches:
        ctx.setdefault("critical_fails", []).append(NAME)
        return _evidence(
            "fail",
            (
                f"Registration number {best['reg_no']} is associated with "
                f"'{best['product_name'] or 'an unnamed product'}', but the "
                f"submitted product is '{claimed_name}'. This is a material "
                "registry discrepancy requiring further verification; "
                "it is not by itself proof of counterfeiting."
            ),
            source,
            weight=60,
        )

    if not manufacturer_matches:
        return _evidence(
            "fail",
            (
                f"The submitted manufacturer/applicant "
                f"('{claimed_manufacturer}') differs from the registered "
                f"applicant ('{best['applicant']}'). Verify the relationship "
                "with the official source."
            ),
            source,
            weight=40,
        )

    if not strength_matches:
        return _evidence(
            "fail",
            (
                f"Submitted strength ('{product.get('strength')}') differs "
                f"from the registered strength ('{best['strength']}')."
            ),
            source,
            weight=40,
        )

    status = _normalise_text(best["status"])

    if status and status != "active":
        return _evidence(
            "unknown",
            (
                f"The matching record lists status '{best['status']}'. "
                "Confirm the current registration status with NAFDAC."
            ),
            source,
            weight=10,
        )

    if not claimed_name_normalized:
        return _evidence(
            "unknown",
            (
                f"Registration number {best['reg_no']} was found for "
                f"'{best['product_name']}', but no submitted product name "
                "was available to compare."
            ),
            source,
            weight=10,
        )

    return _evidence(
        "pass",
        (
            f"Registration number {best['reg_no']} matches the local "
            f"record for '{best['product_name']}'. "
            f"Registered applicant: {best['applicant'] or 'not listed'}. "
            "This registry match does not independently prove that the "
            "physical product or its contents are genuine."
        ),
        source,
        weight=30,
    )
