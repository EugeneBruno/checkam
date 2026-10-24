"""Parse SON's official '2024-2029 List of Certified Products' (NPCD, MANCAP) into JSON.

Input:  data/son_raw/<sector>.md  (PDF-to-markdown conversions of SON's sector lists)
Output: data/son_certified.json   [{sector, company, address, product, state}, ...]

    python scrapers/son_lists.py

The source tables are messy (different column layouts per sector, rows split across
pages, wrapped text). We read every table row, take the last cell that is a Nigerian
state as STATE, the cell before it as PRODUCTS, and the rest as company + address.
Products separated by ';' become separate records.
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "..", "..", "data", "son_raw")
OUT = os.path.join(HERE, "..", "..", "data", "son_certified.json")

STATES = ["Abia", "Adamawa", "Akwa Ibom", "Anambra", "Bauchi", "Bayelsa", "Benue", "Borno", "Cross River",
          "Delta", "Ebonyi", "Edo", "Ekiti", "Enugu", "FCT", "Abuja", "Gombe", "Imo", "Jigawa", "Kaduna", "Kano",
          "Katsina", "Kebbi", "Kogi", "Kwara", "Lagos", "Nasarawa", "Niger", "Ogun", "Ondo", "Osun", "Oyo",
          "Plateau", "Rivers", "Sokoto", "Taraba", "Yobe", "Zamfara"]
STATE_RE = re.compile(r"^(" + "|".join(re.escape(s) for s in STATES) + r")\b", re.I)
SECTORS = {
    "food.md": "food", "chemical.md": "chemical", "mechanical.md": "mechanical",
    "civil_building_mining.md": "civil_building_mining", "electrical_electronics.md": "electrical_electronics",
    "textiles_leather.md": "textiles_leather",
}


def clean(text: str) -> str:
    t = text.replace("<br>", " ").replace("~~", "").replace("**", "")
    t = re.sub(r"NigerA|Nigera|NIGRIA", "Nigeria", t)  # PDF conversion artefacts
    return re.sub(r"\s+", " ", t).strip(" |")


def norm_state(cell: str):
    c = clean(cell)
    m = STATE_RE.match(c)
    if not m or len(c) > 25:
        return None
    s = m.group(1)
    if s.lower() in ("fct", "abuja"):
        return "FCT Abuja"
    if s.lower().startswith("cross"):
        return "Cross River"
    return s.title() if s.lower() != "akwa ibom" else "Akwa Ibom"


def split_products(text: str):
    parts = [p.strip(" .;,") for p in re.split(r";", clean(text))]
    return [p for p in parts if len(p) > 2]


def parse_file(path: str, sector: str):
    records = []
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line.startswith("|") or set(line) <= set("|-: "):
            continue
        cells = [c for c in line.strip("|").split("|")]
        cells = [c for c in cells if clean(c)]
        if len(cells) < 3:
            continue
        joined = " ".join(cells).upper()
        if "COMPANY NAME" in joined or "STANDARDS ORGANISATION" in joined:
            continue
        # state = last cell that looks like a state
        si = None
        for i in range(len(cells) - 1, 0, -1):
            if norm_state(cells[i]):
                si = i
                break
        if si is None or si < 2:
            continue
        state = norm_state(cells[si])
        products = split_products(cells[si - 1])
        left = [clean(c) for c in cells[:si - 1]]
        if left and re.fullmatch(r"\d+", left[0]):          # separate S/N column
            left = left[1:]
        if not left:
            continue
        company = re.sub(r"^\d+\s+", "", left[0]).strip(" ,.")
        address = " ".join(left[1:]).strip()
        for p in products:
            records.append({"sector": sector, "company": company, "address": address,
                            "product": p, "state": state})
    return records


def main():
    allrecs = []
    for fname, sector in SECTORS.items():
        path = os.path.join(RAW, fname)
        if not os.path.exists(path):
            print(f"missing {fname}")
            continue
        recs = parse_file(path, sector)
        print(f"{sector:24s} {len(recs):5d} products")
        allrecs += recs
    json.dump(allrecs, open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"total {len(allrecs)} -> {os.path.relpath(OUT)}")


if __name__ == "__main__":
    main()
