"""Prior buyer reports on this batch."""
from normalize import norm_batch

NAME = "prior_reports"
APPLIES_TO = {"*"}
CRITICAL = False


def run(product, ctx):
    from checks import result
    batch = norm_batch((product.get("identifiers") or {}).get("batch"))
    if not batch:
        return None
    brand = (product.get("brand") or "").lower()
    rows = ctx["conn"].execute(
        "SELECT state, market FROM reports WHERE batch = ? AND lower(coalesce(brand,'')) = ?",
        (batch, brand),
    ).fetchall()
    if not rows:
        return None
    places = sorted({", ".join(x for x in [r["market"], r["state"]] if x) for r in rows} - {""})
    n = len(rows)
    ctx["prior_reports"] = n
    return result(NAME, "fail",
                  f"Reported as fake by {n} other buyer{'s' if n != 1 else ''}"
                  + (f" ({'; '.join(places[:3])})" if places else ""),
                  "Check Am buyer reports", weight=min(25 + 10 * (n - 1), 45))
