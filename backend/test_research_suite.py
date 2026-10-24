"""Test the research agent properly.

    python test_research_suite.py            # offline: logic tests with fake web + fake AI (no keys, no quota)
    python test_research_suite.py --live     # real web search + real Gemini on 7 products (~7 AI calls, ~30 Tavily credits)
    python test_research_suite.py --live --model gemini-3.6-flash   # use the demo model (default: a lite model, saves quota)
    python test_research_suite.py --live --only 2,6                 # run some live cases only

Uses a temporary database, so checkam.db is never touched.
"""
import json
import os
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
sys.path.insert(0, HERE)
os.environ["CHECKAM_DB"] = os.path.join(tempfile.mkdtemp(), "research_test.db")

import research_agent  # noqa: E402
import web_search  # noqa: E402
from db import connect  # noqa: E402
from normalize import reg_key  # noqa: E402
from pipeline import verify_product  # noqa: E402

results = []


def check(name, ok, info=""):
    results.append(ok)
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  ({info})" if info and not ok else ""))


# ---------------------------------------------------------------- offline fakes
class FakeResp:
    def __init__(self, text):
        self.text = text
        self.candidates = []


class FakeModels:
    def __init__(self, answers):
        self.answers = list(answers)   # each: dict (-> JSON), str (raw text) or Exception
        self.calls = []

    def generate_content(self, model, contents, config):
        self.calls.append({"model": model, "contents": contents})
        a = self.answers.pop(0)
        if isinstance(a, Exception):
            raise a
        return FakeResp(a if isinstance(a, str) else json.dumps(a))


class FakeClient:
    def __init__(self, answers):
        self.models = FakeModels(answers)


def fake_env(answers, search_on=True, hits=None, barcode=None, greenbook=None):
    client = FakeClient(answers)
    research_agent._client = lambda: client
    web_search.available = lambda: search_on

    def search(q, max_results=5, include_domains=None):
        if include_domains:  # NAFDAC Greenbook search
            return [dict(h) for h in (greenbook or [])]
        return [{"title": f"{t} ({q[:20]})", "url": f"https://{u}/{abs(hash(q)) % 999}", "content": c}
                for t, u, c in (hits or [])]
    web_search.search = search
    web_search.barcode_lookup = lambda code: barcode
    return client


REF = {"found": True, "official_name": "Peak Evaporated Milk", "manufacturer": "FrieslandCampina WAMCO",
       "category": "food", "nafdac_no": "01-0371", "genuine_features": ["Blue tin", "Peak logo"],
       "counterfeit_tells": ["Blurred print"], "price_range_ngn": "400-600", "alerts": [],
       "summary": "Genuine Peak milk has a clean blue tin."}
HITS = [("Peak milk official", "peakmilk.com.ng", "Peak Evaporated Milk NAFDAC 01-0371"),
        ("Fake reviews on BBB", "bbb.org", "how to spot fake reviews"),
        ("Peak price", "jumia.com.ng", "Peak milk 400 naira")]


