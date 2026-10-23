"""Checker plugins.

Every check module exposes:
    NAME: str
    APPLIES_TO: set of categories, or {"*"} for all
    CRITICAL: bool        # a fail here means "likely fake" on its own
    run(product: dict, ctx: dict) -> dict | None
        returns {"check", "result": pass|fail|unknown, "detail", "source", "weight"}
        or None when the check has nothing to say (e.g. no barcode on the pack).

Categories used across the app:
    drug, cosmetic, food, drink, spirits, water, herbal, medical_device,
    phone, electronics, electrical, auto_part, building_material,
    fashion, other
"""
from . import barcode, dates, registry, clones, reports, alerts, son, imei, ncc, packaging

ALL_CHECKS = [registry, alerts, clones, reports, barcode, dates, son, imei, ncc, packaging]

NAFDAC_CATEGORIES = {"drug", "cosmetic", "food", "drink", "spirits", "water", "herbal", "medical_device"}
SON_CATEGORIES = {"electrical", "electronics", "auto_part", "building_material"}
NCC_CATEGORIES = {"phone"}


def applicable(category: str):
    cat = (category or "other").lower()
    return [c for c in ALL_CHECKS if "*" in c.APPLIES_TO or cat in c.APPLIES_TO]


def result(name, res, detail, source=None, weight=10):
    return {"check": name, "result": res, "detail": detail, "source": source, "weight": weight}
