from backend.checks.registry import run

cases = [
    {"name": "Unknown product", "identifiers": {"nafdac_no": "NOT-A-REAL-NUMBER"}},
    {"name": "Product with no registration number"},
]

for product in cases:
    print(run(product, {}))
