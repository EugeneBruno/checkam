"""Send real photos to the running Check Am server and print the verdict.

Start the server first (in another terminal), then:
    python test_photo.py path\\to\\photo.jpg [more photos...] [--bought] [--research] [--state Lagos]

Examples:
    python test_photo.py C:\\Users\\me\\Pictures\\phone_box.jpg
    python test_photo.py front.jpg back.jpg --bought
"""
import json
import mimetypes
import os
import sys

import httpx

URL = os.environ.get("CHECKAM_URL", "http://127.0.0.1:8000")


def main(argv):
    paths = [a for a in argv if not a.startswith("--")]
    situation = "already_bought" if "--bought" in argv else "before_buying"
    state = "Lagos"
    if "--state" in argv:
        i = argv.index("--state")
        state = argv[i + 1]
        paths = [p for p in paths if p != state]
    if not paths:
        print(__doc__)
        return 1

    files = []
    for p in paths:
        if not os.path.exists(p):
            print(f"File not found: {p}")
            return 1
        mime = mimetypes.guess_type(p)[0] or "image/jpeg"
        files.append(("files", (os.path.basename(p), open(p, "rb"), mime)))

    print(f"Sending {len(files)} photo(s) to {URL}/verify ...")
    try:
        r = httpx.post(f"{URL}/verify", files=files,
                       data={"situation": situation, "state": state,
                             "research": "true" if "--research" in argv else "false"}, timeout=180)
    except httpx.ConnectError:
        print("Can't reach the server. Is uvicorn running in another terminal?")
        return 1
    except httpx.ReadTimeout:
        print("The server took over 3 minutes. Check the server terminal for errors.")
        return 1
    if r.status_code != 200:
        print(f"Error {r.status_code}: {r.text}")
        return 1

    j = r.json()
    p = j["product"]
    print(f"\nPRODUCT   {p.get('category')} | {p.get('brand')} | {p.get('name')} | {p.get('variant')}")
    if p.get("looks_like"):
        print(f"SEEN      {p['looks_like']}" + ("  (no label)" if p.get("label_present") is False else ""))
    print(f"IDS       {json.dumps({k: v for k, v in (p.get('identifiers') or {}).items() if v})}")
    if j.get("contents", {}).get("summary"):
        print(f"CONTENTS  {j['contents']['summary']}")
    print(f"\nVERDICT   {j['verdict']}  score={j['trust_score']}  confidence={j['confidence']}  "
          f"recommendation={j['recommendation']}")
    for e in j["evidence"]:
        print(f"  [{e['result']:7s}] {e['check']}: {e['detail']}")
    print(f"\nNEXT STEP {j['next_step']}")
    for link in j.get("links", []):
        print(f"LINK      {link['label']}: {link['url']}")
    rt = j.get("route") or {}
    if rt:
        print(f"\nROUTE     {rt.get('path')}  ({rt.get('reason')})")
    res = j.get("research")
    if res:
        print(f"\nRESEARCH  {'saved earlier' if res.get('cached') else 'new'}, "
              f"{'verified by sources' if res.get('verified') else 'no specific product found, general tips only'}")
        for st in res.get("steps") or []:
            print(f"  - {st}")
        if res.get("summary"):
            print(f"  summary: {res['summary']}")
        for src in (res.get("sources") or [])[:4]:
            print(f"  source: {src['url']}")
    if j.get("actions"):
        print(f"ACTIONS   {', '.join(j['actions'])}")
    print(f"\nscan_id   {j['scan_id']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
