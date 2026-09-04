#!/usr/bin/env python3
"""Pilot analysis: real IO per axis (RQ3a) + answer-aware order dependence (RQ3b)
on the generated benchmark (data/03_variations.jsonl).

- Pairs: (seed_question, variation) with expected_label from construction.
  --judged-only keeps variants passing the primary judge (04a, axis_ok true).
- RQ3a: IO per axis x model (Definition in paper §3.4), plus group-level IO.
- RQ3b: simulate cache over random arrival orders of ALL queries (seeds + variants);
  each query's true answer key = its seed_id (variants of one seed share the answer
  iff expected HIT; MISS variants get their own synthetic answer key). A query is
  answer-unstable if the answer key that serves it differs across orders.

  python3 scripts/analyze_pilot.py [--models ...] [--taus 0.85 0.9 0.95] [--orders 200]
"""
import argparse
import datetime as dt
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from embed_utils import (DEFAULT_RISK_MODELS, MOCK_MODEL_NAME, embed_texts,
                         irreducible_overlap)

REPO = Path(__file__).resolve().parents[1]
GROUP = {"P1": "invariant", "P2": "invariant", "P3": "invariant",
         "N1": "slope", "N2": "slope",
         "N3": "cliff", "N4": "cliff", "N5": "cliff", "N6": "cliff"}


def load_records(judged_only: bool):
    recs = []
    for ln in (REPO / "data" / "03_variations.jsonl").read_text(encoding="utf-8").splitlines():
        if ln.strip():
            recs.append(json.loads(ln))
    if judged_only:
        ok_ids = set()
        p = REPO / "data" / "04a_judgments_b1.jsonl"
        if p.exists():
            for ln in p.read_text(encoding="utf-8").splitlines():
                if ln.strip():
                    j = json.loads(ln)
                    if j.get("axis_ok"):
                        ok_ids.add(j["id"])
            recs = [r for r in recs if r["id"] in ok_ids]
    return recs


def rq3a(recs, model, mock):
    """IO per axis: HIT population = P-axis pair sims; MISS population per N-axis."""
    qs = [r["seed_question"] for r in recs] + [r["variation"] for r in recs]
    E = embed_texts(qs, model, mock=mock)
    n = len(recs)
    sims = np.einsum("ij,ij->i", E[:n], E[n:])
    by_axis = defaultdict(list)
    for r, s in zip(recs, sims):
        by_axis[r["axis"]].append(float(s))
    hit_sims = np.array(sum((by_axis[a] for a in ("P1", "P2", "P3") if a in by_axis), []))
    out = {"axis_mean_sim": {a: float(np.mean(v)) for a, v in sorted(by_axis.items())},
           "io_per_axis": {}, "io_per_group": {}}
    if hit_sims.size == 0:
        return out, sims
    for ax, v in sorted(by_axis.items()):
        if ax.startswith("N") and v:
            io, tau = irreducible_overlap(hit_sims, np.array(v))
            out["io_per_axis"][ax] = {"io": round(io, 4), "tau_star": round(tau, 4),
                                      "n": len(v)}
    for g in ("slope", "cliff"):
        v = sum((by_axis[a] for a in by_axis if GROUP.get(a) == g and a.startswith("N")), [])
        if v:
            io, tau = irreducible_overlap(hit_sims, np.array(v))
            out["io_per_group"][g] = {"io": round(io, 4), "tau_star": round(tau, 4),
                                      "n": len(v)}
    return out, sims


def rq3b(recs, model, taus, orders, mock, rng):
    """Answer-aware order-dependence simulation over seeds + variants."""
    # answer key: HIT variants share the seed's key; MISS variants have their own
    items, keys = [], []
    seen_seed = set()
    for r in recs:
        if r["seed_id"] not in seen_seed:
            seen_seed.add(r["seed_id"])
            items.append(r["seed_question"])
            keys.append(r["seed_id"])
        items.append(r["variation"])
        keys.append(r["seed_id"] if r["expected_label"] == "HIT" else r["id"])
    E = embed_texts(items, model, mock=mock)
    S = E @ E.T
    n = len(items)
    res = {}
    for tau in taus:
        served_keys = [set() for _ in range(n)]
        wrong_serve_rates, hit_rates = [], []
        for _ in range(orders):
            order = rng.permutation(n)
            stored = []
            hits = wrong = 0
            for i in order:
                if stored:
                    sims = S[i, stored]
                    b = int(np.argmax(sims))
                    if sims[b] > tau:
                        j = stored[b]
                        served_keys[i].add(keys[j])
                        hits += 1
                        if keys[j] != keys[i]:
                            wrong += 1
                        continue
                stored.append(int(i))
                served_keys[i].add(keys[i])
            hit_rates.append(hits / n)
            wrong_serve_rates.append(wrong / n)
        res[str(tau)] = {
            "answer_instability": sum(1 for s in served_keys if len(s) > 1) / n,
            "false_answer_rate_mean": float(np.mean(wrong_serve_rates)),
            "hit_rate_mean": float(np.mean(hit_rates)),
            "hit_rate_std": float(np.std(hit_rates)),
            "n_queries": n,
        }
    return res


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--models", nargs="+", default=None)
    ap.add_argument("--taus", nargs="+", type=float, default=[0.85, 0.90, 0.95])
    ap.add_argument("--orders", type=int, default=200)
    ap.add_argument("--judged-only", action="store_true")
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--out", default=str(REPO / "results" / "pilot_analysis.json"))
    a = ap.parse_args()

    recs = load_records(a.judged_only)
    if len(recs) < 100:
        print(f"only {len(recs)} variation records — wait for more A4 batches", file=sys.stderr)
        return 2
    rng = np.random.default_rng(42)
    models = [MOCK_MODEL_NAME] if a.mock else (a.models or DEFAULT_RISK_MODELS)
    results = {"generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
               "n_records": len(recs), "judged_only": a.judged_only, "mock": a.mock,
               "models": {}}
    Path(a.out).parent.mkdir(exist_ok=True)
    failed = []
    for m in models:
        print(f"\n== {m} ==", flush=True)
        try:
            io, _ = rq3a(recs, m, a.mock)
            od = rq3b(recs, m, a.taus, a.orders, a.mock, rng)
        except Exception as e:  # one broken model must not sink the others
            print(f"  FAILED: {type(e).__name__}: {e}", flush=True)
            failed.append(m)
            continue
        results["models"][m] = {"rq3a": io, "rq3b": od}
        print("  IO per axis:", json.dumps(io["io_per_axis"]))
        print("  IO per group:", json.dumps(io["io_per_group"]))
        for tau, r in od.items():
            print(f"  tau={tau}: answer_instability={r['answer_instability']:.1%} "
                  f"false_answer_rate={r['false_answer_rate_mean']:.1%} "
                  f"hit_rate={r['hit_rate_mean']:.1%}")
        # incremental save — a later crash never loses finished models
        results["failed_models"] = failed
        Path(a.out).write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {a.out}  (ok {len(results['models'])}, failed {len(failed)})")
    return 0 if results["models"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