def offline():
    print("\nOFFLINE: logic tests (fake web, fake AI)")

    print("\n1. Sourced research keeps only the sources the AI used")
    c = fake_env([{**REF, "used_sources": [1, 3]}], hits=HITS)
    ref = research_agent.research({"brand": "Peak", "name": "Evaporated Milk", "category": "food"})
    check("verified with sources", ref["verified"] is True)
    check("junk source (bbb.org) dropped", not any("bbb.org" in s["url"] for s in ref["sources"]),
          [s["url"] for s in ref["sources"]])
    check("NAFDAC number from a brand site (not NAFDAC) is dropped", ref["nafdac_no"] is None, ref["nafdac_no"])
    check("searched 3-5 queries plus NAFDAC Greenbook",
          sum("Searching the web" in s for s in ref["steps"]) in (3, 4, 5)
          and any("Greenbook" in s for s in ref["steps"]))
    check("only one AI call", len(c.models.calls) == 1)
    check("AI got the sources in its prompt", "peakmilk.com.ng" in c.models.calls[0]["contents"])

    print("\n2. No web search and grounding refused (free tier) -> unverified, no NAFDAC number")
    c = fake_env([Exception("429 RESOURCE_EXHAUSTED"), REF], search_on=False)
    ref = research_agent.research({"brand": "Peak", "name": "Evaporated Milk", "category": "food"})
    check("marked unverified", ref["verified"] is False)
    check("NAFDAC number removed (never trust without a source)", ref["nafdac_no"] is None)
    check("no sources claimed", ref["sources"] == [])

    print("\n3. Busy model -> falls back to the next model")
    c = fake_env([Exception("503 UNAVAILABLE high demand"), {**REF, "used_sources": [1]}], hits=HITS)
    ref = research_agent.research({"brand": "Peak", "name": "Evaporated Milk", "category": "food"})
    models = [x["model"] for x in c.models.calls]
    check("second model answered", len(models) == 2 and models[0] != models[1], models)

    print("\n4. Real errors (bad key) are not hidden by the fallback")
    fake_env([Exception("400 API_KEY_INVALID")], hits=HITS)
    try:
        research_agent.research({"brand": "Peak", "name": "Evaporated Milk", "category": "food"})
        check("bad key raises", False)
    except Exception as exc:
        check("bad key raises", "API_KEY_INVALID" in str(exc))

    print("\n5. Unknown item: barcode identifies it, searches use the real name")
    fake_env([{**REF, "official_name": "Nutella", "manufacturer": "Ferrero", "nafdac_no": None,
               "used_sources": [1, 2]}], hits=HITS,
             barcode={"source": "Open Food Facts", "url": "https://world.openfoodfacts.org/product/3017624010701",
                      "name": "Nutella", "brand": "Ferrero"})
    ref = research_agent.research({"category": "other", "identifiers": {"barcode": "3017624010701"}})
    check("identified as Ferrero Nutella", ref["identified"] == {"brand": "Ferrero", "name": "Nutella"})
    check("searched by name, not barcode", any("Ferrero Nutella" in s for s in ref["steps"]))
    check("barcode database cited first", "openfoodfacts" in ref["sources"][0]["url"])

    print("\n6. AI replies with junk -> research fails, but the scan still works")
    fake_env(["Sorry, I can't help with that."], hits=HITS)
    conn = connect()
    out = verify_product(conn, fields={"brand": "Junkbrand", "name": "Thing", "category": "food"},
                         research=True, save=False)
    check("scan returned a verdict", bool(out.get("verdict")))
    check("research marked unavailable", "Research unavailable" in out["research"]["steps"][0])

    print("\n7. Pipeline: research is saved, the next scan uses it instantly (no AI call)")
    c = fake_env([{**REF, "used_sources": [1]}], hits=HITS)
    fields = {"brand": "Peak", "name": "Evaporated Milk", "category": "food", "nafdac_no": "01-0371"}
    out1 = verify_product(conn, fields=fields, research=True, save=False)
    out2 = verify_product(conn, fields=fields, save=False)  # research=True would ask for fresh research
    check("first scan researched", out1["research"]["cached"] is False)
    check("second scan used saved research", out2["research"]["cached"] is True)
    check("only one AI call for both scans", len(c.models.calls) == 1)
    ev = {e["check"]: e for e in out1["evidence"]}
    check("web research is informational only (no score)", ev.get("reference_match", {}).get("weight") == 0,
          ev.get("reference_match"))

    print("\n8. Web research alone never makes a product 'genuine'")
    out = verify_product(conn, fields={**fields, "nafdac_no": "01-9999"}, save=False)
    check("verdict is not 'genuine'", out["verdict"] != "likely_genuine", out["verdict"])

    print("\n9. Unverified research never decides the verdict")
    fake_env([Exception("429"), {**REF, "nafdac_no": "01-0371"}], search_on=False)
    f2 = {"brand": "Milo", "name": "Chocolate drink", "category": "drink", "nafdac_no": "01-5555"}
    out = verify_product(conn, fields=f2, research=True, save=False)
    ev = {e["check"]: e for e in out["evidence"]}
    check("reference_match is 'unknown' with weight 0",
          ev.get("reference_match", {}).get("result") == "unknown" and ev["reference_match"]["weight"] == 0)

    print("\n10. 'Not found' or unverified saved research is retried when asked again")
    c = fake_env([{**REF, "used_sources": [1]}], hits=HITS)
    out = verify_product(conn, fields=f2, research=True, save=False)
    check("unverified Milo reference re-researched", out["research"]["cached"] is False and len(c.models.calls) == 1)
    c = fake_env([{"found": False, "summary": "nothing", "used_sources": []},
                  {**REF, "used_sources": [1]}], hits=HITS)
    f3 = {"brand": "Newbrand", "name": "Soap", "category": "cosmetic"}
    verify_product(conn, fields=f3, research=True, save=False)
    out = verify_product(conn, fields=f3, research=True, save=False)
    check("'not found' reference re-researched", out["research"]["cached"] is False and len(c.models.calls) == 2)


