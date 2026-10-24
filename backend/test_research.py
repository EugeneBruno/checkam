"""Run the research agent directly (no server) and show what it found.

Needs GEMINI_API_KEY. For real web search also set TAVILY_API_KEY (free at tavily.com).
    python test_research.py "La Casera" "Apple Drink" drink
    python test_research.py --barcode 3017624010701          # item the photo couldn't name
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import research_agent  # noqa: E402
import web_search  # noqa: E402

args = sys.argv[1:]
if not args:
    print(__doc__)
    sys.exit(1)
if args[0] == "--barcode":
    product = {"category": "other", "identifiers": {"barcode": args[1]}}
    print(f"Researching unknown item with barcode {args[1]} ...")
else:
    product = {"brand": args[0], "name": args[1] if len(args) > 1 else None,
               "category": args[2] if len(args) > 2 else "other"}
    print(f"Researching {product['brand']} {product.get('name') or ''} ...")
print(f"Web search (Tavily): {'ON' if web_search.available() else 'OFF - set TAVILY_API_KEY'}")
t = time.time()
try:
    ref = research_agent.research(product, progress=lambda m: print("  -", m))
except Exception as exc:
    print(f"FAILED after {time.time() - t:.1f}s: {type(exc).__name__}: {exc}")
    sys.exit(1)
print(f"\nDone in {time.time() - t:.1f}s")
print(json.dumps({k: v for k, v in ref.items() if k != "steps"}, indent=2, ensure_ascii=False)[:3000])
