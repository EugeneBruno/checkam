"""Research agent for Check Am.

Searches for product-specific information, builds a structured reference, and
allows the caller to cache it. Search results alone do not prove authenticity.
"""

import json
import os
import re
import time
from urllib.parse import urlparse

from normalize import REG_KEY_SQL, name_similarity, reg_key

RESEARCH_TIMEOUT_S = int(os.environ.get("CHECKAM_RESEARCH_TIMEOUT", "60"))

PROMPT = """You are the research step of Check Am, a counterfeit checker used in Nigeria.
Research the specific product below.

Product as read from the pack:
{product}

Prefer official brand/manufacturer pages, NAFDAC/SON sources and regulator alerts,
then reputable news and retailers. Never invent registration numbers, prices or facts.
A product listing does not prove that a physical item is genuine.

Reply with ONLY one JSON object with these keys:
{{
  "found": true if sources identify this specific product, else false,
  "official_name": string or null,
  "manufacturer": string or null,
  "category": one of ["drug","cosmetic","food","drink","spirits","water","herbal","medical_device","phone","electronics","electrical","auto_part","building_material","fashion","other"],
  "nafdac_no": registration number only if a source states it for this exact product, else null,
  "genuine_features": short list supported by sources,
  "counterfeit_tells": short list supported by product-specific alerts or guidance,
  "price_range_ngn": "min-max" if a source supports it, else null,
  "alerts": list of relevant NAFDAC/SON alerts, else [],
  "summary": one plain-English sentence for the buyer,
  "greenbook": object only if a supplied Greenbook source itself supports the listing, otherwise null.
}}

For greenbook use:
{{"reg_no": "exact number", "product_name": "registered name", "holder": "holder if shown", "status": "status if shown", "url": "source URL"}}
"""

SOURCES_NOTE = """
Use ONLY facts explicitly supported by the source results below.
Do not invent product details, ingredients, juice percentages, prices,
registration numbers, alerts, or counterfeit indicators.

For every source you use, include its exact source number in
"used_sources". This must be a JSON array of integers, for example:
"used_sources": [1, 3]

Only include sources that directly support a product-specific claim.
A retailer listing can support that a product is sold, but cannot prove
NAFDAC registration or the authenticity of a physical item.

Only provide nafdac_no when an official NAFDAC source supports that
registration number for the exact product.
Only provide greenbook when the supplied Greenbook source supports
the exact registration number and product name.

If a fact is unsupported, use null or an empty array.
If the evidence is insufficient, set found to false unless the product's
existence is supported by a relevant source.

SOURCES:
{sources}
"""

UNVERIFIED_NOTE = """
Web search is unavailable. Answer only from reliable existing knowledge.
Set nafdac_no and price_range_ngn to null. Keep product-specific features,
counterfeit tells and alerts empty unless reliable knowledge supports them.
The result must remain unverified.
"""


def _key(brand, name, variant=None):
    text = " ".join(str(x) for x in (brand, name, variant) if x).lower()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _table(conn):
    conn.execute(
        """CREATE TABLE IF NOT EXISTS product_references (
            ref_key TEXT PRIMARY KEY,
            created_at TEXT DEFAULT (datetime('now')),
            brand TEXT, name TEXT, data_json TEXT, sources_json TEXT
        )"""
    )
    return conn


def lookup(conn, brand, name, variant=None):
    """Return a saved reference for this product, or None."""
    key = _key(brand, name, variant)
    if not key:
        return None
    _table(conn)
    row = conn.execute(
        "SELECT * FROM product_references WHERE ref_key = ?", (key,)
    ).fetchone()
    if not row and variant:
        row = conn.execute(
            "SELECT * FROM product_references WHERE ref_key = ?",
            (_key(brand, name),),
        ).fetchone()
    if not row:
        return None
    ref = json.loads(row["data_json"])
    ref["sources"] = json.loads(row["sources_json"] or "[]")
    ref["cached"] = True
    return ref


def save(conn, brand, name, variant, ref):
    _table(conn)
    data = {k: v for k, v in ref.items() if k not in ("sources", "steps", "cached")}
    conn.execute(
        "INSERT OR REPLACE INTO product_references "
        "(ref_key, brand, name, data_json, sources_json) VALUES (?,?,?,?,?)",
        (
            _key(brand, name, variant),
            brand,
            name,
            json.dumps(data),
            json.dumps(ref.get("sources") or []),
        ),
    )
    conn.commit()