def offline_unlabelled():
    print("\n11. Unlabelled pouch (no brand, no barcode): research runs, but never invents a brand")
    c = fake_env([{"found": True, "official_name": "Tasty Crunch Plantain Chips", "manufacturer": "Tasty Foods Ltd",
                   "category": "food", "used_sources": [1]}], hits=HITS)
    import vision
    real = vision.identify
    vision.identify = lambda images: {"category": "food", "looks_like": "plantain chips in a plain foil pouch",
                                      "label_present": False, "identifiers": {},
                                      "packaging": {"print_quality": "poor"}}
    try:
        conn = connect()
        out = verify_product(conn, images=[b"x"], research=True, save=False)
    finally:
        vision.identify = real
    check("research ran on what the photo showed", out["research"] and not out["research"]["cached"]
          and len(c.models.calls) == 1, out["research"])
    check("searched using 'plantain chips'", any("plantain chips" in st for st in out["research"]["steps"]))
    ev = {e["check"]: e for e in out["evidence"]}
    check("no label is 'unknown', not 'poor print'", ev.get("packaging_quality", {}).get("result") == "unknown")
    check("verdict stays insufficient_evidence", out["verdict"] == "insufficient_evidence", out["verdict"])
    check("no product match claimed for an unidentified pouch",
          ev.get("reference_match", {}).get("result") in (None, "unknown"), ev.get("reference_match"))
    check("next step explains the missing label", "no brand, NAFDAC number or barcode" in (out["next_step"] or ""))


def offline_barcode_owner():
    print("\n12. Barcode owner: the barcode must belong to the brand on the pack")
    conn = connect()
    f = {"brand": "Pringles", "name": "Texas BBQ Sauce", "category": "food", "barcode": "5053990161966"}
    fake_env([{**REF, "official_name": "Pringles Texas BBQ", "manufacturer": "Kellanova", "nafdac_no": None,
               "used_sources": [1]}], hits=HITS,
             barcode={"source": "Open Food Facts", "url": "https://world.openfoodfacts.org/product/5053990161966",
                      "name": "Texas BBQ Sauce", "brand": "Pringles"})
    out = verify_product(conn, fields=f, research=True, save=False)
    ev = {e["check"]: e for e in out["evidence"]}
    check("same brand -> pass", ev.get("barcode_owner", {}).get("result") == "pass", ev.get("barcode_owner"))
    fake_env([], hits=HITS, barcode={"source": "Open Food Facts", "url": "https://x", "name": "Hazelnut spread",
                                     "brand": "Nutella"})
    f2 = {**f, "barcode": "3017624010701"}
    out = verify_product(conn, fields=f2, research=True, save=False)
    ev = {e["check"]: e for e in out["evidence"]}
    check("barcode belongs to Nutella -> fail", ev.get("barcode_owner", {}).get("result") == "fail",
          ev.get("barcode_owner"))
    os.environ["CHECKAM_AUTO_RESEARCH"] = "0"
    out = verify_product(conn, fields={**f, "name": "Sour Cream", "barcode": "4006381333931"}, research=False,
                         save=False)
    os.environ.pop("CHECKAM_AUTO_RESEARCH")
    check("offline scan skips the lookup", "barcode_owner" not in {e["check"] for e in out["evidence"]})


GB_PAGE = {"title": "La Casera Apple Drink", "url": "https://greenbook.nafdac.gov.ng/products/details/1111",
           "content": "Product: La Casera Apple Flavoured Drink. NAFDAC Reg No: 01-4278. Applicant: Seven-Up Bottling "
                      "Company. Status: Active"}


