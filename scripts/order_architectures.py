#!/usr/bin/env python3
"""Order sensitivity (OS) of the Table 1 architectures A, B and D in the arrival-order
cache simulation (Table 1, OS column; Supplementary S.3).

Each architecture is simulated with exactly the decision rule it has in Table 1
(scripts/rq5_heldout.py), at the operating point tuned on all pairs
(results/rq5_heldout.json, in_sample.params):
  A threshold-only        serve iff s > tau_BA
  B + cross-encoder       s in band [tau_BA - 0.06, tau_BA + 0.06]: serve iff CE score > ce_tau;
                          above the band: serve; below: miss
  D + discrete-slot guard serve iff s > tau_BA and the numeric/acronym slots of the two
                          queries match
The cache checks only its most similar stored entry (as in the RQ3b simulation): a
rejected candidate is a miss and the query is stored. The cross-encoder reads
(stored question, incoming question), the orientation of (seed, variant) in Table 1.

Workload: the first N=1,000 queries of the headline RQ3b workload
(analyze_final.stratified_sample, rng 42), with its cached BGE-M3 embeddings
(.cache/rq3b, written by rq3b_answer_identity.py). Outputs results/architectures.json.
C (LLM verifier) is not simulated: it would need a live model in the arrival loop.
"""
import datetime as dt
import json
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_final import load_final, stratified_sample

REPO = Path(__file__).resolve().parents[1]
CROSS = "BAAI/bge-reranker-v2-m3"
N, ORDERS, SIM_SEED = 1000, 50, 20261031


def slots(q):
    nums = set(re.findall(r"\d+(?:[.,/]\d+)*", q))
    caps = set(re.findall(r"\b[A-ZĐ]{2,}\b", q))
    return nums, caps


def simulate(S, keys, decide, orders):
    """Top-1 cache: serve the most similar stored entry iff decide(i, j, s)."""
    n = S.shape[0]
    served = [set() for _ in range(n)]
    hits = wrong = 0
    for order in orders:
        stored = []
        for i in order:
            if stored:
                sims = S[i, stored]
                b = int(np.argmax(sims))
                j = stored[b]
                if decide(i, j, float(sims[b])):
                    served[i].add(keys[j]); hits += 1
                    wrong += keys[j] != keys[i]
                    continue
            stored.append(i)
            served[i].add(keys[i])
    tot = n * len(orders)
    return {"OS": sum(1 for s in served if len(s) > 1) / n,
            "hit": hits / tot, "wrong": wrong / tot}


def main() -> int:
    recs = load_final()
    sample = stratified_sample(recs, 5000, np.random.default_rng(42))
    items, keys = [], []
    seen = set()
    for r in sample:                      # identical construction to rq3b_answer_identity.py
        if r["seed_id"] not in seen:
            seen.add(r["seed_id"])
            items.append(r["seed_question"]); keys.append(r["seed_id"])
        items.append(r["variation"])
        keys.append(r["seed_id"] if r["expected_label"] == "HIT" else r["id"])
    E = np.load(REPO / ".cache" / "rq3b" / f"bge_m3_workload_{len(items)}.npy")
    assert E.shape[0] == len(items) == 5231, (E.shape, len(items))
    items, keys, E = items[:N], keys[:N], E[:N]
    S = E @ E.T

    p = json.loads((REPO / "results" / "rq5_heldout.json").read_text())["in_sample"]["params"]
    tau, (lo, hi), ce_tau = p["tau_BA"], p["band"], p["ce_tau"]

    # cross-encoder scores for every ordered (stored j, query i) pair inside the band
    import torch
    from sentence_transformers import CrossEncoder
    ce = CrossEncoder(CROSS, device="mps" if torch.backends.mps.is_available() else "cpu")
    idx = [(j, i) for i in range(N) for j in range(N) if i != j and lo <= S[i, j] <= hi]
    print(f"cross-encoder: {len(idx)} ordered in-band pairs", flush=True)
    sc = ce.predict([(items[j], items[i]) for j, i in idx], batch_size=64)
    ce_ok = {(j, i): float(s) > ce_tau for (j, i), s in zip(idx, sc)}

    sl = [slots(t) for t in items]
    rules = {
        "A": lambda i, j, s: s > tau,
        "B": lambda i, j, s: ce_ok[(j, i)] if lo <= s <= hi else s > hi,
        "D": lambda i, j, s: s > tau and sl[i] == sl[j],
    }
    rng = np.random.default_rng(SIM_SEED)
    orders = [rng.permutation(N) for _ in range(ORDERS)]   # same orders for every architecture
    res = {}
    for name, rule in rules.items():
        res[name] = simulate(S, keys, rule, orders)
        print(name, res[name], flush=True)

    out = {"generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "script": "scripts/order_architectures.py",
           "workload": f"first {N} queries of the RQ3b workload (stratified_sample, rng 42)",
           "orders": ORDERS, "sim_seed": SIM_SEED,
           "params": {"tau_BA": tau, "band": [lo, hi], "ce_tau": ce_tau,
                      "source": "results/rq5_heldout.json in_sample.params"},
           "order_sensitivity": {k: v["OS"] for k, v in res.items()},
           "detail": res,
           "note": "C (LLM verifier) not simulated: it needs a live model in the arrival loop. "
                   "Error rates of all architectures: results/rq5_heldout.json."}
    (REPO / "results" / "architectures.json").write_text(json.dumps(out, indent=2) + "\n",
                                                         encoding="utf-8")
    print("wrote results/architectures.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
