"""Check Am API.

Run:  uvicorn main:app --reload --host 0.0.0.0 --port 8000   (from backend/)
Docs: http://localhost:8000/docs
"""

import hashlib
import hmac
import os
from pathlib import Path
from fastapi import Header
from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parent.parent / ".env")


import json
from typing import List, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import vision
from db import connect
from normalize import reg_key
from pipeline import report_suspect, verify_product

app = FastAPI(title="Check Am", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
conn = connect()
@app.post("/__temporary_db_upload")
async def temporary_db_upload(
    file: UploadFile = File(...),
    x_upload_token: str = Header(...),
    x_content_sha256: str = Header(...),
):
    expected_token = os.environ.get("CHECKAM_UPLOAD_TOKEN", "")
    if not expected_token or not hmac.compare_digest(
        x_upload_token, expected_token
    ):
        raise HTTPException(status_code=401, detail="Unauthorized")

    target = Path("/data/checkam_transfer.sqlite3")
    partial = Path("/data/checkam_transfer.sqlite3.part")
    digest = hashlib.sha256()

    try:
        with partial.open("wb") as output:
            while chunk := await file.read(1024 * 1024):
                output.write(chunk)
                digest.update(chunk)
            output.flush()
            os.fsync(output.fileno())

        actual_hash = digest.hexdigest()
        if not hmac.compare_digest(actual_hash.lower(), x_content_sha256.lower()):
            partial.unlink(missing_ok=True)
            raise HTTPException(status_code=400, detail="SHA-256 mismatch")

        os.replace(partial, target)
        return {
            "uploaded": True,
            "bytes": target.stat().st_size,
            "sha256": actual_hash,
        }
    except HTTPException:
        raise
    except Exception as exc:
        partial.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="Upload failed") from exc
    finally:
        await file.close()

@app.get("/health")
def health():
    n = conn.execute("SELECT COUNT(*) FROM registry_products").fetchone()[0]
    return {"ok": True, "registry_rows": n}


@app.post("/verify")
async def verify(
    files: Optional[List[UploadFile]] = File(None, description="Upload product photos for AI identification", media_type="image/*",),
    fields: Optional[str] = Form(None),          # JSON: {"brand": "...", "nafdac_no": "...", "batch": "...", ...}
    situation: str = Form("before_buying"),      # before_buying | already_bought
    state: Optional[str] = Form(None),
    market: Optional[str] = Form(None),
):
    images = [await f.read() for f in (files or [])]
    try:
        typed = json.loads(fields) if fields else {}
    except json.JSONDecodeError:
        raise HTTPException(400, "fields must be JSON")
    if not images and not typed:
        raise HTTPException(400, "Send at least one photo or some typed details")
    try:
        return verify_product(conn, images=images, fields=typed, situation=situation,
                              location={"state": state, "market": market})
    except RuntimeError as exc:
        raise HTTPException(500, str(exc))
    except Exception as exc:  # AI provider errors (bad key, quota, model name) -> readable message
        raise HTTPException(502, f"Vision model error ({type(exc).__name__}): {str(exc)[:400]}")


class ReportIn(BaseModel):
    scan_id: Optional[str] = None
    product: Optional[dict] = None
    state: Optional[str] = None
    market: Optional[str] = None
    seller: Optional[str] = None
    note: Optional[str] = None


@app.post("/report")
def report(body: ReportIn):
    if not body.scan_id and not body.product:
        raise HTTPException(400, "Send scan_id or product")
    return report_suspect(conn, scan_id=body.scan_id, product=body.product,
                          location={"state": body.state, "market": body.market},
                          seller=body.seller, note=body.note, reporter="user")


@app.post("/confirm-napams")
async def confirm_napams(screenshot: UploadFile = File(...), expected_reg_no: Optional[str] = Form(None)):
    """User checked NAPAMS themselves and shares the result screenshot; we read it and store it."""
    data = vision.read_napams_screenshot(await screenshot.read())
    if not data.get("is_napams_page"):
        raise HTTPException(422, "That doesn't look like a NAFDAC NAPAMS result page")
    if not data.get("found") or not data.get("reg_no"):
        return {"ok": True, "found": False, "message": "NAPAMS shows no product for this number"}
    if expected_reg_no and reg_key(expected_reg_no) != reg_key(data["reg_no"]):
        raise HTTPException(422, "The screenshot is for a different NAFDAC number")
    conn.execute(
        "INSERT INTO registry_products (country, source, reg_no, reg_key, product_name, category, applicant, "
        "approval_date, expiry_date, status, confirmed_at) VALUES ('NG','napams_user_confirmed',?,?,?,?,?,?,?,'active',"
        "datetime('now')) ON CONFLICT (country, source, reg_key, product_name) DO UPDATE SET confirmed_at = datetime('now')",
        (data["reg_no"], reg_key(data["reg_no"]), data.get("product_name"), data.get("category"),
         data.get("holder"), data.get("approval_date"), data.get("expiry_date")),
    )
    conn.commit()
    return {"ok": True, "found": True, "record": data,
            "message": "Thanks, this NAFDAC number is now confirmed for everyone who scans it."}


class NccResultIn(BaseModel):
    imei: str
    verified: bool
    type_approved: Optional[bool] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    device_name: Optional[str] = None


@app.post("/ncc-result")
def ncc_result(body: NccResultIn):
    """User read their result off the NCC Device Checker page; store it so the next scan uses it."""
    from checks import ncc
    from normalize import digits
    imei = digits(body.imei)
    if len(imei) != 15:
        raise HTTPException(400, "IMEI must be 15 digits")
    ncc.save_user_result(conn, imei, int(body.verified),
                         None if body.type_approved is None else int(body.type_approved),
                         body.brand, body.model, body.device_name)
    return {"ok": True, "message": "Saved. Rescan to include the NCC result."}


@app.get("/scans/{scan_id}")
def get_scan(scan_id: str):
    row = conn.execute("SELECT result_json FROM scans WHERE id = ?", (scan_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Scan not found")
    return json.loads(row["result_json"])


def custom_openapi():
    from fastapi.openapi.utils import get_openapi

    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=app.version,
        routes=app.routes,
    )

    body_schema = schema["components"]["schemas"].get(
        "Body_verify_verify_post"
    )

    if body_schema:
        body_schema.setdefault("properties", {})["files"] = {
            "title": "Files",
            "description": "Upload product photos for AI identification",
            "type": "array",
            "items": {
                "type": "string",
                "format": "binary",
            },
        }

    app.openapi_schema = schema
    return app.openapi_schema


app.openapi = custom_openapi