def _parse(text):
    """Parse JSON, including a JSON object wrapped in incidental text."""
    text = text or ""
    try:
        value = json.loads(text)
        if isinstance(value, dict):
            return value
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        raise ValueError("Research step did not return JSON")
    value = json.loads(match.group(0))
    if not isinstance(value, dict):
        raise ValueError("Research step did not return a JSON object")
    return value


def _sources(resp):
    """Extract Gemini grounding queries and cited pages defensively."""
    queries, sources = [], []
    try:
        meta = resp.candidates[0].grounding_metadata
        queries = list(meta.web_search_queries or [])
        for chunk in meta.grounding_chunks or []:
            web = getattr(chunk, "web", None)
            if web and web.uri:
                sources.append({
                    "title": web.title or web.domain or "source",
                    "url": web.uri,
                    "content": "",
                })
    except Exception:
        pass

    seen, unique = set(), []
    for source in sources:
        if source["url"] not in seen:
            seen.add(source["url"])
            unique.append(source)
    return queries, unique[:8]


NAFDAC_CATS = {
    "drug", "cosmetic", "food", "drink", "spirits", "water", "herbal",
    "medical_device",
}


def _label(product):
    """'Monster Energy' + 'Pipeline Punch' + 'Pipeline Punch, 440ml' -> 'Monster Energy Pipeline Punch'."""
    words, seen = [], set()
    for part in (product.get("brand"), product.get("name"), product.get("variant")):
        for w in re.split(r"[\s,;/]+", str(part or "")):
            key = re.sub(r"[^a-z0-9]", "", w.lower())
            if not key or key in seen or re.fullmatch(r"\d+(\.\d+)?(ml|l|cl|g|kg|mg|oz|pcs|pack|x)", key):
                continue  # skip repeats and pack sizes: they make web searches worse
            seen.add(key)
            words.append(w.strip(",;"))
    return " ".join(words)


GREENBOOK_DOMAINS = ["greenbook.nafdac.gov.ng"]


