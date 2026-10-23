from pathlib import Path

import pytest

from backend.db import get_connection
from backend.checks.registry import run


@pytest.fixture
def registry_db(tmp_path: Path) -> Path:
    """Create an isolated database with one registered product."""
    db_path = tmp_path / "test_registry.sqlite3"

    connection = get_connection(db_path)
    try:
        connection.execute(
            """
            INSERT INTO registry_products (
                country, source, reg_no, reg_key, product_name,
                strength, applicant, category, status, approval_date,
                expiry_date, detail_url
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "NG",
                "nafdac_greenbook",
                "A4-100167",
                "A4-100167",
                "Example Medicine 10mg",
                "10mg",
                "Example Pharma Ltd",
                "Drugs",
                "active",
                "2025-01-01",
                "2027-01-01",
                None,
            ),
        )
        connection.commit()
    finally:
        connection.close()

    return db_path


def make_product(**overrides):
    product = {
        "category": "drug",
        "name": "Example Medicine 10mg",
        "strength": "10mg",
        "identifiers": {
            "nafdac_no": "A4-100167",
            "manufacturer": "Example Pharma Ltd",
        },
    }
    product.update(overrides)
    return product


def check_product(product, db_path):
    """Run the checker using its actual connection-based interface."""
    connection = get_connection(db_path)
    try:
        return run(
            product,
            {"conn": connection, "country": "NG"},
        )
    finally:
        connection.close()


def test_matching_active_record_passes(registry_db):
    result = check_product(make_product(), registry_db)

    assert result["result"] == "pass"
    assert result["check"] == "registry_fit"


def test_unknown_registration_is_unknown(registry_db):
    product = make_product(
        identifiers={"nafdac_no": "NOT-REGISTERED"}
    )

    result = check_product(product, registry_db)

    assert result["result"] == "unknown"
    assert "does not establish" in result["detail"]


def test_missing_registration_is_unknown(registry_db):
    result = check_product({"name": "Example Medicine 10mg"}, registry_db)

    assert result["result"] == "unknown"
    assert "No NAFDAC registration number" in result["detail"]


def test_name_mismatch_fails(registry_db):
    product = make_product(name="Completely Different Product")

    result = check_product(product, registry_db)

    assert result["result"] == "fail"
    assert "not by itself proof of counterfeiting" in result["detail"]


def test_inactive_record_is_unknown(registry_db):
    connection = get_connection(registry_db)
    try:
        connection.execute(
            "UPDATE registry_products SET status = 'inactive'"
        )
        connection.commit()
    finally:
        connection.close()

    result = check_product(make_product(), registry_db)

    assert result["result"] == "unknown"
    assert "Confirm the current registration status" in result["detail"]


def test_duplicate_number_passes_if_matching_record_exists(registry_db):
    connection = get_connection(registry_db)
    try:
        connection.execute(
            """
            INSERT INTO registry_products (
                country, source, reg_no, reg_key, product_name,
                strength, applicant, category, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "NG",
                "nafdac_greenbook",
                "A4-100167",
                "A4-100167",
                "Unrelated Product",
                "500mg",
                "Other Company",
                "Drugs",
                "active",
            ),
        )
        connection.commit()
    finally:
        connection.close()

    result = check_product(make_product(), registry_db)

    assert result["result"] == "pass"


def test_missing_connection_returns_unknown():
    result = run(make_product(), {"country": "NG"})

    assert result["result"] == "unknown"
    assert "connection is unavailable" in result["detail"]


def test_strength_mismatch_fails(registry_db):
    product = make_product(strength="500mg")

    result = check_product(product, registry_db)

    assert result["result"] == "fail"
    assert "differs from the registered strength" in result["detail"]


def test_manufacturer_mismatch_fails(registry_db):
    product = make_product(
        identifiers={
            "nafdac_no": "A4-100167",
            "manufacturer": "Different Manufacturer Ltd",
        }
    )

    result = check_product(product, registry_db)

    assert result["result"] == "fail"
    assert "differs from the registered applicant" in result["detail"]


@pytest.mark.parametrize(
    "product",
    [
        None,
        {},
        {"identifiers": None},
        {"identifiers": "not-a-dictionary"},
        {"identifiers": {"nafdac_no": None}},
        {"identifiers": {"nafdac_no": 12345}},
    ],
)
def test_malformed_product_input_returns_unknown(registry_db, product):
    result = check_product(product, registry_db)

    assert result["result"] == "unknown"
    assert result["check"] == "registry_fit"


@pytest.mark.parametrize(
    "registry_expiry",
    ["2020-01-01", "not-a-valid-date", None],
)
def test_registry_expiry_values_do_not_crash_lookup(
    registry_db, registry_expiry
):
    connection = get_connection(registry_db)
    try:
        connection.execute(
            "UPDATE registry_products SET expiry_date = ?",
            (registry_expiry,),
        )
        connection.commit()
    finally:
        connection.close()

    result = check_product(make_product(), registry_db)

    # The current checker does not evaluate registry expiry dates.
    assert result["result"] == "pass"


def test_package_expiry_is_not_used_as_registry_expiry(registry_db):
    product = make_product(
        identifiers={
            "nafdac_no": "A4-100167",
            "expiry": "2020-01-01",
        }
    )

    result = check_product(product, registry_db)

    assert result["result"] == "pass"
    assert "package expiry" not in result["detail"].lower()


@pytest.mark.parametrize(
    "category",
    [
        "Drugs",
        "Medical devices",
        "Vaccines and Biologics",
        "Herbals and Nutraceuticals",
        "Veterinary",
    ],
)
def test_dataset_categories_are_represented_in_registry_check(category):
    from backend.checks.registry import APPLIES_TO

    supported = {value.casefold() for value in APPLIES_TO}

    assert category.casefold() in supported
