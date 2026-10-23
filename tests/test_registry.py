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
