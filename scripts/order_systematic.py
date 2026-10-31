#!/usr/bin/env python3
"""Systematic characterization of order-dependent cache behavior (review point 7)
and architecture isolation A-E (review point 6).

Order sensitivity OS = share of queries whose serving source varies across random
arrival orders. Sweeps: workload size N, threshold tau, Zipf skew alpha, encoder,
eviction policy (unbounded / FIFO-capacity / LRU-capacity).

Architectures (Table 1) are evaluated by scripts/rq5_heldout.py (error rates) and
scripts/order_architectures.py (order sensitivity).

Outputs results/order_systematic.json.
"""
import json
import re
import sys
import datetime as dt
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from embed_utils import embed_texts
from analyze_final import stratified_sample

REPO = Path(__file__).resolve().parents[1]
GROUP = {"N1": "slope", "N2": "slope", "N3": "cliff", "N4": "cliff",
         "N5": "cliff", "N6": "cliff", "P1": "inv", "P2": "inv", "P3": "inv"}
ENCODERS = {"BAAI/bge-m3": "BGE-M3",
            "sentence-transformers/all-MiniLM-L6-v2": "MiniLM-L6",
            "nomic-ai/nomic-embed-text-v1.5": "Nomic-v1.5"}


def load_final():
    return [json.loads(l) for l in (REPO / "data" / "05_final.jsonl")
            .read_text(encoding="utf-8").splitlines() if l.strip()]


def build_workload(recs, rng, n_seeds_cap=None):
    """Queries = seeds + variants (one entry each); answer key = seed for HIT else own id."""
    items, keys = [], []
    seen = set()
    for r in recs:
        if r["seed_id"] not in seen:
            seen.add(r["seed_id"])
            items.append(r["seed_question"]); keys.append(r["seed_id"])
        items.append(r["variation"])
        keys.append(r["seed_id"] if r["expected_label"] == "HIT" else r["id"])
    return items, keys


def simulate(S, keys, tau, orders, rng, policy="none", capacity=None,
             arrival=None, band=None, band_decide=None):
    """Generic cache sim. arrival: list of index-sequences (len may exceed n for Zipf).
    band/band_decide: verifier hooks — if sim in band, band_decide(i, j) -> serve?"""
    n = S.shape[0]
    served = [set() for _ in range(n)]
    hits_list, wrong_list = [], []
    for order in arrival:
        stored, stored_set = [], set()
        lru = {}
        hits = wrong = t = 0
        for i in order:
            t += 1
            hit = False
            if stored:
                sims = S[i, stored]
                b = int(np.argmax(sims))
                s = sims[b]
                if s > tau:
                    j = stored[b]
                    ok = True
                    if band is not None and band[0] <= s <= band[1]:
                        ok = band_decide(i, j)
                    if ok:
                        served[i].add(keys[j]); hits += 1
                        if keys[j] != keys[i]:
                            wrong += 1
                        lru[j] = t
                        hit = True
            if not hit:
                if i not in stored_set:
                    stored.append(i); stored_set.add(i); lru[i] = t
                    if capacity and len(stored) > capacity:
                        if policy == "lru":
                            ev = min(stored, key=lambda x: lru[x])
                        else:  # fifo
                            ev = stored[0]
                        stored.remove(ev); stored_set.discard(ev)
                served[i].add(keys[i])
        hits_list.append(hits / len(order))
        wrong_list.append(wrong / len(order))
    os_ = sum(1 for s in served if len(s) > 1) / n
    return {"OS": os_, "hit": float(np.mean(hits_list)),
            "wrong": float(np.mean(wrong_list))}


