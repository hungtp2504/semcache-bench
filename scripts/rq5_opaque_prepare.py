#!/usr/bin/env python3
"""Inputs for the opaque-identifier rerun of the LLM verifier (RQ5, configuration C).

The stage-E verifier originally received pairs with their benchmark identifiers
(e.g. d1_s0001_N1_v1, which encode the axis) in seed-grouped, axis-ordered batches.
This rerun removes that information: every pair gets a random opaque identifier and
all pairs are shuffled across seeds, axes and domains before batching. Prompt and
model are unchanged (prompts/E_verify.md v1.0, claude-haiku-4-5-20251001).

Pairs:
  missing  every held-out in-band pair without a recorded decision under the primary
           fold assignment of rq5_heldout.py (493 pairs)
  sample   a stratified random sample of 100 originally decided pairs per axis
           (900 pairs) to compare opaque and original decisions
Writes data/rq5_opaque_input.jsonl (what the model sees) and
data/rq5_opaque_key.jsonl (opaque id -> benchmark id, role); never shown to the model.
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rq5_heldout import HALF_BAND, best_tau, cached, ids_digest, load_recs, seed_folds, tier1_sims

REPO = Path(__file__).resolve().parents[1]
SEED, PER_AXIS = 20261031, 100


def main() -> int:
    recs = load_recs()
    sims = cached("bge_m3_sims", ids_digest(recs), lambda: tier1_sims(recs))
    y = np.array([r["expected_label"] == "HIT" for r in recs])
    decided = set()
    for ln in (REPO / "data" / "06_verify_decisions.jsonl").read_text(encoding="utf-8").splitlines():
        if ln.strip():
            decided.add(json.loads(ln)["pair_id"])
    split = json.loads((REPO / "results" / "rq5_heldout.json").read_text())["protocol"]["split_seed"]
    fold = seed_folds(recs, 5, split)
    missing = []
    for k in range(5):
        te, tr = fold == k, fold != k
        tau = best_tau(sims[tr], y[tr])
        band = (sims >= tau - HALF_BAND) & (sims <= tau + HALF_BAND)
        missing += [i for i in np.where(te & band)[0] if recs[i]["id"] not in decided]
    rng = np.random.default_rng(SEED)
    by_axis = {}
    for i, r in enumerate(recs):
        if r["id"] in decided:
            by_axis.setdefault(r["axis"], []).append(i)
    sample = []
    for ax in sorted(by_axis):
        sample += list(rng.choice(by_axis[ax], size=PER_AXIS, replace=False))
    rows = [(i, "missing") for i in missing] + [(int(i), "sample") for i in sample]
    order = rng.permutation(len(rows))
    ids = set()
    with open(REPO / "data" / "rq5_opaque_input.jsonl", "w", encoding="utf-8") as fi, \
         open(REPO / "data" / "rq5_opaque_key.jsonl", "w", encoding="utf-8") as fk:
        for o in order:
            i, role = rows[o]
            r = recs[i]
            oid = "q" + "".join(rng.choice(list("0123456789abcdef"), size=10))
            assert oid not in ids
            ids.add(oid)
            fi.write(json.dumps({"pair_id": oid, "cached_question": r["seed_question"],
                                 "cached_answer": r["answer"], "new_query": r["variation"]},
                                ensure_ascii=False) + "\n")
            fk.write(json.dumps({"opaque_id": oid, "pair_id": r["id"], "role": role}) + "\n")
    print(f"missing {len(missing)}, sample {len(sample)}, total {len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
