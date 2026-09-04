#!/usr/bin/env python3
"""Doc-level Stage A resume: emit, per domain, the scale-input docs that produced no
seeds yet (covers batches lost to api_error rate limiting).

  python3 scripts/build_stage_a_remaining.py
Writes corpus/<dom>/stage_a_remaining.jsonl and prints counts.
"""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def main() -> int:
    have = set()
    seeds = REPO / "data" / "02_seeds.jsonl"
    if seeds.exists():
        for ln in seeds.read_text(encoding="utf-8").splitlines():
            if ln.strip():
                have.add(json.loads(ln).get("doc_id"))
    total = 0
    for dom in ("d1", "d2", "d3", "d4", "d5"):
        src = REPO / "corpus" / dom / "stage_a_scale.jsonl"
        if not src.exists():
            continue
        remaining = [ln for ln in src.read_text(encoding="utf-8").splitlines()
                     if ln.strip() and json.loads(ln)["doc_id"] not in have]
        out = REPO / "corpus" / dom / "stage_a_remaining.jsonl"
        out.write_text("\n".join(remaining) + ("\n" if remaining else ""), encoding="utf-8")
        print(f"{dom}: {len(remaining)} docs still need extraction")
        total += len(remaining)
    print(f"total remaining: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
