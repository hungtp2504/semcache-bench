#!/usr/bin/env python3
"""FINAL analysis on the frozen benchmark (data/05_final.jsonl).

RQ3a: IO per axis (and per domain) x encoder — full 46k pairs, all encoders.
RQ3b: answer-aware order simulation on a stratified sample (PLAN §7: ~5,000 queries,
      configurable permutations) — quadratic in sample size, hence sampled.

  python3 scripts/analyze_final.py --models ... --rq3b-sample 5000 --orders 500
"""
import argparse
import datetime as dt
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_pilot import rq3a, rq3b  # reuse the measured machinery
from embed_utils import DEFAULT_RISK_MODELS

REPO = Path(__file__).resolve().parents[1]


def load_final():
    recs = []
    for ln in (REPO / "data" / "05_final.jsonl").read_text(encoding="utf-8").splitlines():
        if ln.strip():
            recs.append(json.loads(ln))
    return recs


def stratified_sample(recs, n, rng):
    by_seed = defaultdict(list)
    for r in recs:
        by_seed[r["seed_id"]].append(r)
    seeds = sorted(by_seed)
    rng.shuffle(seeds)
    out = []
    for s in seeds:
        out.extend(by_seed[s])
        if len(out) >= n:
            break
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--models", nargs="+", default=None)
    ap.add_argument("--taus", nargs="+", type=float, default=[0.85, 0.90, 0.95])
    ap.add_argument("--orders", type=int, default=500)
    ap.add_argument("--rq3b-sample", type=int, default=5000)
    ap.add_argument("--skip-rq3b", action="store_true")
    ap.add_argument("--out", default=str(REPO / "results" / "final_analysis.json"))
    a = ap.parse_args()

    recs = load_final()
    rng = np.random.default_rng(42)
    sample = stratified_sample(recs, a.rq3b_sample, rng)
    models = a.models or DEFAULT_RISK_MODELS
    print(f"frozen pairs: {len(recs)}; rq3b sample: {len(sample)} "
          f"({len({r['seed_id'] for r in sample})} seeds); models: {len(models)}")

    results = {"generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
               "n_pairs": len(recs), "rq3b_sample": len(sample), "orders": a.orders,
               "models": {}, "failed_models": []}
    Path(a.out).parent.mkdir(exist_ok=True)
    for m in models:
        print(f"\n== {m} ==", flush=True)
        entry = {}
        try:
            io_all, _ = rq3a(recs, m, mock=False)
            entry["rq3a"] = io_all
            # per-domain IO
            per_dom = {}
            for dom in sorted({r["domain"] for r in recs}):
                sub = [r for r in recs if r["domain"] == dom]
                io_d, _ = rq3a(sub, m, mock=False)
                per_dom[dom] = io_d["io_per_axis"]
            entry["rq3a_per_domain"] = per_dom
            print("  IO per axis:", json.dumps(io_all["io_per_axis"]))
            if not a.skip_rq3b:
                od = rq3b(sample, m, a.taus, a.orders, False, rng)
                entry["rq3b"] = od
                for tau, r in od.items():
                    print(f"  tau={tau}: instability={r['answer_instability']:.1%} "
                          f"false_answers={r['false_answer_rate_mean']:.1%} "
                          f"hit_rate={r['hit_rate_mean']:.1%}")
        except Exception as e:
            print(f"  FAILED: {type(e).__name__}: {e}", flush=True)
            results["failed_models"].append(m)
            continue
        results["models"][m] = entry
        Path(a.out).write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {a.out} (ok {len(results['models'])}, failed {len(results['failed_models'])})")
    return 0 if results["models"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
