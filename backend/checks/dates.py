"""Expiry / manufacture date sanity."""
from normalize import parse_month, today_month, month_str

NAME = "date_sanity"
APPLIES_TO = {"*"}
CRITICAL = False


def run(product, ctx):
    from checks import result
    ids = product.get("identifiers") or {}
    exp = parse_month(ids.get("expiry"))
    mfg = parse_month(ids.get("mfg_date"))
    if not exp and not mfg:
        return None
    now = today_month()
    if exp and mfg and mfg >= exp:
        return result(NAME, "fail", f"Manufacture date {month_str(mfg)} is not before expiry {month_str(exp)}", weight=25)
    if mfg and mfg > now:
        return result(NAME, "fail", f"Manufacture date {month_str(mfg)} is in the future", weight=25)
    if exp and exp < now:
        ctx["expired"] = True
        return result(NAME, "fail", f"Expired in {month_str(exp)}", weight=30)
    if exp and mfg and (exp[0] - mfg[0]) > 10:
        return result(NAME, "fail", "Shelf life over 10 years is implausible", weight=15)
    return result(NAME, "pass", f"Dates look valid (expiry {month_str(exp) or 'not read'})", weight=5)
