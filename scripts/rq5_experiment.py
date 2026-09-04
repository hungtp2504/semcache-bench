#!/usr/bin/env python3
"""RQ5 — second-tier verification, the C4 test (PLAN §15 Month-6, paper §6.5).

Tier-1: bge-m3 similarity threshold. Four configurations:
  1) threshold-only baseline (sweep tau)
  2) + cross-encoder verifier (bge-reranker-v2-m3) in the danger band
  3) + LLM verifier (Haiku) in the danger band  -> this script only EMITS the
     band pairs to data/rq5_band_pairs.jsonl for the E stage (quota needed)
  4) per-domain adaptive threshold (tau* chosen on a held-out split per domain)

For each config: false-hit rate, false-miss rate, and PER-AXIS-GROUP false-hit
reduction (cliff vs slope) — the pre-registered C4 asymmetry test.
Also RQ4: utility U(tau) and tau*(rho) per domain, rho in [1,1000].

Local only. Outputs results/rq5_rq4.json + the E-stage input file.
"""
import json
import sys
import datetime as dt
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from embed_utils import embed_texts

REPO = Path(__file__).resolve().parents[1]
TIER1 = "BAAI/bge-m3"
CROSS = "BAAI/bge-reranker-v2-m3"
GROUP = {"N1": "slope", "N2": "slope", "N3": "cliff", "N4": "cliff",
         "N5": "cliff", "N6": "cliff", "P1": "inv", "P2": "inv", "P3": "inv"}


def load():
    recs = []
    for ln in (REPO / "data" / "05_final.jsonl").read_text(encoding="utf-8").splitlines():
        if ln.strip():
            recs.append(json.loads(ln))
    return recs


def rates(pred_hit, y_hit, groups):
    """false-hit rate on MISS pairs (overall + per group) and miss rate on HIT pairs."""
    y = np.asarray(y_hit); p = np.asarray(pred_hit)
    out = {"false_hit": float(p[~y].mean()) if (~y).any() else 0.0,
           "false_miss": float((~p[y]).mean()) if y.any() else 0.0}
    for g in ("slope", "cliff"):
        m = np.array([gr == g for gr in groups]) & ~y
        out[f"false_hit_{g}"] = float(p[m].mean()) if m.any() else 0.0
    return out


def main() -> int:
    recs = load()
    n = len(recs)
    print(f"pairs: {n}", flush=True)
    y_hit = np.array([r["expected_label"] == "HIT" for r in recs])
    groups = [GROUP[r["axis"]] for r in recs]
    domains = np.array([r["domain"] for r in recs])

    # tier-1 similarities
    print("embedding tier-1 (bge-m3)...", flush=True)
    E = embed_texts([r["seed_question"] for r in recs] + [r["variation"] for r in recs], TIER1)
    sims = np.einsum("ij,ij->i", E[:n], E[n:])

    taus = np.round(np.arange(0.70, 0.981, 0.01), 3)
    results = {"generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
               "tier1": TIER1, "cross": CROSS, "n_pairs": n, "configs": {}}

    # --- config 1: threshold only
    c1 = {str(t): rates(sims > t, y_hit, groups) for t in taus}
    results["configs"]["threshold_only"] = c1
    best_ba_tau = max(taus, key=lambda t: ((sims > t)[y_hit].mean() + (~(sims > t))[~y_hit].mean()) / 2)
    print(f"config1 best-BA tau={best_ba_tau}: {c1[str(best_ba_tau)]}", flush=True)

    # danger band around the operating point: serve >hi, miss <lo, verify in between
    lo, hi = float(best_ba_tau) - 0.06, float(best_ba_tau) + 0.06
    band = (sims >= lo) & (sims <= hi)
    print(f"danger band [{lo:.2f},{hi:.2f}]: {band.sum()} pairs ({band.mean()*100:.1f}%)", flush=True)

    # --- config 2: + cross-encoder in band
    print("cross-encoder scoring band pairs...", flush=True)
    from sentence_transformers import CrossEncoder
    import torch
    ce = CrossEncoder(CROSS, device="mps" if torch.backends.mps.is_available() else "cpu")
    idx = np.flatnonzero(band)
    ce_scores = np.zeros(n)
    pairs = [(recs[i]["seed_question"], recs[i]["variation"]) for i in idx]
    if pairs:
        ce_scores[idx] = ce.predict(pairs, batch_size=64, show_progress_bar=True)
    # CE decision threshold: best BA on the band itself (reported; sweep included)
    band_y = y_hit[idx]
    cands = np.quantile(ce_scores[idx], np.linspace(0.05, 0.95, 19)) if len(idx) else [0]
    best_ce = max(cands, key=lambda t: ((ce_scores[idx] > t)[band_y].mean()
                                        + (~(ce_scores[idx] > t))[~band_y].mean()) / 2)
    pred2 = np.where(band, ce_scores > best_ce, sims > hi)
    results["configs"]["cross_encoder"] = {
        "band": [lo, hi], "ce_tau": float(best_ce),
        "rates": rates(pred2, y_hit, groups),
        "band_share": float(band.mean()),
    }
    print(f"config2: {results['configs']['cross_encoder']['rates']}", flush=True)

    # --- config 4: per-domain adaptive tau (split-half: even idx tune, odd eval)
    even = np.arange(n) % 2 == 0
    pred4 = np.zeros(n, dtype=bool)
    dom_taus = {}
    for d in sorted(set(domains)):
        md = domains == d
        tune = md & even
        t_star = max(taus, key=lambda t: ((sims[tune] > t)[y_hit[tune]].mean()
                                          + (~(sims[tune] > t))[~y_hit[tune]].mean()) / 2) if tune.any() else best_ba_tau
        dom_taus[d] = float(t_star)
        pred4[md] = sims[md] > t_star
    ev = ~even
    results["configs"]["adaptive_domain"] = {
        "domain_taus": dom_taus,
        "rates_evalhalf": rates(pred4[ev], y_hit[ev], [g for g, e in zip(groups, ev) if e]),
    }
    print(f"config4 taus: {dom_taus}", flush=True)

    # --- emit band pairs for config 3 (Haiku E stage)
    with open(REPO / "data" / "rq5_band_pairs.jsonl", "w", encoding="utf-8") as f:
        for i in idx:
            r = recs[i]
            f.write(json.dumps({"pair_id": r["id"], "cached_question": r["seed_question"],
                                "cached_answer": r["answer"], "new_query": r["variation"]},
                               ensure_ascii=False) + "\n")
    print(f"emitted {len(idx)} band pairs for E-stage (config 3)", flush=True)

    # --- RQ4: tau*(rho) per domain
    rq4 = {}
    rhos = np.unique(np.round(np.logspace(0, 3, 25)))
    for d in sorted(set(domains)):
        md = domains == d
        curve = []
        for rho in rhos:
            # U(tau) with C_llm=1: correct-hit saves 1, false-hit costs rho, false-miss costs 1
            best_t, best_u = None, -1e18
            for t in taus:
                p = sims[md] > t
                y = y_hit[md]
                u = (p & y).mean() - rho * (p & ~y).mean() - (~p & y).mean()
                if u > best_u:
                    best_u, best_t = u, float(t)
            curve.append({"rho": float(rho), "tau_star": best_t, "u": float(best_u)})
        rq4[d] = curve
    results["rq4_tau_star"] = rq4

    out = REPO / "results" / "rq5_rq4.json"
    out.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
