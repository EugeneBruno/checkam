"""Check Am MCP server: lets any AI assistant check a product before buying.

Run (stdio, for Claude desktop app and other MCP clients):
    python mcp_server.py

Example client config (claude_desktop_config.json):
    {"mcpServers": {"checkam": {"command": "python", "args": ["/full/path/to/backend/mcp_server.py"]}}}
"""
import base64
import os
import sys
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:  # mcp >= 2
    from mcp.server.mcpserver import MCPServer as _Server
except ImportError:  # mcp 1.x
    from mcp.server.fastmcp import FastMCP as _Server

from db import connect
from pipeline import report_suspect as _report
from pipeline import verify_product as _verify

mcp = _Server("checkam")
conn = connect()


@mcp.tool()
def verify_product(
    brand: Optional[str] = None,
    name: Optional[str] = None,
    category: Optional[str] = None,
    nafdac_no: Optional[str] = None,
    batch: Optional[str] = None,
    expiry: Optional[str] = None,
    barcode: Optional[str] = None,
    imei: Optional[str] = None,
    imei_device: Optional[str] = None,
    price_ngn: Optional[float] = None,
    seller: Optional[str] = None,
    state: Optional[str] = None,
    images_base64: Optional[list[str]] = None,
    situation: str = "before_buying",
) -> dict:
    """Check whether a product (e.g. from a marketplace listing) is likely genuine before buying it in Nigeria.

    Pass whatever the listing shows: brand, name, NAFDAC number, batch, expiry, barcode, IMEI (box) and
    imei_device (what *#06# shows on the phone), and
    optionally listing photos as base64. Returns verdict (likely_genuine | suspicious | likely_fake |
    insufficient_evidence), trust_score 0-100, confidence, evidence with sources, and a recommendation.
    Only proceed to pay when the recommendation is "buy"; ask the human on "caution"; never pay on "do_not_buy".
    """
    fields = {k: v for k, v in dict(brand=brand, name=name, category=category, nafdac_no=nafdac_no, batch=batch,
                                     expiry=expiry, barcode=barcode, imei=imei,
                                     imei_device=imei_device).items() if v}
    images = [base64.b64decode(b) for b in (images_base64 or [])]
    out = _verify(conn, images=images, fields=fields, situation=situation, location={"state": state})
    if price_ngn or seller:
        out["listing"] = {"price_ngn": price_ngn, "seller": seller}
    return out


@mcp.tool()
def report_suspect(scan_id: Optional[str] = None, brand: Optional[str] = None, name: Optional[str] = None,
                   batch: Optional[str] = None, nafdac_no: Optional[str] = None, seller: Optional[str] = None,
                   state: Optional[str] = None, note: Optional[str] = None) -> dict:
    """Report a product the agent believes is fake, so other buyers and agents are warned."""
    product = {"brand": brand, "name": name, "identifiers": {"batch": batch, "nafdac_no": nafdac_no}}
    return _report(conn, scan_id=scan_id, product=product, location={"state": state},
                   seller=seller, note=note, reporter="agent")


if __name__ == "__main__":
    mcp.run()
