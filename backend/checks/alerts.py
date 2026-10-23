"""Known fakes from NAFDAC public alerts."""
from normalize import norm_batch, reg_key, name_similarity

NAME = "nafdac_alerts"
APPLIES_TO = {"drug", "cosmetic", "food", "drink", "spirits", "water", "herbal", "medical_device"}
CRITICAL = True


def run(product, ctx):
    from checks import result
    ids = product.get("identifiers") or {}
    batch = norm_batch(ids.get("batch"))
    key = reg_key(ids.get("nafdac_no"))
    claimed = " ".join(x for x in [product.get("brand"), product.get("name")] if x)
    conn = ctx["conn"]
    hits = []
    if batch:
        hits = conn.execute("SELECT * FROM known_fakes WHERE batch = ?", (batch,)).fetchall()
        hits = [h for h in hits if not claimed or not h["product_name"] or name_similarity(claimed, h["product_name"]) >= 0.5]
    if hits:
        h = hits[0]
        ctx.setdefault("critical_fails", []).append(NAME)
        return result(NAME, "fail",
                      f"Batch {batch} matches a NAFDAC alert on counterfeit {h['product_name']}: {h['note'] or ''}".strip(),
                      h["source"], weight=70)
    if key or batch:
        return result(NAME, "pass", "No NAFDAC alert matches this batch", "NAFDAC public alerts", weight=5)
    return None
