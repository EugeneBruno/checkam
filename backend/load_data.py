"""Load data into SQLite.

    python load_data.py greenbook ../data/greenbook_sample.json   # Bruno's Greenbook scrape
    python load_data.py fakes ../data/known_fakes.json            # NAFDAC alerts
    python load_data.py son ../data/son_certified.json            # SON certified products (all sectors)
    python load_data.py ncc IMEI yes|no "Brand" "Model" "Device name"   # store an NCC result read by hand
    python load_data.py seed-demo                                 # clearly labelled demo scan history
    python load_data.py reset-demo                                # remove demo scans and reports
"""
import json
import re
import sys

from db import connect
from normalize import norm_batch, reg_key

PLACEHOLDERS = {"", "na", "n/a", "nil", "none", "null", "-", "--"}


def clean(v):
    if v is None:
        return None
    t = re.sub(r"\s+", " ", str(v)).strip()
    return None if t.lower() in PLACEHOLDERS else t


def clean_name(v):
    t = clean(v)
    if not t:
        return None
    t = re.sub(r"\s*\$+\s*$", "", t.replace('"', "")).strip()
    return t or None


def load_greenbook(path, conn):
    items = json.load(open(path, encoding="utf-8"))
    n = skipped = 0
    for it in items:
        cat = clean(it.get("Product Category"))
        device = bool(cat) and "device" in cat.lower()
        ingr = clean(it.get("Active Ingredients"))
        reg = clean(it.get("NRN"))
        if not reg:
            skipped += 1
            continue
        detail_id = clean(it.get("Detail ID") or it.get("id"))
        status = clean(it.get("Status"))
        row = {
            "reg_no": reg, "reg_key": reg_key(reg), "product_name": clean_name(it.get("Product Name")),
            "product_type": ingr if device else None, "active_ingredients": None if device else ingr,
            "category": cat, "dosage_form": clean(it.get("Form")), "route": clean(it.get("ROA")),
            "strength": clean(it.get("Strengths")), "applicant": clean(it.get("Applicant Name")),
            "manufacturer": clean(it.get("Manufacturer")), "pack_size": clean(it.get("Pack Size")),
            "status": status.lower() if status else None, "approval_date": clean(it.get("Approval Date")),
            "expiry_date": clean(it.get("Expiry Date")),
            "detail_url": f"https://greenbook.nafdac.gov.ng/products/details/{detail_id}" if detail_id else None,
        }
        cols = ", ".join(row)
        conn.execute(
            f"INSERT INTO registry_products ({cols}) VALUES ({', '.join(':' + k for k in row)}) "
            f"ON CONFLICT (country, source, reg_key, product_name) DO UPDATE SET "
            + ", ".join(f"{k}=excluded.{k}" for k in row), row)
        n += 1
    conn.commit()
    print(f"Greenbook: loaded {n}, skipped {skipped} without NRN")


def load_fakes(path, conn):
    items = json.load(open(path, encoding="utf-8"))
    for it in items:
        conn.execute("INSERT INTO known_fakes (product_name, reg_key, batch, note, source) VALUES (?,?,?,?,?)",
                     (it["product_name"], reg_key(it.get("nafdac_no")), norm_batch(it.get("batch")),
                      it.get("note"), it.get("source")))
    conn.commit()
    print(f"Known fakes: loaded {len(items)}")


def load_son(path, conn):
    items = json.load(open(path, encoding="utf-8"))
    conn.execute("DELETE FROM son_certified")
    conn.executemany(
        "INSERT INTO son_certified (sector, company, address, product, state, search) VALUES (?,?,?,?,?,?)",
        [(i["sector"], i["company"], i["address"], i["product"], i["state"],
          f"{i['company']} {i['product']}".lower()) for i in items])
    conn.commit()
    print(f"SON certified products: loaded {len(items)}")


# Demo scan history. Batch numbers are DEMO values (prefixed DEMO-), not real batches.
DEMO_SCANS = [
    # same batch, consistent expiry -> builds a "genuine" history
    ("demo_1", "medical_device", "Accu-Chek", "Accu-Chek Softclix Lancet", "03-6090", "DEMO-SC2207", "2027-06", "Lagos"),
    ("demo_2", "medical_device", "Accu-Chek", "Accu-Chek Softclix Lancet", "03-6090", "DEMO-SC2207", "2027-06", "Ogun"),
    # batch seen with expiry 2027-03 in Kano: scanning it with any other expiry fires the clone check
    ("demo_3", "medical_device", "Always", "Always 3-In-1 Maxi Thick Sanitary Pads", "03-2099", "DEMO-AL5531", "2027-03", "Kano"),
]


def seed_demo(conn):
    for sid, cat, brand, name, reg, batch, exp, state in DEMO_SCANS:
        conn.execute(
            "INSERT OR REPLACE INTO scans (id, category, brand, product_name, reg_key, batch, expiry, state, verdict, "
            "trust_score, seeded, result_json) VALUES (?,?,?,?,?,?,?,?,'likely_genuine',80,1,'{}')",
            (sid, cat, brand, name, reg_key(reg), norm_batch(batch), exp, state))
    conn.commit()
    print(f"Demo scans seeded: {len(DEMO_SCANS)} (seeded=1)")


def reset_demo(conn):
    conn.execute("DELETE FROM scans WHERE seeded = 1 OR id LIKE 'demo_%'")
    conn.execute("DELETE FROM reports WHERE seeded = 1")
    conn.commit()
    print("Demo data removed")


if __name__ == "__main__":
    c = connect()
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "greenbook":
        load_greenbook(sys.argv[2], c)
    elif cmd == "fakes":
        load_fakes(sys.argv[2], c)
    elif cmd == "son":
        load_son(sys.argv[2], c)
    elif cmd == "ncc":
        from checks import ncc
        a = sys.argv[2:] + [None] * 5
        ncc.save_user_result(c, a[0], 1 if (a[1] or "").lower() == "yes" else 0, None, a[2], a[3], a[4])
        print(f"NCC result stored for {a[0]}")
    elif cmd == "seed-demo":
        seed_demo(c)
    elif cmd == "reset-demo":
        reset_demo(c)
    else:
        print(__doc__)
