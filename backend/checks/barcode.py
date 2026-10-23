"""GTIN/EAN/UPC check digit. Catches invented or mistyped barcodes."""
from normalize import digits

NAME = "barcode_check_digit"
APPLIES_TO = {"*"}
CRITICAL = False


def gtin_valid(code: str) -> bool:
    if len(code) not in (8, 12, 13, 14):
        return False
    body, check = code[:-1], int(code[-1])
    total = 0
    for i, ch in enumerate(reversed(body)):
        total += int(ch) * (3 if i % 2 == 0 else 1)
    return (10 - total % 10) % 10 == check


def run(product, ctx):
    from checks import result
    raw = (product.get("identifiers") or {}).get("barcode")
    code = digits(raw)
    if not code:
        return None
    if gtin_valid(code):
        return result(NAME, "pass", f"Barcode {code} has a valid check digit", weight=5)
    if ctx.get("from_photo") and "barcode" not in ctx.get("typed", set()):
        # Read off a photo: a single misread digit breaks the check, so don't call it fake
        ctx.setdefault("retake", []).append("barcode")
        return result(NAME, "unknown",
                      f"Barcode read from the photo as {code}, but the check digit doesn't add up. "
                      "It may be misread; photograph the barcode up close or type the digits.", weight=0)
    return result(NAME, "fail", f"Barcode {code} has an invalid check digit (likely invented or misprinted)", weight=20)