def main() -> int:
    rng = np.random.default_rng(42)
    recs = load_final()
    # the headline RQ3b workload (analyze_final.py): whole seed families drawn in a
    # seeded random order until >= 5,000 pairs -> 5,231 queries over all five domains.
    # Sub-workloads of size N take the first N queries, i.e. whole random families.
    sample = stratified_sample(recs, 5000, np.random.default_rng(42))
    items, keys = build_workload(sample, rng)
    master = np.arange(len(items))
    assert len(master) == 5231, len(master)
    out_domains = {}
    for r_ in sample:
        out_domains[r_["domain"]] = out_domains.get(r_["domain"], 0) + 1

    out = {"generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "workload": "headline RQ3b sample (analyze_final.stratified_sample, rng 42)",
           "workload_pairs_per_domain": out_domains, "sweeps": {}}
    embs = {}
    for enc in ENCODERS:
        print(f"embedding {enc} ...", flush=True)
        embs[enc] = embed_texts([items[i] for i in master], enc)
    S = {enc: embs[enc] @ embs[enc].T for enc in ENCODERS}
    k_master = [keys[i] for i in master]
    ORD = 50

    def orders_for(n, num=ORD):
        return [rng.permutation(n) for _ in range(num)]

    # --- 7a: OS vs workload size (bge-m3, tau .90) ---
    sizes = [100, 500, 1000, 2500, 5231]
    sw = []
    for N in sizes:
        sub = S["BAAI/bge-m3"][:N, :N]
        r = simulate(sub, k_master[:N], 0.90, ORD, rng, arrival=orders_for(N))
        r["N"] = N; sw.append(r)
        print("size", N, r, flush=True)
    out["sweeps"]["size"] = sw

    # --- 7b: OS vs tau grid (3 encoders, N=2500) ---
    taus = [round(x, 2) for x in np.arange(0.80, 0.981, 0.02)]
    N = 2500
    sw = {}
    for enc, name in ENCODERS.items():
        sub = S[enc][:N, :N]
        rows = []
        ords = orders_for(N)
        for tau in taus:
            r = simulate(sub, k_master[:N], tau, ORD, rng, arrival=ords)
            r["tau"] = tau; rows.append(r)
        sw[name] = rows
        print("tau grid done:", name, flush=True)
    out["sweeps"]["tau"] = sw

    # --- 7c: OS vs Zipf skew (bge-m3, N unique=1000, 5000 arrivals) ---
    Nu, draws = 1000, 5000
    sub = S["BAAI/bge-m3"][:Nu, :Nu]
    sw = []
    for alpha in (0.0, 0.5, 1.0, 1.5):
        if alpha == 0:
            probs = np.ones(Nu) / Nu
        else:
            w = 1.0 / np.arange(1, Nu + 1) ** alpha
            probs = w / w.sum()
        arr = [rng.choice(Nu, size=draws, p=probs) for _ in range(ORD)]
        r = simulate(sub, k_master[:Nu], 0.90, ORD, rng, arrival=arr)
        r["alpha"] = alpha; sw.append(r)
        print("zipf", alpha, r, flush=True)
    out["sweeps"]["zipf"] = sw

    # --- 7d: OS vs eviction policy/capacity (bge-m3, N=2500, tau .90) ---
    N = 2500
    sub = S["BAAI/bge-m3"][:N, :N]
    ords = orders_for(N)
    sw = [dict(simulate(sub, k_master[:N], 0.90, ORD, rng, arrival=ords),
               policy="unbounded", capacity=None)]
    for pol in ("fifo", "lru"):
        for cap in (100, 500, 2000):
            r = simulate(sub, k_master[:N], 0.90, ORD, rng, policy=pol,
                         capacity=cap, arrival=ords)
            r["policy"] = pol; r["capacity"] = cap; sw.append(r)
            print("evict", pol, cap, r, flush=True)
    out["sweeps"]["eviction"] = sw
    (REPO / "results" / "order_systematic.json").write_text(
        json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print("order_systematic.json written", flush=True)

    # Architectures: order sensitivity of A/B/D under their Table 1 decision rules is
    # simulated by scripts/order_architectures.py (results/architectures.json); their
    # error rates come from scripts/rq5_heldout.py (results/rq5_heldout.json).
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
