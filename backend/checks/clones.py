"""Clone detection on scan history.

A genuine batch has one expiry date. The same batch seen with a different
expiry means someone copied the batch number. A serial seen in many states
means a copied serial/IMEI.
"""
from normalize import norm_batch, parse_month, month_str

NAME = "clone_detection"
APPLIES_TO = {"*"}
CRITICAL = True
SERIAL_STATES_LIMIT = 3


def run(product, ctx):
    from checks import result
    conn = ctx["conn"]
    ids = product.get("identifiers") or {}
    batch = norm_batch(ids.get("batch"))
    brand = (product.get("brand") or "").lower()
    out = []

    if batch:
        exp = parse_month(ids.get("expiry"))
        rows = conn.execute(
            "SELECT expiry, state, created_at FROM scans WHERE batch = ? AND lower(coalesce(brand,'')) = ?",
            (batch, brand),
        ).fetchall()
        if exp:
            other = [r for r in rows if r["expiry"] and parse_month(r["expiry"]) and parse_month(r["expiry"]) != exp]
            if other:
                where = sorted({r["state"] for r in other if r["state"]})
                ctx.setdefault("critical_fails", []).append(NAME)
                return result(
                    NAME, "fail",
                    f"Batch {batch} has been scanned with a different expiry "
                    f"({month_str(parse_month(other[0]['expiry']))} vs {month_str(exp)})"
                    + (f" in {', '.join(where)}" if where else "")
                    + ". A real batch has one expiry date, so this batch number has been copied.",
                    "Check Am scan history", weight=60)
        if rows:
            out = result(NAME, "pass",
                         f"Batch {batch} seen in {len(rows)} earlier scan(s), all consistent", "Check Am scan history",
                         weight=10)
        else:
            out = result(NAME, "unknown", f"First time we've seen batch {batch}", "Check Am scan history", weight=0)

    serial = (ids.get("serial") or ids.get("imei") or "").strip()
    if serial:
        states = {r["state"] for r in conn.execute(
            "SELECT DISTINCT state FROM scans WHERE serial = ? AND state IS NOT NULL", (serial,)).fetchall()}
        here = (ctx.get("location") or {}).get("state")
        if here:
            states.add(here)
        if len(states) > SERIAL_STATES_LIMIT:
            ctx.setdefault("critical_fails", []).append(NAME)
            return result(NAME, "fail",
                          f"Serial {serial} has been scanned in {len(states)} different states. "
                          "Each unit has one serial, so it has been copied.",
                          "Check Am scan history", weight=60)

    return out or None
