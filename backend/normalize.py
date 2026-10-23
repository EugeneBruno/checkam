"""Shared normalisation helpers (used by loaders, vision output and checks)."""
import re
from datetime import date
from difflib import SequenceMatcher


def reg_key(raw) -> str:
    """Any printed NAFDAC number -> letters+digits only. 'NAFDAC REG NO: A3 100882' -> 'A3100882'."""
    if not raw:
        return ""
    text = str(raw).upper()
    text = re.sub(r"NAFDAC|REG(ISTRATION)?|NO\.?|NUMBER|NRN|:", " ", text)
    return re.sub(r"[^A-Z0-9]", "", text)


def norm_batch(raw) -> str:
    if not raw:
        return ""
    text = re.sub(r"(?i)\b(batch|lot|b\.?\s*no\.?|no\.?)\b|[:#]", " ", str(raw))
    return re.sub(r"[^A-Z0-9]", "", text.upper())


def digits(raw) -> str:
    return re.sub(r"\D", "", str(raw or ""))


_MONTHS = {m: i for i, m in enumerate(
    ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"], 1)}


def parse_month(raw):
    """Parse common pack date formats to (year, month). Returns None if unknown."""
    if not raw:
        return None
    s = str(raw).strip().upper()
    m = re.search(r"(\d{4})[-/.](\d{1,2})", s)                 # 2027-06
    if m:
        y, mo = int(m.group(1)), int(m.group(2))
    else:
        m = re.search(r"(\d{1,2})[-/.](\d{4})", s)             # 06/2027
        if m:
            mo, y = int(m.group(1)), int(m.group(2))
        else:
            m = re.search(r"([A-Z]{3})[A-Z]*[\s\-/.]*(\d{2,4})", s)  # JUN 2027 / JUN27
            if m and m.group(1) in _MONTHS:
                mo, y = _MONTHS[m.group(1)], int(m.group(2))
                if y < 100:
                    y += 2000
            else:
                m = re.search(r"(\d{1,2})[-/.](\d{1,2})[-/.](\d{2,4})", s)  # 01/06/2027
                if not m:
                    return None
                mo, y = int(m.group(2)), int(m.group(3))
                if y < 100:
                    y += 2000
    if not (1 <= mo <= 12 and 1990 <= y <= 2100):
        return None
    return (y, mo)


def month_str(ym) -> str:
    return f"{ym[0]:04d}-{ym[1]:02d}" if ym else ""


def today_month():
    t = date.today()
    return (t.year, t.month)


def name_similarity(a: str, b: str) -> float:
    """0..1 similarity on word tokens, tolerant of extra words like strength or pack size."""
    if not a or not b:
        return 0.0
    ta = set(re.findall(r"[a-z0-9]+", a.lower()))
    tb = set(re.findall(r"[a-z0-9]+", b.lower()))
    if not ta or not tb:
        return 0.0
    overlap = len(ta & tb) / min(len(ta), len(tb))
    ratio = SequenceMatcher(None, a.lower(), b.lower()).ratio()
    return max(overlap, ratio)
