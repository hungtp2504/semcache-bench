#!/usr/bin/env python3
"""Reference points for the C4 test (held-out, same folds and band as rq5_heldout.py).

The C4 statistic is the relative reduction of false hits (FH) against threshold-only,
per axis group. How large that reduction can be depends on how a group's expected-MISS
pairs sit relative to the danger band, not only on the verifier. This script scores,
with the held-out protocol of rq5_heldout.py (primary fold assignment):
  oracle  a perfect in-band verifier (serves exactly the expected-HIT pairs in the
          band; tier-1 rule outside it) -- the largest reduction any band-limited
          verifier can reach in each group
and reports, per group, the share of threshold-only false hits that lie in the band.
Outputs results/c4_reference.json.
"""
import json
from pathlib import Path

import numpy as np
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rq5_heldout import (GROUP, HALF_BAND, best_tau, cached, ids_digest, load_recs, seed_folds,
                         tier1_sims)

REPO = Path(__file__).resolve().parents[1]


def main() -> int:
    recs = load_recs()
    sims = cached("bge_m3_sims", ids_digest(recs), lambda: tier1_sims(recs))
    y = np.array([r["expected_label"] == "HIT" for r in recs])
    grp = np.array([GROUP[r["axis"]] for r in recs])
    split = json.loads((REPO / "results" / "rq5_heldout.json").read_text())["protocol"]["split_seed"]
    fold = seed_folds(recs, 5, split)
    a_pred = np.zeros(len(recs), dtype=bool)
    o_pred = np.zeros(len(recs), dtype=bool)
    band = np.zeros(len(recs), dtype=bool)
    for k in range(5):
        te, tr = fold == k, fold != k
        tau = best_tau(sims[tr], y[tr])
        lo, hi = tau - HALF_BAND, tau + HALF_BAND
        b = (sims >= lo) & (sims <= hi)
        a_pred[te] = sims[te] > tau
        o_pred[te] = np.where(b[te], y[te], sims[te] > hi)
        band[te] = b[te]
    out = {"split_seed": split}
    for g in ("slope", "cliff"):
        m = (grp == g) & ~y
        fa, fo = a_pred[m].mean(), o_pred[m].mean()
        out[g] = {"fh_threshold": float(fa), "fh_oracle": float(fo),
                  "oracle_rel_reduction": float((fa - fo) / fa),
                  "share_of_threshold_fh_in_band": float((a_pred & band)[m].sum() / a_pred[m].sum())}
    (REPO / "results" / "c4_reference.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
