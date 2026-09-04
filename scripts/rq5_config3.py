#!/usr/bin/env python3
"""RQ5 config-3: fold Haiku SERVE/REGENERATE decisions into the four-config table.

Joins data/06_verify_decisions.jsonl onto the band pairs; computes false-hit /
false-miss overall and per axis group; appends to results/rq5_rq4.json.
"""
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
GROUP = {"N1": "slope", "N2": "slope", "N3": "cliff", "N4": "cliff",
         "N5": "cliff", "N6": "cliff", "P1": "inv", "P2": "inv", "P3": "inv"}


def main() -> int:
    dec = {}
    for ln in (REPO / "data" / "06_verify_decisions.jsonl").read_text(encoding="utf-8").splitlines():
        if ln.strip():
            j = json.loads(ln)
            dec[j["pair_id"]] = j["decision"]
    final = {r["id"]: r for ln in (REPO / "data" / "05_final.jsonl").read_text(encoding="utf-8").splitlines()
             if ln.strip() for r in [json.loads(ln)]}
    res = json.loads((REPO / "results" / "rq5_rq4.json").read_text(encoding="utf-8"))
    lo, hi = res["configs"]["cross_encoder"]["band"]

    joined = [(final[pid], d) for pid, d in dec.items() if pid in final]
    print(f"decisions joined: {len(joined)}/{len(dec)}")
    y_hit = np.array([r["expected_label"] == "HIT" for r, _ in joined])
    serve = np.array([d == "SERVE" for _, d in joined])
    groups = [GROUP[r["axis"]] for r, _ in joined]

    out = {"n_band_decided": len(joined),
           "band_false_hit": float(serve[~y_hit].mean()),
           "band_false_miss": float((~serve[y_hit]).mean())}
    for g in ("slope", "cliff"):
        m = np.array([x == g for x in groups]) & ~y_hit
        out[f"band_false_hit_{g}"] = float(serve[m].mean()) if m.any() else None
    # compare with tier-1-alone inside the band: baseline in-band prediction = sim>tau*
    # (band pairs are ambiguous by construction: tier-1 alone at best-BA tau serves ~half)
    res["configs"]["llm_verifier"] = out
    (REPO / "results" / "rq5_rq4.json").write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
