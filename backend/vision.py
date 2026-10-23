"""Vision: photos / video frames -> structured product JSON.

Provider is set by env CHECKAM_LLM = "anthropic" (default) or "gemini".
  anthropic: needs ANTHROPIC_API_KEY; model from ANTHROPIC_MODEL (default claude-sonnet-5-5)
  gemini:    needs GEMINI_API_KEY;    model from GEMINI_MODEL (required)
"""
import base64
import json
import os
import re

PROMPT = """You are the product-identification step of a counterfeit checker used in Nigeria.
Look at ALL the images (they show the same product from different angles) and return ONLY a JSON object,
no prose, with exactly these keys:

{
  "category": one of ["drug","cosmetic","food","drink","spirits","water","herbal","medical_device",
                      "phone","electronics","electrical","auto_part","building_material","fashion","other"],
  "category_confidence": "low" | "medium" | "high",
  "brand": string or null,
  "name": product name as printed, or null,
  "variant": model / flavour / size / colourway, or null,
  "strength": e.g. "500mg" for medicines, or null,
  "identifiers": {
    "nafdac_no": registration number exactly as printed (e.g. "A4-1234"), or null,
    "batch": batch / lot number exactly as printed, or null,
    "expiry": expiry date exactly as printed, or null,
    "mfg_date": manufacture date exactly as printed, or null,
    "barcode": digits under the barcode, or null,
    "serial": serial number, or null,
    "imei": IMEI printed on the box or sticker, or null,
    "imei_device": IMEI shown on the phone screen (e.g. a *#06# screenshot), or null,
    "style_code": fashion style/article code, or null,
    "son_marks": list of SON marks seen, any of ["MANCAP","NIS","PAM"], empty list if none,
    "scratch_panel": true if there is a scratch-to-verify panel, else false,
    "qr_present": true/false
  },
  "contents": {
    "summary": one plain-English sentence on what the label says the product contains and is for, or null,
    "active_ingredients": list of strings,
    "net_quantity": string or null
  },
  "packaging": {
    "spelling_errors": list of misspelled words actually printed on the pack (empty if none),
    "print_quality": "good" | "poor" | "unknown",
    "logo_notes": short note on the logo (shape, font, spacing, colour) and anything that looks off, or null,
    "notes": short note on anything suspicious (misaligned labels, smudged batch print, missing seal), or null
  },
  "unreadable": list of fields you could not read clearly (e.g. ["batch","expiry"])
}

Rules: never guess numbers. If a number is blurry, set it to null and add it to "unreadable".
Copy identifiers exactly as printed, including dashes and letters."""


def _parse_json(text: str) -> dict:
    text = text.strip()
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("Vision model did not return JSON")
    return json.loads(m.group(0))


def _mime(data: bytes) -> str:
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return "image/jpeg"


def _anthropic(images, prompt=PROMPT):
    import anthropic
    client = anthropic.Anthropic()
    content = [{"type": "image", "source": {"type": "base64", "media_type": _mime(b),
                                            "data": base64.b64encode(b).decode()}} for b in images]
    content.append({"type": "text", "text": prompt})
    msg = client.messages.create(
        model=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5-5"),
        max_tokens=1500,
        messages=[{"role": "user", "content": content}],
    )
    return _parse_json("".join(b.text for b in msg.content if getattr(b, "type", "") == "text"))


def _gemini(images, prompt=PROMPT):
    from google import genai
    from google.genai import types
    model = os.environ.get("GEMINI_MODEL")
    if not model:
        raise RuntimeError("Set GEMINI_MODEL to the Gemini vision model you're using")
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    parts = [types.Part.from_bytes(data=b, mime_type=_mime(b)) for b in images] + [prompt]
    resp = client.models.generate_content(
        model=model, contents=parts,
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    return _parse_json(resp.text)


NAPAMS_PROMPT = """This is a screenshot of a NAFDAC NAPAMS product verification result.
Return ONLY a JSON object: {"found": true/false, "reg_no": string or null, "product_name": string or null,
"category": string or null, "holder": manufacturer or importer name or null,
"approval_date": string or null, "expiry_date": string or null,
"is_napams_page": true if this clearly is a NAFDAC/NAPAMS verification result page, else false}.
Copy values exactly as shown. Never guess."""


def _ask(images, prompt):
    provider = os.environ.get("CHECKAM_LLM", "anthropic").lower()
    return _gemini(images, prompt) if provider == "gemini" else _anthropic(images, prompt)


def read_napams_screenshot(image: bytes) -> dict:
    return _ask([image], NAPAMS_PROMPT)


def identify(images: list) -> dict:
    """images: list of raw image bytes (photos or extracted video frames, max ~10)."""
    if not images:
        return {}
    return _ask(images[:10], PROMPT)
