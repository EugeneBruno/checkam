
from pathlib import Path

from backend.load_son_data import (
    clean_cell,
    parse_markdown_file,
    split_products,
)


def test_clean_cell_converts_html_breaks_to_spaces():
    assert clean_cell("Company<br>Address") == "Company Address"


def test_split_products_handles_semicolon_separated_names():
    assert split_products("Product A; Product B; Product C") == [
        "Product A",
        "Product B",
        "Product C",
    ]


def test_split_products_removes_empty_and_duplicate_names():
    assert split_products("Product A;;Product A; Product B;") == [
        "Product A",
        "Product B",
    ]


def test_food_sector_row_parses_company_address_product_and_state(tmp_path):
    source = tmp_path / "food.md"
    source.write_text(
        "|**S/N**|**COMPANY NAME**|**ADDRESS**|**PRODUCT CERTIFIED**|**STATE**|\n"
        "|---|---|---|---|---|\n"
        "|1|Example Foods Ltd|12 Example Road<br>Lagos|Example Bread|Lagos|\n",
        encoding="utf-8",
    )

    records, stats = parse_markdown_file(source, "food")

    assert len(records) == 1
    assert records[0]["serial_number"] == "1"
    assert records[0]["company_name"] == "Example Foods Ltd"
    assert records[0]["address"] == "12 Example Road Lagos"
    assert records[0]["product_name"] == "Example Bread"
    assert records[0]["state"] == "Lagos"
    assert stats["rows_seen"] == 1
    assert stats["rows_parsed"] == 1


def test_chemical_sector_row_preserves_combined_company_and_address(tmp_path):
    source = tmp_path / "chemical.md"
    source.write_text(
        "|**S/N**|**COMPANY NAME**<br>**ADDRESS**|**PRODUCT CERTIFIED**|**STATE**|\n"
        "|---|---|---|---|\n"
        "|1|Example Chemical Ltd<br>10 Example Road|Example Detergent|Ogun|\n",
        encoding="utf-8",
    )

    records, stats = parse_markdown_file(source, "chemical")

    assert len(records) == 1
    assert records[0]["serial_number"] == "1"
    assert records[0]["company_name"] == "Example Chemical Ltd 10 Example Road"
    assert records[0]["address"] is None
    assert records[0]["product_name"] == "Example Detergent"
    assert records[0]["state"] == "Ogun"
    assert stats["rows_parsed"] == 1


def test_multiple_products_create_separate_records(tmp_path):
    source = tmp_path / "food.md"
    source.write_text(
        "|1|Example Foods Ltd|12 Example Road|Bread A; Bread B|Lagos|\n",
        encoding="utf-8",
    )

    records, _ = parse_markdown_file(source, "food")

    assert [record["product_name"] for record in records] == [
        "Bread A",
        "Bread B",
    ]


def test_missing_source_file_raises_error(tmp_path):
    missing = tmp_path / "missing.md"

    try:
        parse_markdown_file(missing, "food")
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("Expected FileNotFoundError")


def test_real_source_files_have_parseable_records():
    root = Path(__file__).resolve().parents[1]
    sources = [
        (root / "data" / "CHEMICAL-PRODUCTS-SECTOR_compressed.md", "chemical"),
        (root / "data" / "FOOD-PRODUCTS-SECTOR-_compressed-1.md", "food"),
    ]

    for path, sector in sources:
        records, stats = parse_markdown_file(path, sector)

        assert path.is_file()
        assert stats["rows_seen"] > 0
        assert stats["rows_parsed"] > 0
        assert records
        assert all(record["product_name"] for record in records)
        assert all(record["source_row"] for record in records)


def test_food_row_with_missing_state_separator():
    from backend.load_son_data import DEFAULT_SOURCES, parse_markdown_file

    records, stats = parse_markdown_file(
        DEFAULT_SOURCES["food"],
        "food",
    )

    karma = [
        record
        for record in records
        if record["serial_number"] == "715"
    ]

    assert stats["errors"] == 0
    assert len(karma) == 12
    assert all(
        record["company_name"] == "KARMA AGRIC FEEDS AND FOODS LIMITED"
        for record in karma
    )
    assert all(record["state"] == "Oyo" for record in karma)