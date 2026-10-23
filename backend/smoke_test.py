"""Smoke test: runs known cases through the real API and prints PASS/FAIL.

    cd backend
    python smoke_test.py

Uses a separate temporary database, so it never touches checkam.db.
Needs no API key (typed details only). Run it after every change.
"""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
sys.path.insert(0, HERE)
os.environ["CHECKAM_DB"] = os.path.join(tempfile.mkdtemp(), "smoke.db")
os.environ.pop("CHECKAM_NCC_LOOKUP", None)

from fastapi.testclient import TestClient  # noqa: E402

import load_data  # noqa: E402
from db import connect  # noqa: E402

conn = connect()
DATA = os.path.join(HERE, "..", "data")
load_data.load_greenbook(os.path.join(DATA, "greenbook_sample.json"), conn)
load_data.load_fakes(os.path.join(DATA, "known_fakes.json"), conn)
load_data.load_son(os.path.join(DATA, "son_certified.json"), conn)
load_data.seed_demo(conn)
from checks import ncc  # noqa: E402
ncc.save_user_result(conn, "490154203237518", 1, 1, "Nokia", "3110", "Nokia 3110 Classic")

from main import app  # noqa: E402

client = TestClient(app)

# (name, fields, expected verdict, text that must appear in the evidence)
CASES = [
    ("Genuine NAFDAC item", {"category": "medical_device", "brand": "Accu-Chek", "name": "Softclix Lancet",
                             "nafdac_no": "03-6090", "batch": "DEMO-SC2207", "expiry": "06/2027",
                             "barcode": "4015630982325"}, "likely_genuine", "matches"),
    ("Registry mismatch", {"category": "cosmetic", "brand": "Glow", "name": "Shea Butter Cream",
                           "nafdac_no": "A3-100882"}, "likely_fake", "belongs to a different product"),
    ("Clone (batch, other expiry)", {"category": "medical_device", "brand": "Always", "name": "Always 3-in-1 Maxi Thick",
                                     "nafdac_no": "03-2099", "batch": "DEMO-AL5531", "expiry": "2028-09"},
     "likely_fake", "different expiry"),
    ("NAFDAC alert (Betaclox)", {"category": "drug", "brand": "Betaclox", "name": "Betaclox Ampicillin Cloxacillin",
                                 "nafdac_no": "A4-4724", "batch": "230701", "expiry": "07/2026"},
     "likely_fake", "NAFDAC alert"),
    ("Number not in our data", {"category": "drug", "brand": "Paramax", "name": "Paramax 500mg",
                                "nafdac_no": "A4-9999", "batch": "SMOKE-1", "expiry": "2027-05"},
     "insufficient_evidence", "not in our records"),
    ("Phone: NCC verified, box = phone", {"category": "phone", "brand": "Nokia", "name": "3110 Classic",
                                         "imei": "490154203237518", "imei_device": "490154203237518"},
     "likely_genuine", "Verified by NCC"),
    ("Phone: box != phone IMEI", {"category": "phone", "brand": "Nokia", "name": "3110 Classic",
                                  "imei": "490154203237518", "imei_device": "356938035643809"},
     "likely_fake", "doesn't match"),
    ("Phone: IMEI belongs to another model", {"category": "phone", "brand": "Apple", "name": "iPhone 13",
                                              "imei": "490154203237518", "imei_device": "490154203237518"},
     "likely_fake", "belongs to Nokia"),
    ("Phone: invalid IMEI", {"category": "phone", "brand": "Tecno", "name": "Spark 10",
                             "imei": "123456789012345"}, "suspicious", "not a valid IMEI"),
    ("SON listed (Haier fridge)", {"category": "electronics", "brand": "Haier Thermocool",
                                   "name": "Refrigerator HRF-385IBG", "son_marks": ["MANCAP"],
                                   "barcode": "4015630982325"}, "likely_genuine", "certified products list"),
    ("SON: no mark, not listed", {"category": "electrical", "brand": "Generic", "name": "Extension box"},
     None, "No SON mark"),
    ("Fashion not on SON list (Nike)", {"category": "fashion", "brand": "Nike", "name": "Air Force 1"},
     "insufficient_evidence", None),
]


def run():
    failures = 0
    for name, fields, want_verdict, want_text in CASES:
        r = client.post("/verify", data={"fields": json.dumps(fields), "state": "Lagos"})
        if r.status_code != 200:
            print(f"FAIL  {name}: HTTP {r.status_code} {r.text[:200]}")
            failures += 1
            continue
        j = r.json()
        details = " | ".join(e["detail"] for e in j["evidence"])
        ok = (want_verdict is None or j["verdict"] == want_verdict) and (not want_text or want_text in details)
        failures += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {name}: {j['verdict']} ({j['trust_score']})")
        if not ok:
            print(f"      expected {want_verdict!r} with {want_text!r}\n      got: {details}")

    # Report flow: report a batch, then the next scan of it must show the report
    fields = {"category": "drug", "brand": "Smokeco", "name": "Smoke Tabs", "batch": "SMOKE-REP", "expiry": "2027-01"}
    first = client.post("/verify", data={"fields": json.dumps(fields), "state": "Lagos"}).json()
    client.post("/report", json={"scan_id": first["scan_id"], "state": "Lagos", "market": "Idumota"})
    again = client.post("/verify", data={"fields": json.dumps(fields), "state": "Oyo"}).json()
    ok = again.get("prior_reports") == 1
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  Report flow: prior_reports={again.get('prior_reports')}")

    total = len(CASES) + 1
    print(f"\n{total - failures}/{total} passed")
    return failures


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
