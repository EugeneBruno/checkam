
import asyncio
import json
import time
from pathlib import Path

import pandas as pd
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

URL = "https://greenbook.nafdac.gov.ng/"
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)


async def main():
    records = []
    seen = set()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        print(f"Opening {URL}")
        await page.goto(URL, wait_until="domcontentloaded", timeout=60000)

        # Wait for the JavaScript-powered product table.
        await page.locator("table tbody tr").first.wait_for(timeout=60000)

        # Locate the table containing the product records.
        table = page.locator("table").filter(
            has=page.locator("tbody tr")
        ).first

        headers = await table.locator("thead tr").last.locator(
            "th"
        ).all_inner_texts()

        headers = [h.strip() for h in headers]

        if not headers:
            raise RuntimeError(
                "Could not find table headers. Inspect the current website HTML."
            )

        print("Columns:", headers)

        page_number = 1

        while True:
            rows = await table.locator("tbody tr").all()

            page_records = []

            for row in rows:
                cells = await row.locator("td").all_inner_texts()
                cells = [cell.strip() for cell in cells]

                # Ignore DataTables' empty-results placeholder.
                if not cells or (
                    len(cells) == 1
                    and (
                        "no matching records" in cells[0].lower()
                        or "no data available" in cells[0].lower()
                    )
                ):
                    continue

                # Align the available cell values with the headers.
                record = {
                    headers[i]: cells[i] if i < len(cells) else None
                    for i in range(len(headers))
                }

                key = json.dumps(
                    record, sort_keys=True, ensure_ascii=False
                )

                if key not in seen:
                    seen.add(key)
                    page_records.append(record)

            records.extend(page_records)

            print(
                f"Page {page_number}: "
                f"{len(page_records)} new records; "
                f"{len(records)} unique records collected"
            )

            # DataTables can use either an anchor or a button for Next.
            next_button = page.locator(
                "a.paginate_button.next, "
                "button.dt-paging-button.next, "
                "a[aria-label='Next'], "
                "button[aria-label='Next']"
            ).first

            if await next_button.count() == 0:
                print("No standard Next button found; stopping.")
                break

            classes = (
                await next_button.get_attribute("class") or ""
            ).lower()
            disabled = await next_button.get_attribute("aria-disabled")

            if (
                "disabled" in classes.split()
                or disabled == "true"
                or await next_button.is_disabled()
            ):
                break

            # Wait for the table to change after navigating.
            old_rows = await table.locator("tbody tr").all_inner_texts()

            await next_button.click()

            try:
                await page.wait_for_function(
                    """oldRows => {
                        const table = document.querySelector('table');
                        if (!table) return false;
                        const rows = [...table.querySelectorAll('tbody tr')]
                            .map(row => row.innerText);
                        return JSON.stringify(rows) !== JSON.stringify(oldRows);
                    }""",
                    arg=old_rows,
                    timeout=15000,
                )
            except PlaywrightTimeoutError:
                print("Table did not change; stopping to avoid a loop.")
                break

            page_number += 1
            await page.wait_for_timeout(1000)

        await browser.close()

    if not records:
        raise RuntimeError(
            "No records were collected. Check the website's table selectors "
            "and browser output."
        )

    # Export JSON.
    json_path = OUTPUT_DIR / "nafdac_products.json"
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    # Export CSV.
    csv_path = OUTPUT_DIR / "nafdac_products.csv"
    pd.DataFrame(records).to_csv(
        csv_path, index=False, encoding="utf-8-sig"
    )

    print("\nScraping completed.")
    print(f"Total unique records: {len(records)}")
    print(f"JSON: {json_path.resolve()}")
    print(f"CSV:  {csv_path.resolve()}")


if __name__ == "__main__":
    asyncio.run(main())
