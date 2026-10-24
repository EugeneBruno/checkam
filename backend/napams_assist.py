"""NAPAMS assistant: the agent does the typing and reading, a person does the captcha.

For each NAFDAC number it opens NAFDAC's NAPAMS verify page in a real browser window and types the number in.
YOU tick "I'm not a robot" and press Verify. The agent then reads the result page and saves it to Check Am
as "confirmed on NAPAMS", so every later scan of that number uses it.

If NAPAMS doesn't load within 3 seconds, the research agent looks the number up online instead
(NAFDAC's online Greenbook) and saves what it finds.

It never touches the captcha. NAPAMS protects itself from bots on purpose; a human always answers it.

Setup (once, on your laptop):
    pip install playwright
Run (the Check Am server must be running, with GEMINI_API_KEY set, because it reads the result):
    python napams_assist.py --pending                 numbers people scanned that aren't in our NAFDAC data
    python napams_assist.py 01-4278 E1-4010           these numbers (skips any already in our data)
    python napams_assist.py --file numbers.txt        one number per line
    add --force to re-check numbers we already have

Only numbers missing from our NAFDAC data (Greenbook + earlier NAPAMS confirmations) go to NAPAMS.
"""
import os
import re
import sys
import threading
import time

import httpx

NAPAMS_URL = "https://registration.nafdac.gov.ng/#verify"
SERVER = os.environ.get("CHECKAM_URL", "http://127.0.0.1:8000")
WAIT_S = 240
SHOTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "napams_screenshots")

INPUT_SELECTORS = [
    'input[placeholder*="NRN" i]', 'input[placeholder*="registration" i]', 'input[placeholder*="reg" i]',
    'input[placeholder*="number" i]', 'input[name*="reg" i]', 'input[id*="reg" i]', 'input[name*="nrn" i]',
    '#verify input[type="text"]', '#verify input:not([type])', 'input[type="search"]',
]
RESULT_WORDS = ("product name", "applicant", "holder", "approval date", "expiry date", "registration status",
                "no record", "not found", "no product", "invalid")


def squash(text):
    return re.sub(r"[^A-Z0-9]", "", str(text or "").upper())


def fill_number(page, number):
    """Type the number into the verify box. Returns True if a box was found."""
    for sel in INPUT_SELECTORS:
        try:
            box = page.locator(sel).first
            if box.count() and box.is_visible():
                box.click()
                box.fill(number)
                return True
        except Exception:
            continue
    return False


def looks_like_result(text, before, number):
    """The page changed after Verify and shows a result for this number (or says none was found)."""
    low = (text or "").lower()
    if text == before or not any(w in low for w in RESULT_WORDS):
        return False
    return squash(number) in squash(text) or any(w in low for w in ("no record", "not found", "no product"))


def send_to_checkam(png, number):
    r = httpx.post(f"{SERVER}/confirm-napams", files={"screenshot": (f"{number}.png", png, "image/png")},
                   data={"expected_reg_no": number}, timeout=120)
    if r.status_code != 200:
        return f"Check Am couldn't use it ({r.status_code}): {r.text[:200]}"
    j = r.json()
    if not j.get("found"):
        return "NAPAMS shows no product for this number. Saved nothing (treat this number as suspicious)."
    rec = j.get("record") or {}
    return f"Saved: {rec.get('reg_no')} = {rec.get('product_name')} ({rec.get('holder') or 'holder unknown'})"


LOAD_BUDGET_MS = int(os.environ.get("CHECKAM_NAPAMS_TIMEOUT_MS", "2900"))  # under 3s, then go online instead


def open_napams(page):
    """Open NAPAMS and wait for its number box, all within LOAD_BUDGET_MS. False if it's too slow."""
    start = time.time()
    try:
        page.goto(NAPAMS_URL, wait_until="commit", timeout=LOAD_BUDGET_MS)
        left = max(100, LOAD_BUDGET_MS - int((time.time() - start) * 1000))
        page.wait_for_selector("input", state="visible", timeout=left)
        return True
    except Exception:
        return False


def research_online(number, hint):
    """NAPAMS too slow: ask the Check Am server's research agent to look the number up online instead."""
    print(f"NAPAMS didn't load in {LOAD_BUDGET_MS / 1000:.1f}s. Researching {number} online instead...")
    try:
        r = httpx.post(f"{SERVER}/research-number", json={"reg_no": number, **hint}, timeout=120)
    except httpx.ConnectError:
        print(f"Check Am server isn't running at {SERVER}. Start it and rerun.")
        return
    if r.status_code != 200:
        print(f"Research failed ({r.status_code}): {r.text[:200]}")
        return
    j = r.json()
    for st in j.get("steps", []):
        print(f"  - {st}")
    print(j.get("message"))


