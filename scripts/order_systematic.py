#!/usr/bin/env python3
"""Systematic characterization of order-dependent cache behavior (review point 7)
and architecture isolation A-E (review point 6).

Order sensitivity OS = share of queries whose serving source varies across random
arrival orders. Sweeps: workload size N, threshold tau, Zipf skew alpha, encoder,
eviction policy (unbounded / FIFO-capacity / LRU-capacity).

Architectures on the frozen pair benchmark:
  A threshold-only            serve iff sim > tau
  B + cross-encoder verifier  in band -> CE decides
  C + LLM verifier            in band -> Haiku decides (from measured decisions)
  D + discrete-slot guard     serve iff sim > tau AND numeric/acronym slots match
  E learned decision model    logistic model on interpretable features, seed-split

Outputs results/order_systematic.json and results/architectures.json.
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
    items, keys = build_workload(recs, rng)
    # master stratified sample of 5,231 (same as final analysis: first N in seed order)
    idx_all = np.arange(len(items))
    master = idx_all[:5231]

    out = {"generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "sweeps": {}}
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

    # ================= Architectures A-E on the pair benchmark =================
    print("architectures...", flush=True)
    n = len(recs)
    E1 = embed_texts([r["seed_question"] for r in recs] + [r["variation"] for r in recs],
                     "BAAI/bge-m3")
    sims = np.einsum("ij,ij->i", E1[:n], E1[n:])
    y = np.array([r["expected_label"] == "HIT" for r in recs])
    groups = [GROUP[r["axis"]] for r in recs]
    TAU = 0.89

    def slots(q):
        nums = set(re.findall(r"\d+(?:[.,/]\d+)*", q))
        caps = set(re.findall(r"\b[A-ZĐ]{2,}\b", q))
        return nums, caps

    def rates(pred):
        d = {"false_hit": float(pred[~y].mean()), "false_miss": float((~pred[y]).mean()),
             "hit_rate_on_hits": float(pred[y].mean())}
        for g in ("slope", "cliff"):
            m = np.array([x == g for x in groups]) & ~y
            d[f"false_hit_{g}"] = float(pred[m].mean())
        return d

    arch = {}
    arch["A_threshold"] = rates(sims > TAU)
    # D: discrete-slot guard
    slot_ok = np.array([slots(r["seed_question"])[0] == slots(r["variation"])[0] and
                        slots(r["seed_question"])[1] == slots(r["variation"])[1]
                        for r in recs])
    arch["D_slot_guard"] = rates((sims > TAU) & slot_ok)
    # E: learned decision model (interpretable features, split by seed)
    from sklearn.linear_model import LogisticRegression
    def feats(r, s):
        q1, q2 = r["seed_question"], r["variation"]
        w1, w2 = set(q1.lower().split()), set(q2.lower().split())
        n1, c1 = slots(q1); n2, c2 = slots(q2)
        return [s, len(w1 & w2) / max(1, len(w1 | w2)),
                abs(len(q1) - len(q2)) / max(len(q1), len(q2)),
                1.0 * (n1 == n2), 1.0 * (c1 == c2)]
    X = np.array([feats(r, s) for r, s in zip(recs, sims)])
    seeds = np.array([r["seed_id"] for r in recs])
    useeds = np.unique(seeds); rng.shuffle(useeds)
    tr = np.isin(seeds, useeds[:len(useeds) // 2]); te = ~tr
    clf = LogisticRegression(max_iter=2000).fit(X[tr], y[tr])
    pred_e = np.zeros(n, dtype=bool); pred_e[te] = clf.predict(X[te]).astype(bool)
    d = {"false_hit": float(pred_e[te & ~y].mean()), "false_miss": float((~pred_e)[te & y].mean())}
    for g in ("slope", "cliff"):
        m = np.array([x == g for x in groups]) & ~y & te
        d[f"false_hit_{g}"] = float(pred_e[m].mean())
    d["coef"] = dict(zip(["sim", "jaccard", "lendiff", "num_match", "cap_match"],
                         map(float, clf.coef_[0])))
    arch["E_learned"] = d

    # B/C from existing results (rq5_rq4.json) merged for the unified table
    r5 = json.loads((REPO / "results" / "rq5_rq4.json").read_text())
    arch["B_cross_encoder"] = r5["configs"]["cross_encoder"]["rates"]
    arch["C_llm_verifier"] = r5["configs"]["llm_verifier"]

    # instability per architecture (N=1000 subsample, 50 orders):
    Nu = 1000
    subS = S["BAAI/bge-m3"][:Nu, :Nu]
    ords = orders_for(Nu)
    inst = {"A": simulate(subS, k_master[:Nu], 0.90, ORD, rng, arrival=ords)["OS"]}
    # D in simulation: guard on slots of the two queries
    texts_sub = [items[i] for i in master[:Nu]]
    slot_list = [slots(t) for t in texts_sub]
    def d_decide(i, j):
        return slot_list[i][0] == slot_list[j][0] and slot_list[i][1] == slot_list[j][1]
    inst["D"] = simulate(subS, k_master[:Nu], 0.90, ORD, rng, arrival=ords,
                         band=(-1.0, 2.0), band_decide=d_decide)["OS"]
    # B in simulation: CE on in-band pairs (precompute)
    import torch
    from sentence_transformers import CrossEncoder
    ce = CrossEncoder("BAAI/bge-reranker-v2-m3",
                      device="mps" if torch.backends.mps.is_available() else "cpu")
    lo, hi = 0.83, 0.95
    pairs_idx = [(i, j) for i in range(Nu) for j in range(i)
                 if lo <= subS[i, j] <= hi]
    print(f"CE precompute for {len(pairs_idx)} in-band pairs", flush=True)
    ce_scores = {}
    B = 2048
    for k0 in range(0, len(pairs_idx), B):
        chunk = pairs_idx[k0:k0 + B]
        scores = ce.predict([(texts_sub[i], texts_sub[j]) for i, j in chunk],
                            batch_size=128)
        for (i, j), sc in zip(chunk, scores):
            ce_scores[(i, j)] = float(sc); ce_scores[(j, i)] = float(sc)
    ce_tau = r5["configs"]["cross_encoder"]["ce_tau"]
    def b_decide(i, j):
        return ce_scores.get((i, j), 1e9) > ce_tau
    inst["B"] = simulate(subS, k_master[:Nu], 0.90, ORD, rng, arrival=ords,
                         band=(lo, hi), band_decide=b_decide)["OS"]
    arch["instability_N1000_tau090"] = inst
    arch["note"] = ("C (LLM) instability not simulated: requires a live LLM in the "
                    "arrival loop; its pair-level decisions are in config C rates.")
    (REPO / "results" / "architectures.json").write_text(
        json.dumps(arch, indent=2) + "\n", encoding="utf-8")
    print("architectures.json written", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
