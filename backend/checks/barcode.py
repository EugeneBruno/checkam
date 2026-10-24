"""GTIN/EAN/UPC check digit validation.

A valid check digit confirms only that the barcode is structurally valid.
It does not prove that the barcode was issued legitimately or that a
physical product is genuine.
"""

from normalize import digits

NAME = "barcode_check_digit"
APPLIES_TO = {"*"}
CRITICAL = False


def gtin_valid(code: str) -> bool:
    """Return whether a GTIN-8/12/13/14 has a valid check digit."""
    if not code or not code.isdigit() or len(code) not in (8, 12, 13, 14):
        return False

    body = code[:-1]
    check = int(code[-1])

    total = sum(
        int(ch) * (3 if i % 2 == 0 else 1)
        for i, ch in enumerate(reversed(body))
    )

    return (10 - total % 10) % 10 == check


def run(product, ctx):
    from checks import result

    raw = (product.get("identifiers") or {}).get("barcode")
    code = digits(raw)

    if not code:
        return None

    if gtin_valid(code):
        return result(
            NAME,
            "pass",
            f"Barcode {code} has a valid check digit. This does not establish product authenticity.",
            weight=5,
        )

    if ctx.get("from_photo") and "barcode" not in ctx.get("typed", set()):
        ctx.setdefault("retake", []).append("barcode")
        return result(
            NAME,
            "unknown",
            f"Barcode read from the photo as {code}, but its check digit is invalid. "
            "The image may have been misread. Photograph the barcode closely or type the digits.",
            weight=0,
        )

    return result(
        NAME,
        "unknown",
        f"Barcode {code} has an invalid check digit. It may be mistyped, misprinted, "
        "or incorrectly encoded. Confirm the digits before drawing conclusions about authenticity.",
        weight=0,
    )