def offline_greenbook():
    print("\n13. Not in our data -> checks NAFDAC's online register (Greenbook) automatically")
    conn = connect()
    gb = {"reg_no": "01-4278", "product_name": "La Casera Apple Flavoured Drink", "holder": "Seven-Up Bottling Company",
          "status": "Active", "url": GB_PAGE["url"]}
    c = fake_env([{**REF, "official_name": "La Casera Apple", "nafdac_no": None, "greenbook": gb,
                   "used_sources": [1]}], hits=HITS, greenbook=[GB_PAGE])
    f = {"brand": "La Casera", "name": "Apple Drink", "category": "drink", "nafdac_no": "01-4278"}
    out = verify_product(conn, fields=f, save=False)  # note: research NOT requested
    ev = {e["check"]: e for e in out["evidence"]}
    check("research ran automatically", out["research"] and out["research"].get("automatic") is True)
    check("Greenbook page searched first", any("Greenbook" in st for st in out["research"]["steps"]))
    check("pack number found on Greenbook -> pass", ev.get("reference_match", {}).get("result") == "pass",
          ev.get("reference_match"))
    check("cites the Greenbook page", "greenbook.nafdac.gov.ng" in (ev.get("reference_match", {}).get("source") or ""))

    print("\n14. AI claims a Greenbook listing the page doesn't show -> ignored")
    fake_env([{**REF, "nafdac_no": None, "greenbook": {**gb, "reg_no": "01-9999"}, "used_sources": [1]}],
             hits=HITS, greenbook=[GB_PAGE])
    ref = research_agent.research({"brand": "La Casera", "name": "Pear", "category": "drink"})
    check("made-up listing dropped", ref["greenbook"] is None)

    print("\n15. Pack number is on the Greenbook for a DIFFERENT product -> fail")
    fake_env([{"found": False, "summary": "x", "greenbook": gb, "used_sources": [1]}], hits=HITS, greenbook=[GB_PAGE])
    f2 = {"brand": "Glowskin", "name": "Body Cream", "category": "cosmetic", "nafdac_no": "01-4278"}
    out = verify_product(conn, fields=f2, save=False)
    ev = {e["check"]: e for e in out["evidence"]}
    check("reference_match fails", ev.get("reference_match", {}).get("result") == "fail", ev.get("reference_match"))
    check("not 'likely_genuine'", out["verdict"] != "likely_genuine", out["verdict"])

    print("\n16. Number already in our data -> no automatic web search")
    conn.execute("INSERT INTO registry_products (reg_no, reg_key, product_name) VALUES ('A4-1000','A41000','Known')")
    c = fake_env([], hits=HITS)
    out = verify_product(conn, fields={"brand": "Known", "name": "Drug", "category": "drug", "nafdac_no": "A4-1000"},
                         save=False)
    check("no AI call, no research", len(c.models.calls) == 0 and not out["research"])
    conn.execute("INSERT INTO registry_products (reg_no, reg_key, product_name) "
                 "VALUES ('A4-2000','A4-2000','Emzor Paracetamol Tablets 500mg')")
    out = verify_product(conn, fields={"brand": "Emzor", "name": "Paracetamol Tablets 500mg", "category": "drug"},
                         save=False)
    check("no number, but the name is in our copy -> no research", len(c.models.calls) == 0 and not out["research"])

    print("\n17. Router follows the categories our Greenbook copy covers (checks/registry.py)")
    real = research_agent._snapshot_categories
    research_agent._snapshot_categories = lambda: {"drug", "herbal"}
    try:
        conn.execute("INSERT INTO registry_products (reg_no, reg_key, product_name) VALUES ('01-7000','017000','Peak Milk')")
        c = fake_env([{**REF, "used_sources": [1]}], hits=HITS)
        out = verify_product(conn, fields={"brand": "Hollandia", "name": "Yoghurt", "category": "food"}, save=False)
        check("food (not covered) -> online research", out["route"]["covered_locally"] is False
              and len(c.models.calls) == 1, out["route"])
        c = fake_env([], hits=HITS)
        out = verify_product(conn, fields={"brand": "Peak", "name": "Milk", "category": "food", "nafdac_no": "01-7000"},
                             save=False)
        check("food number already saved locally -> local only", out["route"]["covered_locally"] is True
              and len(c.models.calls) == 0, out["route"])
        out = verify_product(conn, fields={"brand": "Emzor", "name": "Paracetamol Tablets 500mg", "category": "drug"},
                             save=False)
        check("drug in our copy -> local only", out["route"]["path"] == "local", out["route"])
    finally:
        research_agent._snapshot_categories = real


