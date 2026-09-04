#!/usr/bin/env python3
"""Parse raw A4 model output into canonical variation records (PLAN §14 schema).

HARD RULE ENFORCED HERE: expected_label and axis_group are DERIVED FROM THE AXIS by
this code (P* -> HIT/invariant, N1-N2 -> MISS/slope, N3-N6 -> MISS/cliff). No model
output ever sets them.

Salvage-friendly: skips lines that are not valid JSON or fail checks, reports counts,
appends only the valid records. Never overwrites.

Usage:
  python3 scripts/assemble_variations.py \
      --raw logs/generation/A4_0001.raw.md \
      --seeds data/02_seeds.jsonl \
      --batch-id A4_0001 --model claude-opus-5 \
      [--out data/03_variations.jsonl]

Stdlib only.
"""
import argparse
import datetime as dt
import json
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

AXIS_GROUP = {
    "P1": "invariant", "P2": "invariant", "P3": "invariant",
    "N1": "slope", "N2": "slope",
    "N3": "cliff", "N4": "cliff", "N5": "cliff", "N6": "cliff",
}
LABEL = {"invariant": "HIT", "slope": "MISS", "cliff": "MISS"}
# v1.2: N4/N5 overgenerated (4 candidates; top-2 judge-passed kept at freeze)
EXPECTED_PER_SEED = {"P1": 4, "P2": 4, "P3": 4, "N1": 2, "N2": 2, "N3": 2, "N4": 4, "N5": 4, "N6": 2}


def load_seeds(path: Path) -> dict:
    seeds = {}
    for ln in path.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            s = json.loads(ln)
        except json.JSONDecodeError:
            continue
        if "seed_id" in s:
            seeds[s["seed_id"]] = s
    return seeds


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raw", required=True)
    ap.add_argument("--seeds", default=str(REPO / "data" / "02_seeds.jsonl"))
    ap.add_argument("--batch-id", required=True)
    ap.add_argument("--model", required=True, help="exact generator model string")
    ap.add_argument("--out", default=str(REPO / "data" / "03_variations.jsonl"))
    a = ap.parse_args()

    seeds = load_seeds(Path(a.seeds))
    if not seeds:
        print("no seeds loaded — check --seeds", file=sys.stderr)
        return 2

    ts = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    records, bad, skipped = [], 0, 0
    texts_seen = set()
    per_seed_axis = Counter()

    for ln in Path(a.raw).read_text(encoding="utf-8").splitlines():
        ln = ln.strip().strip("`")
        if not ln.startswith("{"):
            continue
        try:
            v = json.loads(ln)
        except json.JSONDecodeError:
            bad += 1
            continue
        seed_id, axis, text = v.get("seed_id"), v.get("axis"), (v.get("text") or "").strip()
        if axis not in AXIS_GROUP or seed_id not in seeds or not text:
            bad += 1
            continue
        seed = seeds[seed_id]
        if text == seed.get("question", "").strip() or (seed_id, text) in texts_seen:
            skipped += 1  # duplicate of seed or of another variant
            continue
        texts_seen.add((seed_id, text))
        per_seed_axis[(seed_id, axis)] += 1
        k = per_seed_axis[(seed_id, axis)]
        group = AXIS_GROUP[axis]
        records.append({
            "id": f"{seed_id}_{axis}_v{k}",
            "domain": seed.get("domain"),
            "seed_id": seed_id,
            "seed_question": seed.get("question"),
            "answer": seed.get("answer"),
            "variation": text,
            "axis": axis,
            "axis_group": group,                    # derived
            "expected_label": LABEL[group],         # derived — never model-set
            "delta": v.get("delta") if axis.startswith("N") else None,
            "generator_model": a.model,
            "batch_id": a.batch_id,
            "judge1": None, "judge2": None,
            "ts": ts,
        })

    if not records:
        print(f"NO valid records parsed (bad={bad}) — mark batch failed", file=sys.stderr)
        return 1

    with open(a.out, "a", encoding="utf-8") as f:  # append-only
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # report
    seed_ids = sorted({r["seed_id"] for r in records})
    print(f"appended {len(records)} records to {a.out}  (bad lines: {bad}, dup-skipped: {skipped})")
    short = []
    for sid in seed_ids:
        missing = {ax: n - per_seed_axis.get((sid, ax), 0)
                   for ax, n in EXPECTED_PER_SEED.items()
                   if per_seed_axis.get((sid, ax), 0) != n}
        if missing:
            short.append((sid, missing))
    if short:
        print(f"WARNING: {len(short)}/{len(seed_ids)} seeds deviate from 24-variant contract:")
        for sid, miss in short[:10]:
            print(f"  {sid}: off-by {miss}")
        print("  (negative = extra). Note this in the manifest.")
    else:
        print(f"all {len(seed_ids)} seeds have the full 24-variant contract ✓")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
