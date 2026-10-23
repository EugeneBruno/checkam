"""Packaging quality signals read by the vision model (spelling errors, print quality)."""

NAME = "packaging_quality"
APPLIES_TO = {"*"}
CRITICAL = False


def run(product, ctx):
    from checks import result
    pk = product.get("packaging") or {}
    errors = pk.get("spelling_errors") or []
    quality = (pk.get("print_quality") or "unknown").lower()
    if errors:
        return result(NAME, "fail", "Spelling errors on the pack: " + ", ".join(f"\"{e}\"" for e in errors[:4]),
                      "Photo analysis", weight=30)
    if quality == "poor":
        return result(NAME, "fail", "Poor print quality: " + (pk.get("notes") or "blurred or misaligned printing"),
                      "Photo analysis", weight=15)
    if quality == "good":
        return result(NAME, "pass", "No spelling errors; print quality looks normal", "Photo analysis", weight=5)
    return None
