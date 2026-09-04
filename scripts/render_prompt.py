#!/usr/bin/env python3
"""Assemble a stage prompt deterministically and hash its cached block.

The block between <!-- CACHED BLOCK START --> and <!-- CACHED BLOCK END --> must stay
byte-identical across every turn of a stage (prompt caching + comparability, PLAN §13).
This script (a) renders prompt = cached block + batch input, (b) prints the sha256 of
the cached block so each batch's .meta.json can prove byte-identity.

Usage:
  python3 scripts/render_prompt.py prompts/A4_variation.md --hash
  python3 scripts/render_prompt.py prompts/A4_variation.md \
      --batch-id A4_0001 --input data/02_seeds.jsonl --lines 1:20 > /tmp/prompt.txt

Stdlib only.
"""
import argparse
import hashlib
import re
import sys
from pathlib import Path

START = "<!-- CACHED BLOCK START -->"
END = "<!-- CACHED BLOCK END -->"


def split_prompt(text: str):
    if START not in text or END not in text:
        raise SystemExit("prompt file lacks CACHED BLOCK markers")
    cached = text.split(START, 1)[1].split(END, 1)[0]
    tail = text.split(END, 1)[1]
    return cached, tail


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("prompt_file")
    ap.add_argument("--hash", action="store_true", help="print sha256 of cached block and exit")
    ap.add_argument("--batch-id")
    ap.add_argument("--input", help="JSONL file with batch items")
    ap.add_argument("--lines", help="1-based inclusive range into the input, e.g. 1:20")
    a = ap.parse_args()

    text = Path(a.prompt_file).read_text(encoding="utf-8")
    cached, tail = split_prompt(text)
    digest = hashlib.sha256(cached.encode("utf-8")).hexdigest()

    if a.hash:
        print(digest)
        return 0

    if not (a.batch_id and a.input and a.lines):
        raise SystemExit("need --batch-id, --input and --lines (or use --hash)")

    m = re.fullmatch(r"(\d+):(\d+)", a.lines)
    if not m:
        raise SystemExit("--lines must look like 1:20")
    lo, hi = int(m.group(1)), int(m.group(2))
    lines = [ln for ln in Path(a.input).read_text(encoding="utf-8").splitlines() if ln.strip()]
    batch = lines[lo - 1: hi]
    if len(batch) != hi - lo + 1:
        print(f"warning: requested {hi - lo + 1} lines, file provided {len(batch)}", file=sys.stderr)

    body = tail
    body = body.replace("{{batch_id}}", a.batch_id)
    for slot in ("{{seeds}}", "{{documents}}", "{{items}}", "{{pairs}}"):
        body = body.replace(slot, "\n".join(batch))
    # cached block FIRST — that is what makes prompt caching work
    sys.stdout.write(cached.strip() + "\n" + body)
    print(f"\n[cached_block_sha256: {digest}]", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