def _check_greenbook(gb, sources, step=None):
    """Accept a Greenbook claim only if a retrieved Greenbook result supports it."""
    if not isinstance(gb, dict) or not gb.get("reg_no") or not gb.get("url"):
        return None

    parsed_host = (urlparse(gb["url"]).hostname or "").lower()
    if not (
        parsed_host == "greenbook.nafdac.gov.ng"
        or parsed_host.endswith(".greenbook.nafdac.gov.ng")
    ):
        return None

    page = next(
        (source for source in sources if source.get("url") == gb["url"]),
        None,
    )
    if not page:
        return None

    squash = lambda value: re.sub(r"[^A-Z0-9]", "", str(value or "").upper())
    if not reg_key(gb["reg_no"]):
        return None
    if squash(gb["reg_no"]) not in squash(page.get("content")):
        # Search snippets without the actual number cannot establish a listing.
        return None

    name_words = {
        word for word in re.findall(r"[a-z0-9]+", str(gb.get("product_name") or "").lower())
        if len(word) > 2
    }
    page_words = set(
        re.findall(
            r"[a-z0-9]+",
            ((page.get("content") or "") + " " + (page.get("title") or "")).lower(),
        )
    )
    if name_words and len(name_words & page_words) < max(1, len(name_words) // 2):
        gb = {**gb, "product_name": None}

    if step:
        step(f"Found on NAFDAC Greenbook: {gb['reg_no']} = {gb.get('product_name') or '?'}")
    return {key: gb.get(key) for key in ("reg_no", "product_name", "holder", "status", "url")}


def _queries(product, brief):
    """Build targeted searches."""
    label = _label(product)
    category = (product.get("category") or "").lower()
    if not label:
        queries = []
        if brief.get("barcode"):
            queries.append(f"{brief['barcode']} product")
        if (brief.get("visible_text") or "").strip():
            queries.append(f"{brief['visible_text'].strip()[:120]} Nigeria")
        if product.get("looks_like") and product.get("label_present") is False:
            queries.append(
                f"unlabelled {product['looks_like'][:60]} sold in Nigeria NAFDAC registration safety"
            )
        return queries[:3]

    queries = [
        f"{label} official product",
        f"counterfeit {label} how to identify fake packaging",
    ]
    if category == "phone":
        queries.append(f"{label} specifications original box contents")

    if category in NAFDAC_CATS:
        regulator = "NAFDAC"
    elif category == "phone":
        regulator = "NCC"
    elif category in ("electrical", "electronics", "auto_part", "building_material"):
        regulator = "SON"
    else:
        regulator = ""

    queries.append(f"fake {label} Nigeria {regulator} alert".strip())
    queries.append(f"{label} price in Nigeria")
    return queries[:5]


def gated(product):
    """Whether this product category uses automatic NAFDAC research."""
    return (product.get("category") or "other").lower() in NAFDAC_CATS


def _snapshot_categories():
    """Return categories covered by the local Greenbook snapshot."""
    try:
        from checks.registry import SNAPSHOT_COVERED_CATEGORIES
        return set(SNAPSHOT_COVERED_CATEGORIES)
    except ImportError:
        return set(NAFDAC_CATS)



def route(conn, product):
    """Check the local Greenbook before deciding whether online research is needed."""
    category = (product.get("category") or "other").strip().lower()
    identifiers = product.get("identifiers") or {}
    number = reg_key(identifiers.get("nafdac_no"))
    country = "NG"

    # 1. Registration-number lookup takes priority.
    if number:
        row = conn.execute(
            """
            SELECT source FROM registry_products
            WHERE country = ? AND """ + REG_KEY_SQL + """ = ?
            ORDER BY CASE WHEN source = 'napams_user_confirmed' THEN 0 ELSE 1 END
            LIMIT 1
            """,
            (country, number),
        ).fetchone()

        if row:
            return True, f"NAFDAC number found locally ({row['source']})"

    # 2. If OCR missed the number, try matching the product name locally
    # before deciding that the category is not covered by the snapshot.
    brand = str(product.get("brand") or "").strip()
    name = str(product.get("name") or product.get("product_name") or "").strip()
    variant = str(product.get("variant") or "").strip()
    claimed = " ".join(part for part in (brand, name, variant) if part)

    if not number and name:
        rows = conn.execute(
            """
            SELECT product_name, source
            FROM registry_products
            WHERE country = ?
              AND source = 'nafdac_greenbook'
              AND product_name IS NOT NULL
              AND LOWER(product_name) LIKE ?
            LIMIT 200
            """,
            (country, f"%{name.casefold()}%"),
        ).fetchall()

        matches = [
            row for row in rows
            if name_similarity(claimed or name, row["product_name"] or "") >= 0.8
        ]

        if len(matches) == 1:
            return True, "product name matched a local Greenbook record"
        if len(matches) > 1:
            return False, "multiple possible local Greenbook matches"

    # 3. Only now apply the existing category-coverage routing.
    if category not in _snapshot_categories():
        return False, f"our Greenbook copy doesn't cover {category}"

    if number:
        return False, "NAFDAC number not in our Greenbook copy"

    if not claimed:
        return False, "insufficient product details for local matching"

    return False, "product not found in our Greenbook copy"




def in_greenbook_copy(conn, product):
    return route(conn, product)[0]


BUSY = (
    "503", "UNAVAILABLE", "overloaded", "429", "RESOURCE_EXHAUSTED",
    "404", "NOT_FOUND", "DEADLINE", "timed out", "Timeout",
)


def _models():
    first = os.environ.get("GEMINI_RESEARCH_MODEL") or "gemini-3.5-flash-lite"
    rest = os.environ.get(
        "GEMINI_FALLBACKS",
        "gemini-3.6-flash,gemini-3.5-flash-lite,gemini-3.1-flash-lite",
    )
    output = []
    for model in [first] + [item.strip() for item in rest.split(",")]:
        if model and model not in output:
            output.append(model)
    return output


def _client():
    from google import genai
    from google.genai import types

    return genai.Client(
        api_key=os.environ.get("GEMINI_API_KEY"),
        http_options=types.HttpOptions(
            timeout=max(10, RESEARCH_TIMEOUT_S) * 1000,
            retry_options=types.HttpRetryOptions(attempts=1),
        ),
    )


def _generate(client, contents, config, step=None, models=None):
    """Ask the first model that answers; try fallbacks on busy/quota/timeout errors."""
    last_error = None
    for model in models or _models():
        try:
            response = client.models.generate_content(
                model=model, contents=contents, config=config
            )
            print(f"[research] {model} answered")
            return response
        except Exception as exc:
            if not any(code in str(exc) for code in BUSY):
                raise
            last_error = exc
            if step:
                step(f"{model} busy, trying the next model")
    if last_error:
        raise last_error
    raise RuntimeError("No Gemini research models configured")


def _valid_source_indices(used, source_count):
    if not isinstance(used, list):
        return set()
    indices = set()
    for item in used:
        if isinstance(item, (int, str)) and str(item).isdigit():
            index = int(item)
            if 1 <= index <= min(source_count, 12):
                indices.add(index)
    return indices


def _source_host(url):
    try:
        return (urlparse(url).hostname or "").lower()
    except (TypeError, ValueError):
        return ""


def _is_official_regulator_source(source):
    host = _source_host(source.get("url", ""))
    return (
        host == "nafdac.gov.ng"
        or host.endswith(".nafdac.gov.ng")
        or host == "son.gov.ng"
        or host.endswith(".son.gov.ng")
    )


def research(product, progress=None):
    """Research a product online and return a reference dict with sources and steps."""
    from google.genai import types

    steps = []

    def step(message):
        steps.append(message)
        if progress:
            progress(message)

    identifiers = product.get("identifiers") or {}
    found_by_barcode = None

    # Use barcode lookup only to help identify an otherwise unidentified product.
    if not (product.get("brand") and product.get("name")) and identifiers.get("barcode"):
        import web_search

        step(f"Looking up barcode {identifiers['barcode']} in open product databases")
        found_by_barcode = web_search.barcode_lookup(identifiers["barcode"])
        if found_by_barcode:
            product = {
                **product,
                "brand": product.get("brand") or found_by_barcode.get("brand"),
                "name": product.get("name") or found_by_barcode.get("name"),
            }
            step(
                f"Barcode lookup suggests {found_by_barcode.get('brand') or ''} "
                f"{found_by_barcode.get('name') or ''} ({found_by_barcode['source']})".strip()
            )
        else:
            step("Barcode not found in open product databases")

    brief = {
        key: product.get(key)
        for key in ("category", "brand", "name", "variant", "strength")
    }
    brief["nafdac_no_on_pack"] = identifiers.get("nafdac_no")
    brief["barcode"] = identifiers.get("barcode")

    if not (product.get("brand") or product.get("name")):
        brief["visible_text"] = (
            (product.get("looks_like") or "") + " "
            + ((product.get("contents") or {}).get("summary") or "") + " "
            + ((product.get("packaging") or {}).get("logo_notes") or "")
        ).strip()
        brief["note"] = (
            "Set found=true only when the barcode or visible text identifies one specific "
            "branded product. Generic category matches are found=false."
        )

    label = " ".join(
        value for value in (product.get("brand"), product.get("name")) if value
    ) or "this product"

    client = _client()
    started = time.time()
    contents = PROMPT.format(product=json.dumps(brief, ensure_ascii=False))
    sources, queries, response, grounded = [], [], None, False
    tavily_mode = False

    import web_search

    # 1. Tavily search, then Gemini reads only retrieved results.
    if web_search.available():
        tavily_mode = True
        queries = _queries(product, brief)
        seen = set()

        if (
            (product.get("category") or "").lower() in NAFDAC_CATS
            and (label != "this product" or identifiers.get("nafdac_no"))
        ):
            greenbook_query = " ".join(
                value for value in (
                    identifiers.get("nafdac_no"),
                    label if label != "this product" else None,
                ) if value
            )
            step(f"Checking NAFDAC Greenbook: {greenbook_query}")
            for hit in web_search.search(
                greenbook_query, max_results=4, include_domains=GREENBOOK_DOMAINS
            ):
                if hit.get("url") and hit["url"] not in seen:
                    seen.add(hit["url"])
                    sources.append({
                        **hit,
                        "title": "NAFDAC Greenbook: " + hit.get("title", "result"),
                    })
            if not sources:
                step("No Greenbook search result was returned")

        for query in queries:
            step(f"Searching the web: {query}")
            for hit in web_search.search(query, max_results=4):
                if hit.get("url") and hit["url"] not in seen:
                    seen.add(hit["url"])
                    sources.append(hit)

        if found_by_barcode:
            sources.insert(0, {
                "title": f"{found_by_barcode['source']}: barcode lookup",
                "url": found_by_barcode.get("url", ""),
                "content": json.dumps({
                    key: value for key, value in found_by_barcode.items()
                    if key not in ("url", "image_url")
                }),
            })

        if sources:
            selected_sources = sources[:12]
            step(f"Reading {len(selected_sources)} source results")
            block = "\n\n".join(
                f"[{index}] {source.get('title', 'source')} ({source.get('url', '')})\n"
                f"{source.get('content', '')}"
                for index, source in enumerate(selected_sources, 1)
            )
            response = _generate(
                client,
                contents + SOURCES_NOTE.format(sources=block),
                types.GenerateContentConfig(response_mime_type="application/json"),
                step,
            )
            grounded = True  # the AI read only these retrieved pages; used_sources is checked below
        else:
            step("Web search returned no results")

    # 2. Gemini built-in Google Search grounding when Tavily is unavailable.
    if response is None and not web_search.available():
        step(f"Searching the web for {label}")
        try:
            response = _generate(
                client,
                contents,
                types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())]
                ),
                step,
                models=_models()[:1],
            )
            queries, sources = _sources(response)
            for query in queries[:4]:
                step(f"Searched: {query}")
            grounded = bool(sources)
        except Exception as exc:
            if not any(
                code in str(exc)
                for code in ("429", "RESOURCE_EXHAUSTED", "403", "PERMISSION_DENIED")
            ):
                raise
            response = None

    # 3. Model knowledge only: always unverified.
    if response is None:
        step("Web search unavailable; using model knowledge (unverified)")
        response = _generate(
            client,
            contents + UNVERIFIED_NOTE,
            types.GenerateContentConfig(response_mime_type="application/json"),
            step,
        )
        sources, grounded = [], False
        tavily_mode = False

    ref = _parse(response.text)
    ref.setdefault("found", False)
    ref.setdefault("nafdac_no", None)

    # Only accept a Greenbook claim if a retrieved Greenbook result supports it.
    ref["greenbook"] = _check_greenbook(ref.get("greenbook"), sources, step)
    if ref["greenbook"] and not ref.get("nafdac_no") and ref.get("found"):
        ref["nafdac_no"] = ref["greenbook"]["reg_no"]

    used = ref.pop("used_sources", None)
    selected_indices = _valid_source_indices(used, len(sources))

    if selected_indices:
        sources = [
            source
            for index, source in enumerate(sources[:12], start=1)
            if index in selected_indices
        ]
        step(f"Selected {len(sources)} supporting source(s)")
    elif tavily_mode:
        grounded = False
        step("No valid used_sources selection; research remains unverified")

    if not ref.get("found"):
        sources = [
            source for source in sources
            if ref.get("greenbook")
            and source.get("url") == ref["greenbook"].get("url")
        ]

    ref["verified"] = bool(
        grounded
        and sources
        and ref.get("found")
        and (not tavily_mode or selected_indices)
    )

    has_official_source = any(_is_official_regulator_source(source) for source in sources)
    if ref.get("nafdac_no") and not has_official_source:
        ref["nafdac_no"] = None
        ref["greenbook"] = None

    if not ref["verified"]:
        ref["nafdac_no"] = None

    if found_by_barcode:
        ref["identified_by_barcode"] = {
            key: found_by_barcode.get(key)
            for key in ("brand", "name", "source")
        }

    ref["identified"] = {
        "brand": product.get("brand"),
        "name": product.get("name"),
    }
    ref["sources"] = [
        {"title": source.get("title", "source"), "url": source.get("url", "")}
        for source in sources[:8]
        if source.get("url")
    ]

    step(
        f"Built a reference in {time.time() - started:.0f}s"
        + (" (product found)" if ref.get("found")
           else " (couldn't confirm this exact product)")
    )
    ref["steps"] = steps
    ref["cached"] = False
    return ref
