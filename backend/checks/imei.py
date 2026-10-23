"""IMEI checks for phones/tablets/modems.

- Format: 15 digits + Luhn check digit (catches made-up IMEIs printed on fake boxes)
- Box vs phone: IMEI printed on the box (identifiers.imei) must equal the one the phone
  reports when you dial *#06# (identifiers.imei_device). A mismatch means the phone
  isn't the one the box was made for (swapped, refurbished or fake).
"""
from normalize import digits

NAME = "imei_check"
APPLIES_TO = {"phone"}
CRITICAL = False


def luhn_ok(num: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(num)):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def valid_imei(imei: str) -> bool:
    return len(imei) == 15 and luhn_ok(imei)


def run(product, ctx):
    from checks import result
    ids = product.get("identifiers") or {}
    box = digits(ids.get("imei"))
    device = digits(ids.get("imei_device"))
    imei = box or device
    if not imei:
        return result(NAME, "unknown", "No IMEI yet. Dial *#06# on the phone and compare it with the box.", weight=0)

    for label, num in (("box", box), ("phone", device)):
        if num and not valid_imei(num):
            return result(NAME, "fail", f"IMEI on the {label} ({num}) is not a valid IMEI (fails the format check)",
                          weight=40)

    ctx["imei"] = imei
    if box and device:
        if box != device:
            ctx.setdefault("critical_fails", []).append(NAME)
            return result(NAME, "fail",
                          f"IMEI on the box ({box}) doesn't match the phone's IMEI from *#06# ({device}). "
                          "This phone isn't the one the box was made for.", weight=50)
        return result(NAME, "pass", f"IMEI {box} is valid and matches between the box and the phone (*#06#)",
                      weight=20)
    where = "box" if box else "phone"
    return result(NAME, "pass",
                  f"IMEI {imei} (from the {where}) has a valid format. "
                  + ("Dial *#06# on the phone and check it matches the box." if box else
                     "Check it matches the IMEI printed on the box."),
                  weight=10)
