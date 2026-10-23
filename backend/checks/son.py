"""SON checks: certified-products list lookup + SON marks on the pack.

Data: SON NPCD '2024-2029 List of Certified Products' (MANCAP, locally made goods),
all sectors, loaded into son_certified (see scrapers/son_lists.py).

Imported goods are certified under SONCAP and are NOT on this list, so
"not on the list" is never treated as fake on its own.
"""
import re

from normalize import name_similarity

NAME = "son_certification"
# SON-regulated categories get the full check; fashion/other only get a pass when listed.
SON_REGULATED = {"electrical", "electronics", "auto_part", "building_material"}
APPLIES_TO = SON_REGULATED | {"fashion", "other"}
CRITICAL = False

SON_FAQ = "https://son.gov.ng/helpie_faq/how-can-one-identify-products-certified-by-son/"
LIST_SOURCE = "SON NPCD 2024-2029 List of Certified Products"
STOP = {"limited", "ltd", "nigeria", "nig", "plc", "the", "and", "company", "industries", "industry",
        "enterprises", "global", "international", "products", "product"}
MATCH = 0.55

# Which SON sector lists can hold a product of each category
SECTORS_FOR = {
    "electrical": {"electrical_electronics", "mechanical"},
    "electronics": {"electrical_electronics", "mechanical"},
    "auto_part": {"mechanical", "chemical"},
    "building_material": {"civil_building_mining", "chemical", "mechanical"},
    "fashion": {"textiles_leather"},
}


def _stem(t):
    return t[:-1] if len(t) > 4 and t.endswith("s") else t


def _tokens(text):
    return [_stem(t) for t in re.findall(r"[a-z0-9]+", (text or "").lower()) if len(t) >= 3 and t not in STOP]


def find_certified(conn, brand, name, category=None):
    """Best SON-certified record for this brand/product, or None."""
    claimed = " ".join(x for x in [brand, name] if x)
    keys = _tokens(brand) or _tokens(name)
    if not keys:
        return None, 0.0
    key = max(keys, key=len)
    rows = conn.execute("SELECT * FROM son_certified WHERE search LIKE ? LIMIT 400", (f"%{key}%",)).fetchall()
    best, best_score = None, 0.0
    want = set(_tokens(claimed))
    word = re.compile(rf"\b{re.escape(key)}s?\b")
    brand_re = re.compile(rf"\b{re.escape(brand.lower())}\b") if brand else None
    sectors = SECTORS_FOR.get((category or "").lower())
    for r in rows:
        if sectors and r["sector"] not in sectors:
            continue
        if not word.search(r["search"]):          # whole-word match only ("nike" must not match "unikem")
            continue
        have = set(_tokens(f"{r['company']} {r['product']}"))
        brand_hit = bool(brand_re and brand_re.search(r["search"]))
        product_close = name_similarity(claimed, r["product"]) >= 0.5
        if not product_close and not (brand_re and brand_re.search(r["company"].lower())):
            continue  # brand-level match only when the brand is the maker's name
        if len(want & have) < (1 if brand_hit else min(2, len(want))):   # real word overlap, not just letters
            continue
        score = max(name_similarity(claimed, r["product"]),
                    name_similarity(claimed, f"{r['company']} {r['product']}"))
        if brand_hit:
            score += 0.15
        if score > best_score:
            best, best_score = r, score
    return (best, best_score) if best_score >= MATCH else (None, best_score)


def run(product, ctx):
    from checks import result
    cat = (product.get("category") or "other").lower()
    marks = [m.upper() for m in ((product.get("identifiers") or {}).get("son_marks") or [])]
    hit, _ = find_certified(ctx["conn"], product.get("brand"), product.get("name"), cat)

    if hit:
        where = f"{hit['company']}, {hit['state']}" if hit["state"] else hit["company"]
        claimed = " ".join(x for x in [product.get("brand"), product.get("name")] if x)
        if name_similarity(claimed, hit["product"]) >= 0.5:
            detail = f"On SON's certified products list: \"{hit['product']}\" by {where}."
        else:  # the maker is listed, but not this exact product name
            detail = (f"The maker, {where}, is on SON's certified products list "
                      f"(e.g. \"{hit['product']}\"). Check the exact model on the label.")
        if marks:
            detail += f" SON mark seen on the pack ({', '.join(marks)})."
            weight = 25
        elif cat in SON_REGULATED:
            detail += " No SON mark seen yet; photograph the label to confirm it carries MANCAP."
            weight = 15
        else:
            weight = 15
        if any("PAM" in m for m in marks):
            detail += " Confirm the authentication mark by SMS to 281 or by scanning its QR."
        return result(NAME, "pass", detail, LIST_SOURCE, weight=weight)

    if cat not in SON_REGULATED:
        return None  # not listed is normal for imports, fashion and most other goods

    if marks:
        detail = (f"SON mark present ({', '.join(marks)}), but this product isn't on SON's 2024-2029 list of "
                  "locally certified products. Imported goods are certified under SONCAP instead, so this alone "
                  "doesn't mean it's fake.")
        if any("PAM" in m for m in marks):
            detail += " Confirm the authentication mark by SMS to 281 or by scanning its QR."
        return result(NAME, "unknown", detail, LIST_SOURCE, weight=0)

    return result(NAME, "fail",
                  "No SON mark (MANCAP, NIS or PAM) seen, and the product isn't on SON's list of locally made "
                  "certified products. Locally made goods like this should carry MANCAP; if it's imported, ask the "
                  "seller for its SONCAP certificate. Photograph the label if the mark is elsewhere.",
                  SON_FAQ, weight=10)
