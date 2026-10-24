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
  "looks_like": what the item visibly is, in a few words, even with no label (e.g. "plantain chips in a plain foil pouch"),
  "label_present": true if the pack has any printed label or branding, false if it is plain/unlabelled,
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

Rules: if the pack has no printed label, set print_quality to "unknown" (there is no print to judge).
Never guess numbers. If a number is blurry, set it to null and add it to "unreadable".
Copy identifiers exactly as printed, including dashes and letters."""


def _parse_json(text: str) -> dict:
    text = text.strip()
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("Vision model did not return JSON")
    return json.loads(m.group(0))


MAX_SIDE = int(os.environ.get("CHECKAM_MAX_IMAGE_SIDE", "1600"))
TIMEOUT_S = int(os.environ.get("CHECKAM_LLM_TIMEOUT", "60"))          # Anthropic / overall cap
GEMINI_MIN_TIMEOUT_S = 10  # Gemini rejects deadlines under 10s ("Minimum allowed deadline is 10s")
FAST_TIMEOUT_S = max(GEMINI_MIN_TIMEOUT_S, int(os.environ.get("CHECKAM_FAST_TIMEOUT", "10")))  # per model
LAST_TIMEOUT_S = max(GEMINI_MIN_TIMEOUT_S, int(os.environ.get("CHECKAM_LAST_TIMEOUT", "45")))  # final fallback


def shrink(data: bytes) -> bytes:
    """Downscale big phone photos (often 3-8 MB) to max 1600px JPEG: much faster upload, labels stay readable."""
    try:
        from io import BytesIO
        from PIL import Image, ImageOps
        img = ImageOps.exif_transpose(Image.open(BytesIO(data)))
        if max(img.size) <= MAX_SIDE and len(data) < 1_500_000:
            return data
        img.thumbnail((MAX_SIDE, MAX_SIDE))
        out = BytesIO()
        img.convert("RGB").save(out, "JPEG", quality=85)
        return out.getvalue()
    except Exception:
        return data  # Pillow missing or unreadable image: send as-is


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
    client = anthropic.Anthropic(timeout=TIMEOUT_S, max_retries=1)
    content = [{"type": "image", "source": {"type": "base64", "media_type": _mime(b),
                                            "data": base64.b64encode(b).decode()}} for b in images]
    content.append({"type": "text", "text": prompt})
    msg = client.messages.create(
        model=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5-5"),
        max_tokens=1500,
        messages=[{"role": "user", "content": content}],
    )
    return _parse_json("".join(b.text for b in msg.content if getattr(b, "type", "") == "text"))


def _gemini_once(client, types, model, images, prompt, timeout_s):
    parts = [types.Part.from_bytes(data=b, mime_type=_mime(b)) for b in images] + [prompt]
    config = {"response_mime_type": "application/json",
              "http_options": types.HttpOptions(timeout=timeout_s * 1000)}  # milliseconds
    # Reading a label doesn't need much "thinking"; keeping it low makes Flash models much faster.
    if os.environ.get("CHECKAM_THINKING", "off").lower() != "on":
        config["thinking_config"] = types.ThinkingConfig(thinking_level="low")
    try:
        return client.models.generate_content(
            model=model, contents=parts, config=types.GenerateContentConfig(**config))
    except Exception as exc:
        # If this model doesn't accept the thinking setting, retry once with its defaults
        if "thinking_config" in config and "400" in str(exc) and "think" in str(exc).lower():
            config.pop("thinking_config")
            return client.models.generate_content(
                model=model, contents=parts, config=types.GenerateContentConfig(**config))
        raise


def _busy(exc) -> bool:
    text = str(exc)
    return any(code in text for code in ("503", "UNAVAILABLE", "504", "DEADLINE_EXCEEDED", "429",
                                          "RESOURCE_EXHAUSTED", "high demand"))


def _timeout(exc) -> bool:
    name = type(exc).__name__.lower()
    return "timeout" in name or "timed out" in str(exc).lower()


def _gemini(images, prompt=PROMPT):
    """Try GEMINI_MODEL first; if Google says it's busy, fall back to the models in GEMINI_FALLBACKS."""
    import time
    from google import genai
    from google.genai import types
    model = os.environ.get("GEMINI_MODEL") or "gemini-3.6-flash"
    fallbacks = [m.strip() for m in os.environ.get(
        "GEMINI_FALLBACKS", "gemini-3.6-flash,gemini-3.5-flash-lite,gemini-3.1-flash-lite").split(",") if m.strip()]
    models = [model] + [m for m in fallbacks if m != model]
    client = genai.Client(
        api_key=os.environ.get("GEMINI_API_KEY"),
        http_options=types.HttpOptions(retry_options=types.HttpRetryOptions(attempts=1)),  # we retry ourselves
    )
    last = None
    for i, m in enumerate(models):
        timeout_s = LAST_TIMEOUT_S if i == len(models) - 1 else FAST_TIMEOUT_S
        t0 = time.time()
        try:
            resp = _gemini_once(client, types, m, images, prompt, timeout_s)
            note = f" (fallback for {model})" if m != model else ""
            print(f"[vision] {m} answered in {time.time() - t0:.1f}s{note}")
            return _parse_json(resp.text)
        except Exception as exc:
            last = exc
            print(f"[vision] {m} failed after {time.time() - t0:.1f}s: {str(exc)[:100]}")
            if not (_busy(exc) or _timeout(exc) or "404" in str(exc)):
                raise                    # bad key, bad request: don't hide it
    raise last


NAPAMS_PROMPT = """This is a screenshot of a NAFDAC NAPAMS product verification result.
Return ONLY a JSON object: {"found": true/false, "reg_no": string or null, "product_name": string or null,
"category": string or null, "holder": manufacturer or importer name or null,
"approval_date": string or null, "expiry_date": string or null,
"is_napams_page": true if this clearly is a NAFDAC/NAPAMS verification result page, else false}.
Copy values exactly as shown. Never guess."""


def _ask(images, prompt):
    provider = os.environ.get("CHECKAM_LLM", "anthropic").lower()
    images = [shrink(b) for b in images]
    return _gemini(images, prompt) if provider == "gemini" else _anthropic(images, prompt)


def read_napams_screenshot(image: bytes) -> dict:
    return _ask([image], NAPAMS_PROMPT)


def identify(images: list) -> dict:
    """images: list of raw image bytes (photos or extracted video frames, max ~10)."""
    if not images:
        return {}
    return _ask(images[:10], PROMPT)