# ---------------------------------------------------------------- live
LIVE = [
    # (label, product, expect_found, expect_identified)
    ("Peak milk (food)", {"brand": "Peak", "name": "Evaporated Milk", "category": "food"}, True, None),
    ("Emzor paracetamol (drug)", {"brand": "Emzor", "name": "Paracetamol 500mg", "category": "drug"}, True, None),
    ("Tecno Spark (phone)", {"brand": "Tecno", "name": "Spark 20", "category": "phone"}, True, None),
    ("Nivea lotion (cosmetic)", {"brand": "Nivea", "name": "Perfect & Radiant Body Lotion",
                                 "category": "cosmetic"}, True, None),
    ("Unknown barcode -> Nutella", {"category": "other", "identifiers": {"barcode": "3017624010701"}}, True,
     "nutella"),
    ("Made-up product (must NOT be found)", {"brand": "Zorblaxx", "name": "Quantum Mint Toothpaste 9000",
                                             "category": "cosmetic"}, False, None),
    ("Emzor + pack number 04-0411 -> on NAFDAC Greenbook", {"brand": "Emzor", "name": "Paracetamol 500mg",
     "category": "drug", "identifiers": {"nafdac_no": "04-0411"}}, True, None),
    ("Barcode nobody knows", {"category": "other", "identifiers": {"barcode": "6151234567892"}}, None, None),
]


def live(only, model):
    if not os.environ.get("GEMINI_API_KEY"):
        sys.exit("Set GEMINI_API_KEY first.")
    os.environ["GEMINI_RESEARCH_MODEL"] = model
    print(f"\nLIVE: real web search ({'ON' if web_search.available() else 'OFF - set TAVILY_API_KEY'}), "
          f"AI model {model}")
    real_search = web_search.search
    seen_text = []

    def recording_search(q, max_results=5, include_domains=None):
        hits = real_search(q, max_results, include_domains)
        seen_text.extend(h["content"] for h in hits)
        return hits
    web_search.search = recording_search

    for i, (label, product, want_found, want_ident) in enumerate(LIVE, 1):
        if only and i not in only:
            continue
        print(f"\n{i}. {label}")
        seen_text.clear()
        t = time.time()
        try:
            ref = research_agent.research(dict(product), progress=lambda m: print("     -", m))
        except Exception as exc:
            check("research ran", False, f"{type(exc).__name__}: {str(exc)[:200]}")
            continue
        took = time.time() - t
        check(f"finished in under 45s ({took:.0f}s)", took < 45)
        check("answer has the expected fields",
              all(k in ref for k in ("found", "summary", "verified", "sources"))
              and isinstance(ref.get("counterfeit_tells") or [], list))
        if web_search.available():
            check("verified by web sources", ref["verified"] and len(ref["sources"]) >= 1, ref.get("sources"))
        check("source links are real URLs", all(s["url"].startswith("http") for s in ref["sources"]))
        if ref.get("nafdac_no"):
            grounded = reg_key(ref["nafdac_no"]) in reg_key(" ".join(seen_text)) or \
                       ref["nafdac_no"] in " ".join(seen_text)
            check(f"NAFDAC number {ref['nafdac_no']} appears in a source (not invented)", grounded)
        if want_found is not None:
            check(f"found = {want_found}", bool(ref.get("found")) == want_found, ref.get("found"))
        if (product.get("identifiers") or {}).get("nafdac_no"):
            check("found on the NAFDAC Greenbook online", bool(ref.get("greenbook")), ref.get("greenbook"))
        if want_found is False:
            check("no NAFDAC number for a made-up product", not ref.get("nafdac_no"))
        if want_ident:
            ident = json.dumps(ref.get("identified")).lower()
            check(f"identified as {want_ident}", want_ident in ident, ref.get("identified"))
        print(f"     summary: {ref.get('summary')}")
        print(f"     sources: {[s['url'] for s in ref['sources']][:4]}")

    print("\nCache: research once, then the same product again through the full scan")
    conn = connect()
    f = {"brand": "Peak", "name": "Evaporated Milk", "category": "food"}
    verify_product(conn, fields=f, research=True, save=False)
    t = time.time()
    out = verify_product(conn, fields=f, research=True, save=False)
    check(f"second scan uses saved research ({time.time() - t:.2f}s)",
          out["research"] and out["research"]["cached"] and time.time() - t < 2)


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--live" in args:
        model = args[args.index("--model") + 1] if "--model" in args else "gemini-3.5-flash-lite"
        only = {int(x) for x in args[args.index("--only") + 1].split(",")} if "--only" in args else set()
        live(only, model)
    else:
        offline()
        offline_unlabelled()
        offline_barcode_owner()
        offline_greenbook()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)
