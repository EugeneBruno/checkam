"""Evidence from online product research.

General web research is informational only: it never raises or lowers the score.
The one exception is NAFDAC's own register: if the research found the pack's NAFDAC number on the
online Greenbook (greenbook.nafdac.gov.ng, and the number really appears on that page), that is
registry evidence, just like our local Greenbook copy.
"""
from normalize import name_similarity, reg_key

NAME = "reference_match"
APPLIES_TO = {"*"}
CRITICAL = False


def _greenbook(product, reference):
    """Pass/fail when the official online Greenbook lists the pack's number; else None."""
    # research_agent only keeps a greenbook listing if the retrieved Greenbook page shows the number
    gb = reference.get("greenbook")
    printed = reg_key((product.get("identifiers") or {}).get("nafdac_no"))
    if not gb or not printed or reg_key(gb.get("reg_no")) != printed:
        return None
    from checks import result
    claimed = " ".join(x for x in [product.get("brand"), product.get("name")] if x)
    listed = gb.get("product_name") or ""
    holder = f" ({gb['holder']})" if gb.get("holder") else ""
    if claimed and listed and name_similarity(claimed, listed) < 0.5 \
            and name_similarity(claimed, f"{listed} {gb.get('holder') or ''}") < 0.5:
        return result(NAME, "fail", f"On NAFDAC's online Greenbook, {gb['reg_no']} is registered to "
                      f"\"{listed}\"{holder}, not \"{claimed}\".", gb.get("url"), weight=40)
    status = f" Status: {gb['status']}." if gb.get("status") else ""
    return result(NAME, "pass", f"NAFDAC number {gb['reg_no']} is on NAFDAC's online Greenbook for "
                  f"\"{listed or claimed}\"{holder}.{status} A registry match does not by itself prove "
                  "this physical item is genuine.", gb.get("url"), weight=30)


def run(product: dict, ctx=None):
    ctx = ctx or {}
    reference = ctx.get("reference")

    if not reference:
        return None

    from checks import result

    official = _greenbook(product, reference)
    if official:
        return official

    sources = reference.get("sources") or []
    verified = bool(reference.get("verified"))
    found = bool(reference.get("found"))

    if not verified or not sources:
        return result(
            NAME,
            "unknown",
            "Online research could not verify this product from cited sources.",
            weight=0,
        )

    if not found:
        return result(
            NAME,
            "unknown",
            "Online sources did not confirm this exact product. "
            "This is not evidence that it is counterfeit.",
            weight=0,
        )

    summary = reference.get("summary") or (
        "Online sources found information about this product."
    )

    return result(
        NAME,
        "unknown",
        f"Online reference found, but it does not prove this physical item is genuine. "
        f"{summary}",
        source=sources[0].get("url"),
        weight=0,
    )
