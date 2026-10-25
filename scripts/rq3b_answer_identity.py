#!/usr/bin/env python3
"""RQ3b revision (IEEE Access R1 concern 4): how the constructed answer identity
affects the order-dependence and wrong-answer rates.

The published simulation (analyze_pilot.rq3b) keys every query by a constructed
answer identity: a seed and its HIT variants share the seed's key, each MISS
variant has its own key. A served entry is wrong iff keys differ, so a serve
across two different seeds is always counted wrong. This script reruns that
simulation on the identical 5,231-query workload and classifies every wrong
serve by what its "wrong" verdict rests on:

  within_family    query and served entry derive from the same seed: the verdict
                   rests on the construction-derived HIT/MISS label (audited
                   against three blind annotators, 98.5% agreement).
  cross_verified   different seeds, both with a recorded reference answer (seed or
                   HIT variant): the two stored answers are compared directly
                   (normalized exact match = same answer, i.e. not actually wrong).
  cross_unverified different seeds and at least one side is a MISS variant, whose
                   answer was never generated: the verdict rests on the
                   assumption that distinct seeds/variants have distinct answers.

It also reports two bounds and one re-keyed rerun:
  lower bound  count only within-family + verified-different cross-seed serves
               as wrong (every unverifiable cross-seed serve assumed correct);
  upper bound  the published constructed-identity count;
  answer-text  re-key seeds/HIT variants by their normalized answer text, so seeds
               with literally identical answers share a key; recompute OS + wrong.

Cache decisions do not depend on the keys, so one simulation per tau yields all
variants. Outputs results/rq3b_answer_identity.json.
"""
import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_final import load_final, stratified_sample
from embed_utils import embed_texts

REPO = Path(__file__).resolve().parents[1]
CACHE = REPO / ".cache" / "rq3b"


def norm(t):
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", t.lower())).strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--taus", nargs="+", type=float, default=[0.85, 0.90, 0.95])
    ap.add_argument("--orders", type=int, default=500)
    ap.add_argument("--sim-seed", type=int, default=20261025)
    a = ap.parse_args()

    recs = load_final()
    sample = stratified_sample(recs, 5000, np.random.default_rng(42))   # published workload
    doc_of = {}
    for ln in (REPO / "data" / "02_seeds.jsonl").read_text(encoding="utf-8").splitlines():
        if ln.strip():
            j = json.loads(ln)
            doc_of[j["seed_id"]] = j["doc_id"]

    # items exactly as analyze_pilot.rq3b builds them
    items, keys, fam, kind, ans = [], [], [], [], []
    seen = set()
    for r in sample:
        if r["seed_id"] not in seen:
            seen.add(r["seed_id"])
            items.append(r["seed_question"]); keys.append(r["seed_id"])
            fam.append(r["seed_id"]); kind.append("seed"); ans.append(norm(r["answer"]))
        items.append(r["variation"])
        hit = r["expected_label"] == "HIT"
        keys.append(r["seed_id"] if hit else r["id"])
        fam.append(r["seed_id"]); kind.append("HIT" if hit else "MISS")
        ans.append(norm(r["answer"]) if hit else None)
    n = len(items)
    print(f"workload: {n} queries from {len(sample)} pairs, {len(seen)} seeds", flush=True)

    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / f"bge_m3_workload_{n}.npy"
    if f.exists():
        E = np.load(f)
    else:
        E = embed_texts(items, "BAAI/bge-m3"); np.save(f, E)
    S = E @ E.T

    key_id = {k: i for i, k in enumerate(dict.fromkeys(keys))}
    K = np.array([key_id[k] for k in keys])
    # answer-text keys: seed/HIT items keyed by normalized answer; MISS items stay unique
    akey_map = {}
    AK = np.array([akey_map.setdefault(("A", ans[i]) if ans[i] is not None else ("M", keys[i]),
                                       len(akey_map)) for i in range(n)])
    fam_arr = np.array(fam)
    verifiable = np.array([k != "MISS" for k in kind])
    same_doc = lambda i, j: doc_of.get(fam[i]) == doc_of.get(fam[j])

    rng = np.random.default_rng(a.sim_seed)
    out = {"generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "script": "scripts/rq3b_answer_identity.py", "n_queries": n, "n_pairs": len(sample),
           "n_seeds": len(seen), "orders": a.orders, "sim_seed": a.sim_seed,
           "seed_answer_texts_shared_by_2plus_seeds": int(
               (np.unique(AK[np.array(kind) == "seed"], return_counts=True)[1] > 1).sum()),
           "taus": {}}
    for tau in a.taus:
        served_c = [set() for _ in range(n)]
        served_a = [set() for _ in range(n)]
        cnt = dict(serves=0, wrong=0, within_family=0, cross_verified_diff=0,
                   cross_verified_same=0, cross_unverified=0, cross_same_doc=0,
                   wrong_answer_text=0)
        for _ in range(a.orders):
            order = rng.permutation(n)
            stored = np.empty(n, dtype=np.int64); m = 0
            for i in order:
                if m:
                    st = stored[:m]
                    sims = S[i, st]
                    b = int(np.argmax(sims))
                    if sims[b] > tau:
                        j = int(st[b])
                        cnt["serves"] += 1
                        served_c[i].add(K[j]); served_a[i].add(AK[j])
                        if AK[j] != AK[i]:
                            cnt["wrong_answer_text"] += 1
                        if K[j] != K[i]:
                            cnt["wrong"] += 1
                            if fam_arr[i] == fam_arr[j]:
                                cnt["within_family"] += 1
                            else:
                                if same_doc(i, j):
                                    cnt["cross_same_doc"] += 1
                                if verifiable[i] and verifiable[j]:
                                    if ans[i] == ans[j]:
                                        cnt["cross_verified_same"] += 1
                                    else:
                                        cnt["cross_verified_diff"] += 1
                                else:
                                    cnt["cross_unverified"] += 1
                        continue
                stored[m] = i; m += 1
                served_c[i].add(K[i]); served_a[i].add(AK[i])
        denom = n * a.orders
        w = cnt["wrong"]
        res = {
            "order_sensitivity": sum(1 for s in served_c if len(s) > 1) / n,
            "wrong_rate": w / denom,
            "hit_rate": cnt["serves"] / denom,
            "wrong_shares": {k: (cnt[k] / w if w else 0.0) for k in
                             ("within_family", "cross_verified_diff", "cross_verified_same",
                              "cross_unverified", "cross_same_doc")},
            "wrong_rate_lower_bound": (cnt["within_family"] + cnt["cross_verified_diff"]) / denom,
            "wrong_rate_upper_bound": w / denom,
            "answer_text_keys": {"order_sensitivity": sum(1 for s in served_a if len(s) > 1) / n,
                                 "wrong_rate": cnt["wrong_answer_text"] / denom},
            "counts": cnt,
        }
        out["taus"][str(tau)] = res
        print(f"tau={tau}: OS {res['order_sensitivity']:.1%}  wrong {res['wrong_rate']:.2%} "
              f"[lower {res['wrong_rate_lower_bound']:.2%}]  shares "
              + " ".join(f"{k}={v:.1%}" for k, v in res["wrong_shares"].items())
              + f"  | answer-text keys: OS {res['answer_text_keys']['order_sensitivity']:.1%} "
                f"wrong {res['answer_text_keys']['wrong_rate']:.2%}", flush=True)
        (REPO / "results" / "rq3b_answer_identity.json").write_text(
            json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print("wrote results/rq3b_answer_identity.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
