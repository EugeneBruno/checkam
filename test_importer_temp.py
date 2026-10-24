import json
import tempfile
from pathlib import Path

from backend.db import connect
from backend.load_data import load_greenbook

with tempfile.TemporaryDirectory() as temp_dir:
    root = Path(temp_dir)
    db_path = root / "test.sqlite3"
    json_path = root / "records.json"

    original = {
        "NRN": "TEST-001",
        "Product Name": "Check Am Test Product",
        "Status": "Active",
    }
    json_path.write_text(json.dumps([original]), encoding="utf-8")

    first = load_greenbook(json_path, db_path)
    second = load_greenbook(json_path, db_path)

    changed = {
        **original,
        "Status": "Inactive",
    }
    json_path.write_text(json.dumps([changed]), encoding="utf-8")

    third = load_greenbook(json_path, db_path)

    conn = connect(db_path)
    current = conn.execute(
        "SELECT status FROM registry_products WHERE reg_key = 'TEST-001'"
    ).fetchone()
    versions = conn.execute(
        "SELECT COUNT(*) FROM registry_source_versions WHERE reg_key = 'TEST-001'"
    ).fetchone()[0]
    conn.close()

    print("First import:", first)
    print("Identical import:", second)
    print("Changed import:", third)
    print("Current status:", current["status"])
    print("Historical versions:", versions)

    assert first["imported"] == 1
    assert second["skipped"] == 1
    assert third["imported"] == 1
    assert current["status"] == "inactive"
    assert versions == 2

    print("PASS: importer handles unchanged and changed records correctly.")
