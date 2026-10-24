from backend.db import get_connection
from backend.checks.registry import run

connection = get_connection()

try:
    row = connection.execute("""
        SELECT nafdac_number, product_name, applicant_name, strength, status
        FROM registry_records
        WHERE nafdac_normalized != ''
          AND LOWER(COALESCE(status, '')) = 'active'
        ORDER BY product_id
        LIMIT 1
    """).fetchone()
finally:
    connection.close()

if row is None:
    raise SystemExit("No active sample record found.")

product = {
    "name": row["product_name"],
    "strength": row["strength"],
    "manufacturer": row["applicant_name"],
    "identifiers": {"nafdac_no": row["nafdac_number"]},
}

print("Testing registration:", row["nafdac_number"])
print("Registered product:", row["product_name"])
print("\nMATCH TEST:")
print(run(product, {}))

product["name"] = "Definitely Different Product XYZ"

print("\nMISMATCH TEST:")
print(run(product, {}))
