"""Call the vision model directly (no server) with one photo, and time each step.

Run in a terminal where CHECKAM_LLM, GEMINI_API_KEY / ANTHROPIC_API_KEY and GEMINI_MODEL are set:
    python test_vision.py "..\\..\\lacasera test image.jpeg"
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vision  # noqa: E402

if len(sys.argv) < 2:
    print(__doc__)
    sys.exit(1)

provider = os.environ.get("CHECKAM_LLM", "anthropic")
key_name = "GEMINI_API_KEY" if provider == "gemini" else "ANTHROPIC_API_KEY"
key = os.environ.get(key_name, "")
print(f"provider={provider}  model={os.environ.get('GEMINI_MODEL') if provider == 'gemini' else os.environ.get('ANTHROPIC_MODEL', 'default')}")
print(f"{key_name}: {'set, ' + str(len(key)) + ' characters' if key else 'NOT SET'}")

t = time.time()
raw = open(sys.argv[1], "rb").read()
small = vision.shrink(raw)
print(f"1. photo: {len(raw) / 1e6:.1f} MB -> {len(small) / 1e6:.2f} MB after shrinking ({time.time() - t:.1f}s)")

print(f"2. calling the model ({vision.FAST_TIMEOUT_S}s per model, then the next one) ...")
t = time.time()
try:
    out = vision.identify([raw])
except Exception as exc:
    print(f"   FAILED after {time.time() - t:.1f}s: {type(exc).__name__}: {str(exc)[:500]}")
    sys.exit(1)
print(f"   OK in {time.time() - t:.1f}s")
print(json.dumps(out, indent=2)[:2500])