def check_one(page, number, hint=None):
    print(f"\n=== {number} ===")
    if not open_napams(page):
        research_online(number, hint or {})
        return
    if fill_number(page, number):
        print(f"Typed {number} into the NAPAMS box.")
    else:
        print(f"Couldn't find the number box. Type {number} into it yourself.")
    print("Now, in the browser window: tick \"I'm not a robot\", then press Verify.")
    print("(Press Enter here if the result is showing but I haven't noticed, or type s + Enter to skip.)")

    before = page.inner_text("body")
    typed = {"value": None}

    def read_terminal():
        try:
            typed["value"] = sys.stdin.readline().strip().lower()
        except Exception:
            typed["value"] = ""
    threading.Thread(target=read_terminal, daemon=True).start()

    start = time.time()
    while time.time() - start < WAIT_S:
        if typed["value"] == "s":
            print("Skipped.")
            return
        try:
            text = page.inner_text("body")
        except Exception:
            text = before
        if typed["value"] is not None or looks_like_result(text, before, number):
            break
        page.wait_for_timeout(1000)
    else:
        print("No result after 4 minutes. Skipped.")
        return

    page.wait_for_timeout(1500)  # let the result finish drawing
    os.makedirs(SHOTS, exist_ok=True)
    path = os.path.join(SHOTS, f"{re.sub(r'[^A-Za-z0-9-]', '_', number)}.png")
    png = page.screenshot(path=path, full_page=True)
    print(f"Result captured ({path}). Reading it...")
    try:
        print(send_to_checkam(png, number))
    except httpx.ConnectError:
        print(f"Check Am server isn't running at {SERVER}. The screenshot is saved; start the server and rerun.")


def _conn():
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from db import connect
    return connect()


def pending_numbers(conn):
    """NAFDAC numbers from real scans that aren't in our data yet (most scanned first)."""
    from normalize import REG_KEY_SQL
    rows = conn.execute(
        "SELECT reg_key, COUNT(*) n FROM scans WHERE reg_key IS NOT NULL AND reg_key != '' AND seeded = 0 "
        "AND reg_key NOT IN (SELECT " + REG_KEY_SQL + " FROM registry_products) GROUP BY reg_key ORDER BY n DESC"
    ).fetchall()
    out = []
    for r in rows:  # show the number as printed on the pack, not the squashed key
        row = conn.execute("SELECT result_json FROM scans WHERE reg_key = ? ORDER BY created_at DESC LIMIT 1",
                           (r["reg_key"],)).fetchone()
        printed = None
        try:
            import json
            printed = ((json.loads(row["result_json"]).get("product") or {}).get("identifiers") or {}).get("nafdac_no")
        except Exception:
            pass
        out.append(printed or r["reg_key"])
    return out


def hint_for(conn, number):
    """What earlier scans of this number said the product is (helps the online research)."""
    import json
    from normalize import reg_key
    row = conn.execute("SELECT result_json FROM scans WHERE reg_key = ? ORDER BY created_at DESC LIMIT 1",
                       (reg_key(number),)).fetchone()
    try:
        p = json.loads(row["result_json"]).get("product") or {}
        return {k: p.get(k) for k in ("category", "brand", "name") if p.get(k)}
    except Exception:
        return {}


def known(conn, number):
    from normalize import reg_key
    from normalize import REG_KEY_SQL
    row = conn.execute("SELECT reg_no, product_name, source FROM registry_products WHERE " + REG_KEY_SQL +
                       " = ? LIMIT 1", (reg_key(number),)).fetchone()
    return row


def main(argv):
    numbers = [a for a in argv if not a.startswith("--")]
    if "--file" in argv:
        path = argv[argv.index("--file") + 1]
        numbers = [n for n in numbers if n != path]
        with open(path, encoding="utf-8") as f:
            numbers += [line.strip() for line in f if line.strip()]
    conn = _conn()
    if "--pending" in argv:
        numbers += pending_numbers(conn)
        print(f"{len(numbers)} scanned number(s) not in our NAFDAC data yet.")
    if "--force" not in argv:
        todo = []
        for n in dict.fromkeys(numbers):
            row = known(conn, n)
            if row:
                print(f"{n}: already in our data ({row['product_name']}, {row['source']}). Skipping.")
            else:
                todo.append(n)
        numbers = todo
    if not numbers:
        print("Nothing to check on NAPAMS." if "--pending" in argv or argv else __doc__)
        return 0
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Run this first:  pip install playwright")
        return 1

    with sync_playwright() as p:
        browser = None
        for kwargs in ({"channel": "msedge"}, {"channel": "chrome"}, {}):  # use a browser already on the laptop
            try:
                browser = p.chromium.launch(headless=False, **kwargs)
                break
            except Exception:
                continue
        if browser is None:
            print("No browser found. Run:  python -m playwright install chromium")
            return 1
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        for n in numbers:
            check_one(page, n, hint_for(conn, n))
        browser.close()
    print("\nDone. Rescan these products to see the result.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
