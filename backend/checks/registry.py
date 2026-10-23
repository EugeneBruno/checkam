"""NAFDAC registry fit: does the printed number belong to THIS product?

Sources in registry_products: 'nafdac_greenbook' (bulk snapshot) and
'napams_user_confirmed' (screenshots users shared after checking NAPAMS).
A number missing from our data is never treated as fake.
"""
from normalize import reg_key, name_similarity

NAME = "registry_fit"
APPLIES_TO = {"drug", "cosmetic", "food", "drink", "spirits", "water", "herbal", "medical_device"}
CRITICAL = True  # only when the number clearly belongs to another product

NAPAMS_URL = "https://registration.nafdac.gov.ng/#verify"
MATCH = 0.6


def _label(row):
    if row["source"] == "napams_user_confirmed":
        when = (row["confirmed_at"] or "")[:10]
        return f"NAPAMS (confirmed by a user {when})".strip()
    return "NAFDAC Greenbook snapshot"


def run(product, ctx):
    from checks import result
    ids = product.get("identifiers") or {}
    printed = ids.get("nafdac_no")
    if not printed:
        return result(NAME, "unknown", "No NAFDAC number read from the pack", weight=0)

    key = reg_key(printed)
    rows = ctx["conn"].execute(
        "SELECT * FROM registry_products WHERE country = ? AND reg_key = ?",
        (ctx.get("country", "NG"), key),
    ).fetchall()
    if not rows:
        ctx.setdefault("flags", []).append("confirm_on_napams")
        return result(NAME, "unknown",
                      f"NAFDAC number {printed} is not in our records yet. Confirm it on NAFDAC (NAPAMS).",
                      NAPAMS_URL, weight=0)

    claimed = " ".join(x for x in [product.get("brand"), product.get("name"), product.get("variant")] if x)
    best = max(rows, key=lambda r: name_similarity(claimed, r["product_name"] or ""))
    sim = name_similarity(claimed, best["product_name"] or "")
    src = best["detail_url"] or _label(best)

    if claimed and sim < MATCH:
        ctx.setdefault("critical_fails", []).append(NAME)
        return result(NAME, "fail",
                      f"NAFDAC number {best['reg_no']} belongs to a different product: "
                      f"\"{best['product_name']}\" ({best['applicant'] or 'unknown holder'}), "
                      f"not \"{claimed}\". [{_label(best)}]",
                      src, weight=60)

    # Strength check for drugs, when both sides have it
    strength = (product.get("strength") or "").replace(" ", "").lower()
    reg_strength = (best["strength"] or "").replace(" ", "").lower()
    if strength and reg_strength and strength not in reg_strength and reg_strength not in strength:
        return result(NAME, "fail",
                      f"Strength on pack ({product.get('strength')}) differs from registration ({best['strength']})",
                      src, weight=40)

    status = (best["status"] or "").lower()
    if status and status != "active":
        return result(NAME, "unknown",
                      f"Registered as \"{best['product_name']}\" but registration is {status}. "
                      "Could be old stock; be careful.", src, weight=10)

    return result(NAME, "pass",
                  f"NAFDAC number {best['reg_no']} matches \"{best['product_name']}\" "
                  f"({best['applicant'] or 'holder unknown'}). [{_label(best)}]",
                  src, weight=30)
