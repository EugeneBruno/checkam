import sqlite3
from pathlib import Path

import pytest

from backend.db import get_connection
from backend.checks.registry import run


@pytest.fixture
def registry_db(tmp_path: Path) -> Path:
    """Create an isolated registry database for each test."""
    db_path = tmp_path / "test_registry.sqlite3"

    with get_connection(db_path) as connection:
        connection.execute(
            """
            INSERT INTO registry_records (
                product_id, nafdac_number, nafdac_normalized,
                product_name, applicant_name, strength, composition,
                ingredient_name, category_name, status, approval_date,
                expiry_date, source, source_retrieved_at, raw_json,
                content_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "product-1", "A4-100167", "A4-100167",
                "Example Medicine 10mg", "Example Pharma Ltd", "10mg",
                "Example ingredient", "Example ingredient", "Drugs",
                "Active", "2025-01-01", "2027-01-01",
                "test", "2026-01-01T00:00:00+00:00", "{}",
                "hash-1",
            ),
        )

    return db_path


def make_product(**overrides):
    product = {
        "name": "Example Medicine 10mg",
        "strength": "10mg",
        "manufacturer": "Example Pharma Ltd",
        "identifiers": {"nafdac_no": "A4-100167"},
    }
    product.update(overrides)
    return product


def test_matching_active_record_passes(registry_db):
    result = run(make_product(), {"db_path": registry_db})
    assert result["result"] == "pass"


def test_unknown_registration_is_unknown(registry_db):
    product = make_product(
        identifiers={"nafdac_no": "NOT-REGISTERED"}
    )
    result = run(product, {"db_path": registry_db})
    assert result["result"] == "unknown"


def test_missing_registration_is_unknown(registry_db):
    product = {"name": "Example Medicine 10mg"}
    result = run(product, {"db_path": registry_db})
    assert result["result"] == "unknown"


def test_name_mismatch_fails(registry_db):
    product = make_product(name="Completely Different Product")
    result = run(product, {"db_path": registry_db})
    assert result["result"] == "fail"
    assert "not proof of counterfeiting" in result["detail"]


def test_inactive_only_record_is_unknown(registry_db):
    with get_connection(registry_db) as connection:
        connection.execute(
            "UPDATE registry_records SET status = 'Inactive'"
        )

    result = run(make_product(), {"db_path": registry_db})
    assert result["result"] == "unknown"


def test_duplicate_number_passes_if_any_active_record_matches(registry_db):
    with get_connection(registry_db) as connection:
        connection.execute(
            """
            INSERT INTO registry_records (
                product_id, nafdac_number, nafdac_normalized,
                product_name, applicant_name, strength, composition,
                ingredient_name, category_name, status, approval_date,
                expiry_date, source, source_retrieved_at, raw_json,
                content_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "product-2", "A4-100167", "A4-100167",
                "Unrelated Product", "Other Company", "500mg",
                None, None, "Drugs", "Active", None, None,
                "test", "2026-01-01T00:00:00+00:00", "{}",
                "hash-2",
            ),
        )

    result = run(make_product(), {"db_path": registry_db})
    assert result["result"] == "pass"


def test_database_error_returns_unknown(tmp_path):
    # A directory at the expected database path forces a SQLite open error.
    db_path = tmp_path / "not-a-database"
    db_path.mkdir()

    result = run(make_product(), {"db_path": db_path})
    assert result["result"] == "unknown"


def test_strength_mismatch_fails(registry_db):
    product = make_product(strength="500mg")
    result = run(product, {"db_path": registry_db})
    assert result["result"] == "fail"
    assert "strength differs" in result["detail"]


def test_manufacturer_mismatch_fails(registry_db):
    product = make_product(manufacturer="Different Manufacturer Ltd")
    result = run(product, {"db_path": registry_db})
    assert result["result"] == "fail"
    assert "manufacturer/applicant differs" in result["detail"]


@pytest.mark.parametrize("product", [
    None,
    {},
    {"identifiers": None},
    {"identifiers": "not-a-dictionary"},
    {"identifiers": {"nafdac_no": None}},
    {"identifiers": {"nafdac_no": 12345}},
])
def test_malformed_product_input_returns_unknown(registry_db, product):
    result = run(product, {"db_path": registry_db})

    assert result["result"] == "unknown"
    assert result["check"] == "nafdac_registry"


@pytest.mark.parametrize("registry_expiry", [
    "2020-01-01",
    "not-a-valid-date",
    None,
])
def test_registry_expiry_values_do_not_crash_lookup(
    registry_db, registry_expiry
):
    with get_connection(registry_db) as connection:
        connection.execute(
            "UPDATE registry_records SET expiry_date = ?",
            (registry_expiry,),
        )

    result = run(make_product(), {"db_path": registry_db})

    # The current check compares product details, not date validity.
    assert result["result"] == "pass"

    if registry_expiry:
        assert "Registry record expiry date:" in result["detail"]


def test_package_expiry_is_not_mistaken_for_registry_expiry(registry_db):
    product = make_product(
        identifiers={
            "nafdac_no": "A4-100167",
            "expiry": "2020-01-01",
        }
    )

    result = run(product, {"db_path": registry_db})

    assert result["result"] == "pass"
    assert "Registry record expiry date: 2027-01-01" in result["detail"]
    assert "package expiry" not in result["detail"].lower()


@pytest.mark.parametrize("category", [
    "Drugs",
    "Medical devices",
    "Vaccines and Biologics",
    "Herbals and Nutraceuticals",
    "Veterinary",
])
def test_dataset_categories_are_represented_in_registry_check(category):
    from backend.checks.registry import APPLIES_TO

    assert category.casefold() in {
        supported.casefold() for supported in APPLIES_TO
    }
