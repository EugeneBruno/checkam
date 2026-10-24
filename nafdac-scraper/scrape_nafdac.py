
import asyncio
import json
from pathlib import Path
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

import pandas as pd
from playwright.async_api import async_playwright

URL = "https://greenbook.nafdac.gov.ng/"
OUTPUT_DIR = Path("output2")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

BATCH_SIZE = 1000
DELAY_SECONDS = 1
MAX_RETRIES = 5


def save_records(records):
    """Save all collected records to JSON and CSV."""
    json_path = OUTPUT_DIR / "nafdac_products.json"
    csv_path = OUTPUT_DIR / "nafdac_products.csv"

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    pd.DataFrame(records).to_csv(
        csv_path,
        index=False,
        encoding="utf-8-sig",
    )

    print(f"Saved {len(records)} records.")


def make_batch_url(original_url, start, length, draw):
    """Update DataTables pagination parameters."""
    parsed = urlparse(original_url)
    params = parse_qsl(parsed.query, keep_blank_values=True)

    updated = []
    replaced = set()

    for key, value in params:
        if key == "start":
            updated.append((key, str(start)))
            replaced.add(key)
        elif key == "length":
            updated.append((key, str(length)))
            replaced.add(key)
        elif key == "draw":
            updated.append((key, str(draw)))
            replaced.add(key)
        else:
            updated.append((key, value))

    for key, value in (
        ("start", start),
        ("length", length),
        ("draw", draw),
    ):
        if key not in replaced:
            updated.append((key, str(value)))

    return urlunparse(
        parsed._replace(query=urlencode(updated))
    )


async def fetch_batch(page, batch_url, start):
    """Retry transient request failures with exponential backoff."""
    for attempt in range(MAX_RETRIES):
        try:
            response = await page.request.get(
                batch_url,
                headers={
                    "X-Requested-With": "XMLHttpRequest",
                    "Referer": URL,
                    "Accept": "application/json, text/javascript, */*",
                },
                timeout=90000,
            )

            if response.status in (429, 500, 502, 503, 504):
                raise RuntimeError(
                    f"Temporary server error: HTTP {response.status}"
                )

            if not response.ok:
                raise RuntimeError(
                    f"Request failed: HTTP {response.status}"
                )

            return await response.json()

        except Exception as exc:
            if attempt == MAX_RETRIES - 1:
                raise RuntimeError(
                    f"Batch at offset {start} failed after "
                    f"{MAX_RETRIES} attempts: {exc}"
                ) from exc

            wait_seconds = 2 ** (attempt + 1)

            print(
                f"Request failed at offset {start}: {exc}\n"
                f"Retrying in {wait_seconds}s "
                f"(attempt {attempt + 2}/{MAX_RETRIES})..."
            )

            await asyncio.sleep(wait_seconds)


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        captured = []

        def capture_request(request):
            parsed = urlparse(request.url)
            params = dict(parse_qsl(parsed.query))

            if (
                request.method == "GET"
                and parsed.hostname == "greenbook.nafdac.gov.ng"
                and all(k in params for k in ("draw", "start", "length"))
            ):
                captured.append(request.url)

        page.on("request", capture_request)

        try:
            print("Opening Greenbook to capture its data request...")

            await page.goto(
                URL,
                wait_until="domcontentloaded",
                timeout=60000,
            )

            await page.locator(
                "table tbody tr"
            ).first.wait_for(timeout=60000)

            if not captured:
                raise RuntimeError(
                    "Could not capture the DataTables request. "
                    "The website may have changed its request format."
                )

            original_url = captured[0]
            print("Captured the table request.")

            # Load existing checkpoint, if present.
            json_path = OUTPUT_DIR / "nafdac_products.json"

            if json_path.exists():
                try:
                    with json_path.open("r", encoding="utf-8") as f:
                        all_records = json.load(f)

                    if not isinstance(all_records, list):
                        raise ValueError("Checkpoint must contain a JSON list.")

                    print(
                        f"Loaded checkpoint: {len(all_records)} records."
                    )

                except (json.JSONDecodeError, ValueError) as exc:
                    raise RuntimeError(
                        f"Could not load checkpoint {json_path}: {exc}. "
                        "Preserve the file and inspect it before restarting."
                    ) from exc
            else:
                all_records = []

            # Use the full record as the deduplication key.
            seen = {
                json.dumps(
                    record, sort_keys=True, ensure_ascii=False
                )
                for record in all_records
            }

            # Resume at the next batch boundary.
            start = (len(all_records) // BATCH_SIZE) * BATCH_SIZE
            draw = start // BATCH_SIZE + 1
            expected_total = None

            if start:
                print(f"Resuming at offset {start}.")

            while True:
                batch_url = make_batch_url(
                    original_url,
                    start=start,
                    length=BATCH_SIZE,
                    draw=draw,
                )

                payload = await fetch_batch(page, batch_url, start)

                if not isinstance(payload, dict):
                    raise RuntimeError(
                        "Unexpected response format: expected a JSON object."
                    )

                if payload.get("error"):
                    raise RuntimeError(
                        f"Greenbook returned an error: {payload['error']}"
                    )

                batch = payload.get("data")

                if not isinstance(batch, list):
                    raise RuntimeError(
                        "Response does not contain a valid 'data' array. "
                        f"Keys received: {list(payload.keys())}"
                    )

                total = payload.get(
                    "recordsFiltered",
                    payload.get("recordsTotal"),
                )

                if total is not None:
                    expected_total = int(total)

                if not batch:
                    print(f"No records returned at offset {start}.")
                    break

                new_count = 0

                for record in batch:
                    key = json.dumps(
                        record,
                        sort_keys=True,
                        ensure_ascii=False,
                    )

                    if key not in seen:
                        seen.add(key)
                        all_records.append(record)
                        new_count += 1

                print(
                    f"Offset {start}: received {len(batch)}, "
                    f"{new_count} new; "
                    f"{len(all_records)} unique collected"
                    + (
                        f" / {expected_total} reported"
                        if expected_total is not None
                        else ""
                    )
                )

                # Save after every batch so progress survives failures.
                save_records(all_records)

                start += len(batch)
                draw += 1

                if expected_total is not None and start >= expected_total:
                    break

                if len(batch) < BATCH_SIZE:
                    break

                await asyncio.sleep(DELAY_SECONDS)

            print("\nExport finished.")
            print(f"Unique records collected: {len(all_records)}")
            print(f"Server-reported total: {expected_total}")

            if (
                expected_total is not None
                and len(all_records) != expected_total
            ):
                print(
                    "WARNING: The collected count differs from the "
                    "server-reported total. Check for duplicate or missing "
                    "records before treating the export as complete."
                )

            print(
                f"JSON: {(OUTPUT_DIR / 'nafdac_products.json').resolve()}"
            )
            print(
                f"CSV: {(OUTPUT_DIR / 'nafdac_products.csv').resolve()}"
            )

        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
