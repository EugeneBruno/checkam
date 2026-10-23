# Check Am

**A product checker that people and AI assistants use to tell whether anything is genuine, with evidence, and it gets smarter with every scan.**

Built at T.I.C Hackathon 3.0 (PAU 24-Hour Hackathon), 23–24 October 2026, by Team Syntax.

> A faker can copy a number. They can't copy a consistent history.

## What it does

Send a photo, video frames or typed details of any product. Check Am:

1. **Identifies it** with a vision model: category, brand, NAFDAC number, batch, expiry, barcode, IMEI, SON marks, label contents, packaging quality.
2. **Runs the checks that apply** to that category (checker plugins).
3. **Scores the evidence** with fixed rules, so the same product always gets the same verdict.
4. **Saves the scan**, so every scan strengthens clone detection and buyer reports for everyone.

AI assistants use the same engine through MCP (`verify_product`, `report_suspect`) before they buy on someone's behalf.

## Checks

| Check | Catches | Source |
|---|---|---|
| `registry_fit` | NAFDAC number copied from another product | NAFDAC Greenbook snapshot + user-confirmed NAPAMS results |
| `nafdac_alerts` | Batches named in NAFDAC counterfeit alerts | NAFDAC public alerts |
| `clone_detection` | Same batch with a different expiry; one serial in many states | Check Am scan history |
| `prior_reports` | Batches other buyers reported | Check Am buyer reports |
| `barcode_check_digit` | Invented barcodes | GTIN maths |
| `date_sanity` | Expired, impossible or re-labelled dates | Pack dates |
| `son_certification` | Products not on SON's certified list; missing MANCAP / NIS / PAM marks | SON 2024-2029 List of Certified Products (11,646 products, 6 sectors) + marks on the pack |
| `imei_check` | Invalid IMEIs; box IMEI that doesn't match the phone (*#06#) | IMEI format (Luhn) |
| `ncc_device_check` | Phones not verified by NCC; IMEI that belongs to a different model than the one sold | NCC Device Checker (link, user-read results, optional rate-limited lookup) |
| `packaging_quality` | Spelling errors, poor print | Vision |

A number missing from our data is **never** called fake: the app asks the user to confirm it on NAPAMS and share a screenshot, which we read and store.

## Run the backend

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env            # add your API key, then export the variables
python load_data.py greenbook ../data/greenbook_sample.json
python load_data.py fakes ../data/known_fakes.json
python scrapers/son_lists.py      # parse SON's certified product lists (data/son_raw) -> data/son_certified.json
python load_data.py son ../data/son_certified.json
python load_data.py seed-demo   # labelled demo scan history (remove with reset-demo)
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

API docs: http://localhost:8000/docs

### Endpoints

- `POST /verify` (multipart): `files` (photos or video frames, optional), `fields` (JSON string of typed details), `situation` (`before_buying` | `already_bought`), `state`, `market`
- `POST /report` (JSON): `scan_id`, `state`, `market`, `seller`, `note`
- `POST /confirm-napams` (multipart): `screenshot`, `expected_reg_no`
- `POST /ncc-result` (JSON): `imei`, `verified`, `type_approved`, `brand`, `model`, `device_name` (a result the user read off the NCC page)
- `GET /scans/{scan_id}`
- `GET /health`

Example (no photo, typed details only):

```bash
curl -X POST localhost:8000/verify \
  -F 'fields={"category":"cosmetic","brand":"Glow","name":"Shea Butter Cream","nafdac_no":"A3-100882"}' \
  -F state=Lagos
```

Sample responses for the UI: `data/sample_response_genuine.json`, `data/sample_response_registry_mismatch.json`.

### Connect an AI assistant (MCP)

```json
{"mcpServers": {"checkam": {"command": "python", "args": ["/full/path/to/backend/mcp_server.py"]}}}
```

Then ask the assistant: *"Which of these two listings is safe to buy?"*

## Data

- `data/greenbook_sample.json`: sample of NAFDAC Greenbook rows (full scrape loads the same way)
- `data/known_fakes.json`: counterfeit batches from NAFDAC public alerts, with source links
- `data/son_raw/`: SON NPCD "2024-2029 List of Certified Products" by sector (food, chemical, mechanical, civil/building/mining, electrical/electronics, textiles/leather)
- `data/son_certified.json`: the same lists parsed into one record per certified product
- Demo scan history uses batch numbers prefixed `DEMO-` and is flagged `seeded = 1`

## Team

Team Syntax: Austine Okoye, Eugene Bruno, + team (add names)
