"""Informational evidence from online product research.

Online research alone must not increase the authenticity score.
"""
NAME = "reference_match"
APPLIES_TO = {"*"}


def run(product: dict, ctx=None):
    ctx = ctx or {}
    reference = ctx.get("reference")

    if not reference:
        return None

    from checks import result

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
