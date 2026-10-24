
"""verify_product: identify -> run applicable checks -> score -> save scan."""

import json
import os
import uuid

import research_agent
import vision

from checks import applicable
from normalize import norm_batch, reg_key, parse_month, month_str
from scoring import score, next_step


def _merge(base: dict, typed: dict) -> dict:
    """Typed fields override values read by vision."""
    out = dict(base or {})
    ids = dict(out.get("identifiers") or {})

    for key, value in (typed or {}).items():
        if value in (None, "", []):
            continue

        if key in (
            "nafdac_no", "batch", "expiry", "mfg_date", "barcode",
            "serial", "imei", "imei_device", "style_code", "son_marks",
        ):
            ids[key] = value
        else:
            out[key] = value

    out["identifiers"] = ids
    return out


def verify_product(
    conn,
    images=None,
    fields=None,
    situation="before_buying",
    location=None,
    country="NG",
    save=True,
    progress=None,
    research=False,
    product=None,
):
    """Identify a product, run checks, optionally research it, and save the scan.

    The existing /verify call signature remains compatible.
    Pass research=True to request a fresh research attempt.
    """

    def step(message):
        if progress:
            progress(message)

    # 1. Identify the product (or reuse one from a saved scan).
    product = dict(product or {})

    if images and not product:
        step("Identifying product")
        product = vision.identify(images)

    product = _merge(product, fields)

    if not product.get("category"):
        product["category"] = "other"

    ids = product.get("identifiers") or {}
    named = bool(product.get("brand") or product.get("name"))

    researchable = (
        named
        or bool(ids.get("barcode"))
        or bool((product.get("contents") or {}).get("summary"))
        or bool(product.get("looks_like"))
    )

    ctx = {
        "conn": conn,
        "country": country,
        "situation": situation,
        "location": location or {},
        "from_photo": bool(images),
        "typed": {
            key for key, value in (fields or {}).items() if value
        },
    }

    # 2. Look for previously saved, source-verified research.
    reference = None
    research_info = None

    if named and not research:
        try:
            cached_reference = research_agent.lookup(
                conn,
                product.get("brand"),
                product.get("name"),
                product.get("variant"),
            )

            if (
                cached_reference
                and cached_reference.get("verified")
                and cached_reference.get("found")
                and cached_reference.get("sources")
            ):
                reference = cached_reference
            elif cached_reference:
                step(
                    "Saved reference is unverified or inconclusive; "
                    "a fresh research attempt may be needed"
                )

        except Exception as exc:
            step(
                f"Saved research lookup unavailable: "
                f"{type(exc).__name__}"
            )

    if reference:
        research_info = {
            "cached": True,
            "steps": ["Used saved research for this product"],
            "sources": reference.get("sources") or [],
            "summary": reference.get("summary"),
            "verified": bool(reference.get("verified")),
            "found": bool(reference.get("found")),
        }

    # 3. Determine whether the local Nigerian registry snapshot covers it.
    try:
        if research_agent.gated(product):
            covered, route_reason = research_agent.route(conn, product)
        else:
            covered = None
            route_reason = "not a NAFDAC-regulated category"

    except Exception as exc:
        # Routing failure must not prevent local checks from running.
        covered = None
        route_reason = (
            f"Local routing unavailable ({type(exc).__name__})"
        )

    # 4. Decide whether to trigger automatic research.
    automatic_research = False
    research_attempted = False

    auto_enabled = (
        os.environ.get("CHECKAM_AUTO_RESEARCH", "1").strip().lower()
        in {"1", "true", "yes", "on"}
    )

    if (
        covered is not True
        and reference is None
        and researchable
        and auto_enabled
    ):
        research = True
        automatic_research = True
        step(
            f"Not covered locally ({route_reason}); "
            "attempting online research"
        )

    # 5. Research when explicitly requested or automatically triggered.
    if reference is None and research and researchable:
        research_attempted = True

        try:
            result_reference = research_agent.research(
                product,
                progress=progress,
            )

            # Normalize an unexpected empty result safely.
            reference = (
                result_reference
                if isinstance(result_reference, dict)
                else None
            )

            if reference is None:
                raise ValueError(
                    "Research agent returned no usable result"
                )

            # Only use source-backed verification to fill an unknown category.
            if (
                reference.get("verified")
                and reference.get("found")
                and product.get("category") in (None, "", "other")
                and reference.get("category")
            ):
                product["category"] = reference["category"]

            # Save the research result as a reference or research note.
            # A saved note is not proof of authenticity.
            if product.get("brand") or product.get("name"):
                research_agent.save(
                    conn,
                    product.get("brand"),
                    product.get("name"),
                    product.get("variant"),
                    reference,
                )

            research_info = {
                "cached": False,
                "steps": reference.get("steps") or [],
                "sources": reference.get("sources") or [],
                "summary": reference.get("summary"),
                "verified": bool(reference.get("verified")),
                "found": bool(reference.get("found")),
                "automatic": automatic_research,
                "greenbook": reference.get("greenbook"),
            }

        except Exception as exc:
            # Research is supplementary; preserve the scan if it fails.
            reference = None
            research_info = {
                "cached": False,
                "steps": [
                    f"Research unavailable: {type(exc).__name__}: "
                    f"{str(exc)[:150]}"
                ],
                "sources": [],
                "summary": None,
                "verified": False,
                "found": False,
                "automatic": automatic_research,
            }
            step("Online research failed; continuing with local checks")

    ctx["reference"] = reference
    ctx["online"] = bool(research_attempted or reference)

    # 6. Run all applicable checks.
    evidence = []

    for check in applicable(product["category"]):
        step(f"Running {check.NAME.replace('_', ' ')}")

        try:
            result = check.run(product, ctx)

        except Exception as exc:
            # One failed check must not break the entire scan.
            result = {
                "check": check.NAME,
                "result": "unknown",
                "detail": (
                    f"Check failed: {type(exc).__name__}: "
                    f"{str(exc)[:200]}"
                ),
                "source": None,
                "weight": 0,
            }

        if result:
            evidence.append(result)

    # 7. Score only evidence returned by the checks.
    # Online research alone must never be a strong authenticity pass.
    scored = score(evidence, ctx)

    # "unknown" means a check ran but could not establish a result.
    # Only an explicit "not_checked" result is reported as skipped.
    not_checked = [
        item["check"]
        for item in evidence
        if item.get("result") == "not_checked"
    ]

    if not images:
        not_checked.append("photo_analysis")

    ids = product.get("identifiers") or {}
    scan_id = "scn_" + uuid.uuid4().hex[:10]

    # 8. Build the API response.
    reference_verified = bool(
        reference
        and reference.get("verified")
        and reference.get("found")
        and reference.get("sources")
    )

    actions = []

    if "confirm_on_napams" in ctx.get("flags", []):
        actions.append("confirm_on_napams")

    if scored["verdict"] in ("suspicious", "likely_fake"):
        actions.append("report")

    # Offer another research attempt if the evidence is still inconclusive.
    # This also works after an automatic research attempt failed.
    if (
        covered is not True
        and researchable
        and not reference_verified
        and scored["verdict"] in (
            "insufficient_evidence",
            "suspicious",
        )
    ):
        actions.append("research")

    out = {
        "scan_id": scan_id,
        "situation": situation,
        **scored,
        "product": {
            "category": product.get("category"),
            "category_confidence": product.get("category_confidence"),
            "brand": product.get("brand"),
            "name": product.get("name"),
            "variant": product.get("variant"),
            "strength": product.get("strength"),
            "looks_like": product.get("looks_like"),
            "label_present": product.get("label_present"),
            "identifiers": ids,
        },
        "contents": product.get("contents") or {},
        "evidence": evidence,
        "registry_candidate": ctx.get("registry_candidate"),
        "not_checked": not_checked,
        "next_step": next_step(
            product,
            evidence,
            ctx,
            scored["verdict"],
        ),
        "prior_reports": ctx.get("prior_reports", 0),
        "links": ctx.get("links", []),
        "route": {
            "covered_locally": covered,
            "reason": route_reason,
            "path": (
                "local + online research"
                if research_info and not research_info.get("cached")
                else "local"
            ),
        },
        "research": research_info,
        "actions": actions,
    }

    # 9. Save the scan using the existing database schema.
    if save:
        loc = location or {}

        conn.execute(
            """
            INSERT INTO scans (
                id, country, category, brand, product_name, reg_key,
                batch, expiry, mfg_date, serial, state, market,
                verdict, trust_score, result_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                scan_id,
                country,
                product.get("category"),
                product.get("brand"),
                product.get("name"),
                reg_key(ids.get("nafdac_no")),
                norm_batch(ids.get("batch")),
                month_str(parse_month(ids.get("expiry"))),
                month_str(parse_month(ids.get("mfg_date"))),
                ids.get("serial") or ids.get("imei") or None,
                loc.get("state"),
                loc.get("market"),
                scored["verdict"],
                scored["trust_score"],
                json.dumps(out),
            ),
        )
        conn.commit()

    step("Done")
    return out


def report_suspect(
    conn,
    scan_id=None,
    product=None,
    location=None,
    seller=None,
    note=None,
    reporter="user",
):
    """Save a buyer report, optionally using a previously saved scan."""

    p = dict(product or {})

    if scan_id:
        row = conn.execute(
            "SELECT result_json FROM scans WHERE id = ?",
            (scan_id,),
        ).fetchone()

        if row:
            saved_result = json.loads(row["result_json"])
            saved_product = (
                saved_result.get("_product")
                or saved_result.get("product")
                or {}
            )
            p = {**saved_product, **p}

    ids = p.get("identifiers") or {}
    loc = location or {}

    conn.execute(
        """
        INSERT INTO reports (
            scan_id, brand, product_name, reg_key, batch,
            seller, state, market, note, reporter
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            scan_id,
            p.get("brand"),
            p.get("name") or p.get("product_name"),
            reg_key(ids.get("nafdac_no")),
            norm_batch(ids.get("batch")),
            seller,
            loc.get("state"),
            loc.get("market"),
            note,
            reporter,
        ),
    )
    conn.commit()

    batch = norm_batch(ids.get("batch"))

    total = (
        conn.execute(
            """
            SELECT COUNT(*)
            FROM reports
            WHERE batch = ? AND lower(coalesce(brand, '')) = ?
            """,
            (batch, (p.get("brand") or "").lower()),
        ).fetchone()[0]
        if batch
        else 0
    )

    return {
        "ok": True,
        "batch": batch,
        "total_reports_for_batch": total,
        "message": "Thanks. Anyone who scans this batch will now see your report.",
    }
