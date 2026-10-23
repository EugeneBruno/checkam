"""Evidence -> trust score, verdict, confidence, recommendation, next step.

Deterministic on purpose: the same evidence always gives the same verdict.
"""

RECOMMENDATION = {
    "before_buying": {
        "likely_genuine": "buy", "suspicious": "caution",
        "likely_fake": "do_not_buy", "insufficient_evidence": "caution",
    },
    "already_bought": {
        "likely_genuine": "safe_to_use", "suspicious": "caution",
        "likely_fake": "do_not_use", "insufficient_evidence": "caution",
    },
}

STRONG_PASSES = {"registry_fit", "clone_detection", "imei_check", "ncc_device_check", "son_certification"}


def score(evidence: list, ctx: dict) -> dict:
    critical = set(ctx.get("critical_fails", []))
    decided = [e for e in evidence if e["result"] in ("pass", "fail")]
    passes = [e for e in decided if e["result"] == "pass"]
    fails = [e for e in decided if e["result"] == "fail"]

    s = 50 + sum(e["weight"] for e in passes) - sum(e["weight"] for e in fails)
    s = max(0, min(100, s))

    if critical:
        verdict = "likely_fake"
        s = min(s, 15)
    elif len(decided) < 2:
        verdict = "suspicious" if any(e["weight"] >= 30 for e in fails) else "insufficient_evidence"
    elif len(fails) >= 2 and s < 40:
        verdict = "likely_fake"
    elif fails:
        verdict = "suspicious"
    elif s >= 70 and any(e["check"] in STRONG_PASSES for e in passes):
        verdict = "likely_genuine"
    else:
        verdict = "insufficient_evidence"  # nothing wrong found, but nothing strong confirmed either

    if critical or len(decided) >= 4:
        confidence = "high"
    elif len(decided) >= 2:
        confidence = "medium"
    else:
        confidence = "low"

    situation = ctx.get("situation", "before_buying")
    rec = RECOMMENDATION.get(situation, RECOMMENDATION["before_buying"])[verdict]
    if ctx.get("expired"):  # expired is never OK to buy or use, genuine or not
        rec = "do_not_use" if situation == "already_bought" else "do_not_buy"
    return {"verdict": verdict, "trust_score": int(s), "confidence": confidence, "recommendation": rec}


def next_step(product: dict, evidence: list, ctx: dict, verdict: str):
    if verdict == "likely_fake":
        return "Don't use it. Tap Report so other buyers are warned."
    if ctx.get("expired"):
        return "This product is expired. Don't use it, whether it's genuine or not."
    ids = product.get("identifiers") or {}
    cat = (product.get("category") or "other").lower()
    unreadable = set(product.get("unreadable") or [])
    from checks import NAFDAC_CATEGORIES, SON_CATEGORIES
    if cat == "phone":
        if not ids.get("imei") and not ids.get("imei_device"):
            return "Dial *#06# on the phone and type the IMEI, or photograph the IMEI on the box"
        if not ids.get("imei_device"):
            return "Dial *#06# on the phone and type the IMEI it shows, so we can match it with the box"
        if not ids.get("imei"):
            return "Photograph the IMEI sticker on the box, so we can match it with the phone"
        if any(e["check"] == "ncc_device_check" and e["result"] == "pass" for e in evidence):
            return None
        return "Open the NCC Device Checker link to confirm the IMEI is verified"
    if cat in SON_CATEGORIES:
        if not ids.get("son_marks"):
            return "Photograph the label or sticker where the SON mark (MANCAP, NIS or PAM) should be"
        if not ids.get("serial"):
            return "Photograph the rating label with the model and serial number"
        return None
    if cat == "fashion":
        return "Take a close photo of the logo and the inside tag"
    if cat in NAFDAC_CATEGORIES and not ids.get("nafdac_no"):
        return "Take a close photo of the NAFDAC number on the pack"
    if "confirm_on_napams" in ctx.get("flags", []):
        return "Confirm this NAFDAC number on NAPAMS, then share a screenshot of the result"
    if not ids.get("batch") or "batch" in unreadable:
        return "Take a close photo of the batch number and expiry date"
    if not ids.get("barcode") or "barcode" in ctx.get("retake", []):
        return "Take a close, sharp photo of the barcode (or type the digits under it)"
    return None
