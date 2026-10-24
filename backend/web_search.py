"""Web search and product lookups for the research agent.

- search(query): Tavily web search (free tier: 1,000 credits/month, no card). Needs TAVILY_API_KEY.
- barcode_lookup(code): Open Food Facts / Open Beauty Facts by barcode (free, no key).
Both return plain dicts and never raise: on any problem they return [] / None.
"""
import os

import httpx

UA = "CheckAm/0.1 (hackathon counterfeit checker; contact via GitHub EugeneBruno/checkam)"
TIMEOUT = 12


def available() -> bool:
    return bool(os.environ.get("TAVILY_API_KEY"))


def search(query: str, max_results: int = 5, include_domains=None):
    """[{title, url, content}] from a Tavily basic search (1 credit). [] if unavailable or on error."""
    key = os.environ.get("TAVILY_API_KEY")
    if not key or not query.strip():
        return []
    body = {"query": query, "search_depth": "basic", "max_results": max_results, "topic": "general"}
    if include_domains:
        body["include_domains"] = include_domains
    try:
        r = httpx.post("https://api.tavily.com/search", json=body, timeout=TIMEOUT,
                       headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        r.raise_for_status()
        out = []
        for item in r.json().get("results", []):
            if item.get("url"):
                out.append({"title": item.get("title") or item["url"], "url": item["url"],
                            "content": (item.get("content") or "")[:1200]})
        return out
    except Exception as exc:
        print(f"[web_search] '{query}' failed: {str(exc)[:120]}")
        return []


def barcode_lookup(code: str):
    """Product name/brand from Open Food Facts, then Open Beauty Facts. None if not found."""
    digits = "".join(ch for ch in str(code or "") if ch.isdigit())
    if len(digits) < 8:
        return None
    fields = "product_name,brands,quantity,countries,categories,image_url"
    for host, label in (("world.openfoodfacts.org", "Open Food Facts"),
                        ("world.openbeautyfacts.org", "Open Beauty Facts")):
        try:
            r = httpx.get(f"https://{host}/api/v2/product/{digits}", params={"fields": fields},
                          headers={"User-Agent": UA}, timeout=TIMEOUT)
            data = r.json()
            p = data.get("product") or {}
            if data.get("status") == 1 and (p.get("product_name") or p.get("brands")):
                return {"source": label, "url": f"https://{host}/product/{digits}",
                        "name": p.get("product_name"), "brand": (p.get("brands") or "").split(",")[0].strip() or None,
                        "quantity": p.get("quantity"), "countries": p.get("countries"),
                        "categories": p.get("categories"), "image_url": p.get("image_url")}
        except Exception as exc:
            print(f"[web_search] {label} lookup failed: {str(exc)[:120]}")
    return None
