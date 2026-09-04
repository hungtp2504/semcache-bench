#!/usr/bin/env python3
"""Parse raw B1/B2 judge output into flat judgment records (04a/04b). Append-only.

  python3 scripts/assemble_judgments.py --raw logs/generation/B1_0001.raw.md \
      --batch-id B1_0001 --model claude-sonnet-5 --out data/04a_judgments_b1.jsonl
"""
import argparse
import datetime as dt
import json
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raw", required=True)
    ap.add_argument("--batch-id", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    ts = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    records, bad = [], 0
    for ln in Path(a.raw).read_text(encoding="utf-8").splitlines():
        ln = ln.strip().strip("`")
        if not ln.startswith("{"):
            continue
        try:
            o = json.loads(ln)
        except json.JSONDecodeError:
            bad += 1
            continue
        if not o.get("id") or not isinstance(o.get("axis_ok"), bool):
            bad += 1
            continue
        conf = o.get("conf")
        if not isinstance(conf, (int, float)) or not (0 <= conf <= 1):
            bad += 1
            continue
        records.append({"id": o["id"], "judge_model": a.model,
                        "axis_ok": o["axis_ok"], "conf": float(conf),
                        "issue": o.get("issue"), "batch_id": a.batch_id, "ts": ts})
    if not records:
        print(f"NO judgments parsed (bad={bad})", file=sys.stderr)
        return 1
    with open(a.out, "a", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    ok = sum(1 for r in records if r["axis_ok"])
    print(f"appended {len(records)} judgments (axis_ok {ok}/{len(records)}, bad lines: {bad})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
