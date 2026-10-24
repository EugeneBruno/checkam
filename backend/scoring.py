
"""Evidence -> trust score, verdict, confidence and recommendation.

A strong active Greenbook name match can support a likely-genuine verdict
when the registration number is unreadable. This is a provisional assessment,
not proof that the physical package is authentic.
"""

RECOMMENDATION = {
    "before_buying": {
        "likely_genuine": "buy",
        "suspicious": "caution",
        "likely_fake": "do_not_buy",
        "insufficient_evidence": "caution",
    },
    "already_bought": {
        "likely_genuine": "safe_to_use",
        "suspicious": "caution",
        "likely_fake": "do_not_use",
        "insufficient_evidence": "caution",
    },
}

STRONG_PASSES = {
    "registry_fit",
    "clone_detection",
    "imei_check",
    "ncc_device_check",
    "son_certification",
}

# Cap the influence of weak checks, even if an older check returns a larger
# weight. Strong checks retain their explicitly assigned weights.
WEAK_CHECK_CAPS = {
    "packaging_quality": 2,
    "barcode_check_digit": 1,
    "nafdac_alerts": 0,
}

def score(evidence: list, ctx: dict) -> dict:
    critical = set(ctx.get("critical_fails", []))

    decided = [
        item for item in evidence
        if item.get("result") in ("pass", "fail")
    ]
    passes = [item for item in decided if item["result"] == "pass"]
    fails = [item for item in decided if item["result"] == "fail"]

    candidate = ctx.get("registry_candidate") or {}

    active_name_candidate = (
        str(candidate.get("status") or "").strip().lower() == "active"
        and candidate.get("match_status") == "candidate_only"
        and bool(candidate.get("product_name"))
        and "greenbook" in str(candidate.get("source") or "").lower()
    )

    def effective_weight(item: dict) -> float:
        weight = max(0, item.get("weight", 0))
        check = item.get("check")
        if check in WEAK_CHECK_CAPS:
            return min(weight, WEAK_CHECK_CAPS[check])
        return weight

    # Start at 50 and use evidence-specific weights.
    score_value = 50
    score_value += sum(effective_weight(item) for item in passes)
    score_value -= sum(effective_weight(item) for item in fails)

    # A strong active Greenbook name match is positive evidence, but the
    # printed registration number has not been confirmed.
    if active_name_candidate:
        score_value += 30

    # A confirmed registry pass receives its configured evidence weight.
    # Avoid adding another candidate bonus on top of that pass.
    confirmed_registry_match = any(
        item.get("check") == "registry_fit"
        and item.get("result") == "pass"
        for item in passes
    )
    if confirmed_registry_match and active_name_candidate:
        score_value -= 30

    score_value = max(0, min(100, round(score_value)))

    strong_passes = [
        item for item in passes
        if item.get("check") in STRONG_PASSES
    ]

    # Critical failures and conflicting evidence take priority.
    if critical:
        verdict = "likely_fake"
        score_value = min(score_value, 15)
    elif len(fails) >= 2 and score_value < 40:
        verdict = "likely_fake"
    elif fails:
        verdict = "suspicious"
    elif strong_passes and score_value >= 70:
        verdict = "likely_genuine"
    elif active_name_candidate and score_value >= 70:
        verdict = "likely_genuine"
    elif score_value < 50:
        verdict = "insufficient_evidence"
    else:
        verdict = "insufficient_evidence"

    # Name-only candidates receive medium confidence, never high.
    if critical:
        confidence = "high"
    elif active_name_candidate and not confirmed_registry_match:
        confidence = "medium" if verdict == "likely_genuine" else "low"
    elif strong_passes and score_value >= 70:
        confidence = "high"
    elif len(fails) >= 2:
        confidence = "medium"
    else:
        confidence = "low"

    situation = ctx.get("situation", "before_buying")
    recommendation = RECOMMENDATION.get(
        situation, RECOMMENDATION["before_buying"]
    )[verdict]

    if ctx.get("expired"):
        recommendation = (
            "do_not_use"
            if situation == "already_bought"
            else "do_not_buy"
        )

    return {
        "verdict": verdict,
        "trust_score": int(score_value),
        "confidence": confidence,
        "recommendation": recommendation,
    }


def next_step(product: dict, evidence: list, ctx: dict, verdict: str):
    if verdict == "likely_fake":
        return "Don't use it. Tap Report so other buyers are warned."

    if ctx.get("expired"):
        return "This product is expired. Don't use it, whether it's genuine or not."

    ids = product.get("identifiers") or {}
    category = (product.get("category") or "other").lower()
    unreadable = set(product.get("unreadable") or [])

    from checks import NAFDAC_CATEGORIES, SON_CATEGORIES

    if category == "phone":
        if not ids.get("imei") and not ids.get("imei_device"):
            return (
                "Dial *#06# on the phone and type the IMEI, "
                "or photograph the IMEI on the box"
            )
        if not ids.get("imei_device"):
            return (
                "Dial *#06# on the phone and type the IMEI it shows, "
                "so we can match it with the box"
            )
        if not ids.get("imei"):
            return (
                "Photograph the IMEI sticker on the box, "
                "so we can match it with the phone"
            )
        if any(
            item.get("check") == "ncc_device_check"
            and item.get("result") == "pass"
            for item in evidence
        ):
            return None
        return "Open the NCC Device Checker link to confirm the IMEI is verified"

    if category in SON_CATEGORIES:
        if not ids.get("son_marks"):
            return (
                "Photograph the label or sticker where the SON mark "
                "(MANCAP, NIS or PAM) should be"
            )
        if not ids.get("serial"):
            return "Photograph the rating label with the model and serial number"
        return None

    if category == "fashion":
        return "Take a close photo of the logo and the inside tag"

    if category in NAFDAC_CATEGORIES and not (product.get("brand") or product.get("name")) \
            and not ids.get("nafdac_no") and not ids.get("barcode"):
        return ("This pack shows no brand, NAFDAC number or barcode. If another side has a label, photograph it. "
                "If not, it can't be verified: packaged food and drinks sold in Nigeria must carry a NAFDAC "
                "number, so only buy unlabelled items from a seller you know.")

    if category in NAFDAC_CATEGORIES and not ids.get("nafdac_no"):
        candidate = ctx.get("registry_candidate") or {}
        if (
            candidate.get("match_status") == "candidate_only"
            and str(candidate.get("status") or "").lower() == "active"
        ):
            return (
                "An active Greenbook record matches this product. "
                "Take a close photo of the NAFDAC number to strengthen verification."
            )
        return "Take a close photo of the NAFDAC number on the pack"

    if "confirm_on_napams" in ctx.get("flags", []):
        return (f"We read the NAFDAC number as {ids.get('nafdac_no')}. Check it matches the pack exactly "
                "(type the right one if not), then confirm it on NAPAMS and share a screenshot of the result")

    if not ids.get("batch") or "batch" in unreadable:
        return "Take a close photo of the batch number and expiry date"

    if not ids.get("barcode") or "barcode" in ctx.get("retake", []):
        return "Take a close, sharp photo of the barcode (or type the digits under it)"

    return None
