#!/usr/bin/env python3
"""Build judge-batch input from data/03_variations.jsonl.

  python3 scripts/prep_judge_input.py --out data/judge_input.jsonl
Each line: {id, axis, seed_question, answer, variation, delta}. Skips records already
judged in --exclude (a 04a/04b file) so reruns only cover the gap.
"""
import argparse
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--variations", default=str(REPO / "data" / "03_variations.jsonl"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--exclude", default=None)
    a = ap.parse_args()

    done = set()
    if a.exclude and Path(a.exclude).exists():
        for ln in Path(a.exclude).read_text(encoding="utf-8").splitlines():
            try:
                done.add(json.loads(ln)["id"])
            except Exception:
                pass
    n = 0
    src = Path(a.variations)
    if not src.exists():
        Path(a.out).write_text("", encoding="utf-8")
        print(f"{a.out}: 0 items (no variations file yet)")
        return 0
    with open(a.out, "w", encoding="utf-8") as f:
        for ln in src.read_text(encoding="utf-8").splitlines():
            if not ln.strip():
                continue
            v = json.loads(ln)
            if v["id"] in done:
                continue
            f.write(json.dumps({"id": v["id"], "axis": v["axis"],
                                "seed_question": v["seed_question"], "answer": v["answer"],
                                "variation": v["variation"], "delta": v.get("delta")},
                               ensure_ascii=False) + "\n")
            n += 1
    print(f"{a.out}: {n} items")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
