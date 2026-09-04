#!/usr/bin/env python3
"""RQ6 — does the generator tier change the study's conclusions?

For each generator's variant set (opus = main benchmark restricted to the RQ6 seed
subset; sonnet; haiku), compute each encoder's mean IO over change axes, rank the
encoders, and compare rankings with Kendall's tau. Also compare axis-level IO
orderings. tau > 0.9 -> "cheap generators suffice"; < 0.7 -> generator matters.

  python3 scripts/rq6_analysis.py [--models ...]
"""
import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import kendalltau

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_pilot import rq3a
from embed_utils import DEFAULT_RISK_MODELS

REPO = Path(__file__).resolve().parents[1]
ENCODERS = ["sentence-transformers/all-MiniLM-L6-v2", "BAAI/bge-m3",
            "intfloat/e5-large-v2", "thenlper/gte-large",
            "nomic-ai/nomic-embed-text-v1.5", "intfloat/multilingual-e5-large"]


def load_jsonl(p):
    out = []
    for ln in Path(p).read_text(encoding="utf-8").splitlines():
        if ln.strip():
            out.append(json.loads(ln))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--models", nargs="+", default=ENCODERS)
    ap.add_argument("--out", default=str(REPO / "results" / "rq6.json"))
    a = ap.parse_args()

    subset = {json.loads(l)["seed_id"] for l in
              open(REPO / "data" / "rq6_seed_subset.jsonl", encoding="utf-8") if l.strip()}
    sets = {}
    # opus = main frozen benchmark restricted to subset (judge-filtered)
    sets["opus"] = [r for r in load_jsonl(REPO / "data" / "05_final.jsonl")
                    if r["seed_id"] in subset]
    for gen in ("sonnet", "haiku"):
        p = REPO / "data" / f"03_variations_rq6_{gen}.jsonl"
        if p.exists():
            sets[gen] = load_jsonl(p)  # unjudged; same construction-derived labels
    for k, v in sets.items():
        print(f"{k}: {len(v)} pairs, {len({r['seed_id'] for r in v})} seeds")

    results = {"generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
               "note": "opus set is judge-filtered (main benchmark); sonnet/haiku unfiltered "
                       "generation - rank comparison is the pre-registered measure",
               "per_generator": {}, "kendall": {}}
    mean_io = {}
    for gen, recs in sets.items():
        per_enc = {}
        for enc in a.models:
            io, _ = rq3a(recs, enc, mock=False)
            vals = [v["io"] for v in io["io_per_axis"].values()]
            per_enc[enc] = {"mean_io": float(np.mean(vals)), "per_axis": io["io_per_axis"]}
            print(f"  [{gen}] {enc.split('/')[-1]}: mean IO {np.mean(vals):.4f}", flush=True)
        results["per_generator"][gen] = per_enc
        mean_io[gen] = [per_enc[e]["mean_io"] for e in a.models]

    for g1, g2 in (("opus", "sonnet"), ("opus", "haiku"), ("sonnet", "haiku")):
        if g1 in mean_io and g2 in mean_io:
            t, p = kendalltau(mean_io[g1], mean_io[g2])
            results["kendall"][f"{g1}_vs_{g2}"] = {"tau": float(t), "p": float(p)}
            print(f"Kendall tau {g1} vs {g2}: {t:.3f} (p={p:.3g})")

    Path(a.out).write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
