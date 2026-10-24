"""Who owns this barcode? Looks it up in Open Food Facts / Open Beauty Facts and compares the brand.

Fakes often print a random or copied barcode. If the barcode belongs to another product, that's a red flag.
Runs only on online scans (research on) and caches lookups. Not found in the open databases says nothing:
many Nigerian products simply aren't listed there.
"""
import json
import re

NAME = "barcode_owner"
APPLIES_TO = {"food", "drink", "spirits", "water", "cosmetic"}
CRITICAL = False

GENERIC = {"the", "and", "ltd", "limited", "plc", "inc", "company", "foods", "food", "drinks", "nigeria",
           "flavour", "flavor", "original", "classic", "new", "brand"}


def _tokens(text):
    return {t for t in re.findall(r"[a-z0-9]+", (text or "").lower()) if len(t) >= 3 and t not in GENERIC}


def _lookup(conn, code):
    conn.execute("CREATE TABLE IF NOT EXISTS barcode_cache (code TEXT PRIMARY KEY, data_json TEXT, "
                 "checked_at TEXT DEFAULT (datetime('now')))")
    row = conn.execute("SELECT data_json FROM barcode_cache WHERE code = ?", (code,)).fetchone()
    if row:
        return json.loads(row["data_json"])
    import web_search
    rec = web_search.barcode_lookup(code)
    conn.execute("INSERT OR REPLACE INTO barcode_cache (code, data_json) VALUES (?, ?)", (code, json.dumps(rec)))
    conn.commit()
    return rec


def run(product, ctx):
    from checks import result
    from normalize import digits
    code = digits((product.get("identifiers") or {}).get("barcode"))
    if not ctx.get("online") or len(code) < 8 or "barcode" in ctx.get("retake", []):
        return None
    claimed = " ".join(x for x in [product.get("brand"), product.get("name")] if x)
    if not claimed:
        return None
    rec = _lookup(ctx["conn"], code)
    if not rec:
        return None
    listed = " ".join(x for x in [rec.get("brand"), rec.get("name")] if x)
    ref = ctx.get("reference") or {}
    known = _tokens(claimed) | _tokens(ref.get("manufacturer")) | _tokens(ref.get("official_name"))
    if _tokens(product.get("brand")) & _tokens(listed) or _tokens(rec.get("brand")) & known:
        return result(NAME, "pass", f"{rec['source']} lists barcode {code} as {listed}, the same brand as this pack.",
                      rec["url"], weight=15)
    return result(NAME, "fail", f"{rec['source']} lists barcode {code} as {listed}, not {claimed}. "
                  "Fakes often reuse another product's barcode.", rec["url"], weight=25)
