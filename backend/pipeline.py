"""verify_product: identify -> run applicable checks -> score -> save scan."""
import json
import uuid

import vision
from checks import applicable
from normalize import norm_batch, reg_key, parse_month, month_str
from scoring import score, next_step


def _merge(base: dict, typed: dict) -> dict:
    """Typed fields (from the user or an AI assistant) fill in / override what vision read."""
    out = dict(base or {})
    ids = dict(out.get("identifiers") or {})
    for k, v in (typed or {}).items():
        if v in (None, "", []):
            continue
        if k in ("nafdac_no", "batch", "expiry", "mfg_date", "barcode", "serial", "imei", "imei_device",
                 "style_code", "son_marks"):
            ids[k] = v
        else:
            out[k] = v
    out["identifiers"] = ids
    return out


def verify_product(conn, images=None, fields=None, situation="before_buying", location=None,
                   country="NG", save=True, progress=None):
    def step(msg):
        if progress:
            progress(msg)

    product = {}
    if images:
        step("Identifying product")
        product = vision.identify(images)
    product = _merge(product, fields)
    if not product.get("category"):
        product["category"] = "other"

    ctx = {"conn": conn, "country": country, "situation": situation, "location": location or {}}

    evidence = []
    for check in applicable(product["category"]):
        step(f"Running {check.NAME.replace('_', ' ')}")
        try:
            r = check.run(product, ctx)
        except Exception as exc:  # one broken check must never break a scan
            r = {"check": check.NAME, "result": "unknown", "detail": f"Check failed: {exc}", "source": None, "weight": 0}
        if r:
            evidence.append(r)

    s = score(evidence, ctx)
    not_checked = [e["check"] for e in evidence if e["result"] == "unknown"]
    if images is None or not images:
        not_checked.append("photo_analysis")
    ids = product.get("identifiers") or {}

    scan_id = "scn_" + uuid.uuid4().hex[:10]
    out = {
        "scan_id": scan_id,
        "situation": situation,
        **s,
        "product": {
            "category": product.get("category"),
            "category_confidence": product.get("category_confidence"),
            "brand": product.get("brand"),
            "name": product.get("name"),
            "variant": product.get("variant"),
            "strength": product.get("strength"),
            "identifiers": ids,
        },
        "contents": product.get("contents") or {},
        "evidence": evidence,
        "not_checked": not_checked,
        "next_step": next_step(product, evidence, ctx, s["verdict"]),
        "prior_reports": ctx.get("prior_reports", 0),
        "links": ctx.get("links", []),
        "actions": (["confirm_on_napams"] if "confirm_on_napams" in ctx.get("flags", []) else [])
                   + (["report"] if s["verdict"] in ("suspicious", "likely_fake") else []),
    }

    if save:
        loc = location or {}
        conn.execute(
            "INSERT INTO scans (id, country, category, brand, product_name, reg_key, batch, expiry, mfg_date, "
            "serial, state, market, verdict, trust_score, result_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (scan_id, country, product.get("category"), product.get("brand"), product.get("name"),
             reg_key(ids.get("nafdac_no")), norm_batch(ids.get("batch")),
             month_str(parse_month(ids.get("expiry"))), month_str(parse_month(ids.get("mfg_date"))),
             (ids.get("serial") or ids.get("imei") or None), loc.get("state"), loc.get("market"),
             s["verdict"], s["trust_score"], json.dumps(out)),
        )
        conn.commit()
    step("Done")
    return out


def report_suspect(conn, scan_id=None, product=None, location=None, seller=None, note=None, reporter="user"):
    """Save a buyer/agent report. Uses the saved scan if scan_id is given."""
    p = dict(product or {})
    if scan_id:
        row = conn.execute("SELECT result_json FROM scans WHERE id = ?", (scan_id,)).fetchone()
        if row:
            saved = json.loads(row["result_json"])["product"]
            p = {**saved, **p}
    ids = p.get("identifiers") or {}
    loc = location or {}
    conn.execute(
        "INSERT INTO reports (scan_id, brand, product_name, reg_key, batch, seller, state, market, note, reporter) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        (scan_id, p.get("brand"), p.get("name"), reg_key(ids.get("nafdac_no")), norm_batch(ids.get("batch")),
         seller, loc.get("state"), loc.get("market"), note, reporter),
    )
    conn.commit()
    batch = norm_batch(ids.get("batch"))
    n = conn.execute("SELECT COUNT(*) FROM reports WHERE batch = ? AND lower(coalesce(brand,'')) = ?",
                     (batch, (p.get("brand") or "").lower())).fetchone()[0] if batch else 0
    return {"ok": True, "batch": batch, "total_reports_for_batch": n,
            "message": "Thanks. Anyone who scans this batch will now see your report."}
