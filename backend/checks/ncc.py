"""NCC Device Checker (phones, tablets, modems, POS terminals), in effect since 7 Oct 2026.

How we use it (and how we don't):
- Always: give the user the official NCC result link for their IMEI (they can also dial *315#).
- Optional server lookup (CHECKAM_NCC_LOOKUP=1): a plain GET of the public result page,
  rate-limited and cached. If NCC's page doesn't return a readable result to a plain request
  (it uses a handshake script), we stop there and fall back to the link. We never try to
  get around protections on the site.
- Wording: NCC says a failed check isn't proof of a counterfeit, so we say
  "Not verified by NCC, ask the seller", never "fake".
"""
import os
import re
import sqlite3
import time
import urllib.request

from normalize import digits

NAME = "ncc_device_check"
APPLIES_TO = {"phone"}
CRITICAL = False

RESULT_URL = "https://embed-ncc.registermydevice.ng/result?imei={imei}"
CHECKER_URL = "https://ncc.gov.ng/devicechecker"
SOURCE = "NCC Device Checker"
_last_call = [0.0]
MIN_INTERVAL = 2.0  # seconds between live lookups


def _cache(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS ncc_cache (
        imei TEXT PRIMARY KEY, checked_at TEXT DEFAULT (datetime('now')),
        verified INTEGER, type_approved INTEGER, brand TEXT, model TEXT, device_name TEXT)""")
    return conn


def _parse(html: str):
    """Pull fields out of the result page text. Returns None if the page isn't a readable result."""
    text = re.sub(r"<[^>]+>", "\n", html)
    text = re.sub(r"\n\s*\n+", "\n", text)
    if "Verification Status" not in text and "NCC Type Approved" not in text:
        return None

    def field(label):
        m = re.search(rf"{label}\s*\n\s*([^\n]+)", text)
        return m.group(1).strip() if m else None

    status = (field("Verification Status") or "").lower()
    approved = (field("NCC Type Approved") or "").lower()
    return {
        "verified": 1 if status.startswith("verified") else 0 if status else None,
        "type_approved": 1 if approved.startswith("yes") else 0 if approved else None,
        "brand": field("Brand Name"), "model": field("Model"), "device_name": field("Device Name"),
    }


def lookup(imei: str, conn):
    """Cached result dict, or None when no readable result is available."""
    _cache(conn)
    row = conn.execute("SELECT * FROM ncc_cache WHERE imei = ?", (imei,)).fetchone()
    if row:
        return dict(row)
    if os.environ.get("CHECKAM_NCC_LOOKUP") != "1":
        return None
    wait = MIN_INTERVAL - (time.time() - _last_call[0])
    if wait > 0:
        time.sleep(wait)
    _last_call[0] = time.time()
    try:
        req = urllib.request.Request(RESULT_URL.format(imei=imei), headers={"User-Agent": "CheckAm/0.1"})
        html = urllib.request.urlopen(req, timeout=6).read().decode("utf-8", "ignore")
    except Exception:
        return None
    data = _parse(html)
    if data is None:
        return None
    conn.execute("INSERT OR REPLACE INTO ncc_cache (imei, verified, type_approved, brand, model, device_name) "
                 "VALUES (?,?,?,?,?,?)", (imei, data["verified"], data["type_approved"], data["brand"],
                                          data["model"], data["device_name"]))
    conn.commit()
    return data


def save_user_result(conn, imei, verified, type_approved=None, brand=None, model=None, device_name=None):
    """Store a result the user read off the NCC page themselves (or a demo pre-fetch)."""
    _cache(conn)
    conn.execute("INSERT OR REPLACE INTO ncc_cache (imei, verified, type_approved, brand, model, device_name) "
                 "VALUES (?,?,?,?,?,?)", (imei, verified, type_approved, brand, model, device_name))
    conn.commit()


def run(product, ctx):
    from checks import result
    ids = product.get("identifiers") or {}
    imei = digits(ids.get("imei_device") or ids.get("imei"))
    from checks.imei import valid_imei
    if not valid_imei(imei):
        return None  # imei_check already explains what's missing or invalid
    link = RESULT_URL.format(imei=imei)
    ctx.setdefault("links", []).append({"label": "Check on NCC Device Checker", "url": link})

    data = lookup(imei, ctx["conn"])
    if data is None:
        return result(NAME, "unknown",
                      f"Check IMEI {imei} on the NCC Device Checker (link below, or dial *315#).", link, weight=0)

    name = data.get("device_name") or " ".join(x for x in [data.get("brand"), data.get("model")] if x) or "a device"
    if data.get("verified") == 1:
        detail = f"Verified by NCC: {name}" + (", NCC type approved" if data.get("type_approved") == 1 else "")
        claimed = " ".join(x for x in [product.get("brand"), product.get("name")] if x).lower()
        ncc_brand = (data.get("brand") or "").lower()
        if claimed and ncc_brand and ncc_brand not in claimed:
            ctx.setdefault("critical_fails", []).append(NAME)
            return result(NAME, "fail",
                          f"NCC says IMEI {imei} belongs to {name}, not the {product.get('brand')} "
                          f"{product.get('name') or ''} being sold. Ask the seller.".replace("  ", " "),
                          link, weight=50)
        return result(NAME, "pass", detail + ".", link, weight=25)
    return result(NAME, "fail", f"Not verified by NCC for IMEI {imei}. Ask the seller before you pay "
                  "(NCC says a failed check isn't proof of a fake on its own).", link, weight=20)
