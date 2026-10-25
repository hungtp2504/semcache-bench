#!/usr/bin/env python3
"""RQ5 revision (IEEE Access R1 concerns 1-3): held-out, same-denominator evaluation.

Every configuration is tuned only on training folds and scored on held-out pairs,
with one denominator for all configurations:

  * 5-fold cross-validation grouped by seed (all pairs of a seed share a fold) and
    stratified by domain, so no seed's paraphrases or edits leak across the split.
  * Per fold, on the TRAINING folds only: tau*_BA (A), danger band tau*_BA +/- 0.06,
    the cross-encoder threshold (B), the per-domain thresholds (adaptive), and the
    logistic model (E). D reuses fold tau*_BA. C (Haiku) has no tunable parameter;
    its recorded SERVE/REGENERATE decisions are reused unchanged.
  * Out-of-fold predictions cover every pair exactly once, so FH/FM/hit rate are
    computed over the full benchmark for every configuration (FH over all
    expected-MISS pairs, FM over all expected-HIT pairs, serve rate over all pairs).
  * C over the full benchmark: Haiku decides in-band pairs, the tier-1 rule
    (serve iff sim > band top) decides the rest -- the same rule B uses outside the
    band. In-band pairs without a recorded decision fall back to REGENERATE
    (counted and reported).
  * The pre-revision in-sample protocol (tune and score on all pairs) is rerun as
    `in_sample` -- it must reproduce the submitted 27.5% / 18.4% -- and is reported
    as an optimistic best-achievable bound.
  * 95% CIs: percentile cluster bootstrap over seeds.

Outputs results/rq5_heldout.json. Similarity and cross-encoder scores are cached in
.cache/rq5/ (git-ignored). Local only; no LLM calls.
"""
import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from embed_utils import embed_texts

REPO = Path(__file__).resolve().parents[1]
CACHE = REPO / ".cache" / "rq5"
TIER1 = "BAAI/bge-m3"
CROSS = "BAAI/bge-reranker-v2-m3"
GROUP = {"N1": "slope", "N2": "slope", "N3": "cliff", "N4": "cliff",
         "N5": "cliff", "N6": "cliff", "P1": "inv", "P2": "inv", "P3": "inv"}
TAUS = np.round(np.arange(0.70, 0.981, 0.01), 3)
HALF_BAND = 0.06
CONFIGS = ["A_threshold", "B_cross_encoder", "C_llm_verifier", "D_slot_guard",
           "E_learned", "adaptive_domain", "C_llm_tier1_fallback"]


def load_recs():
    return [json.loads(l) for l in (REPO / "data" / "05_final.jsonl")
            .read_text(encoding="utf-8").splitlines() if l.strip()]


def ids_digest(recs):
    return hashlib.sha256("\n".join(r["id"] for r in recs).encode()).hexdigest()[:16]


def cached(name, digest, compute):
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / f"{name}_{digest}.npy"
    if f.exists():
        return np.load(f)
    arr = compute()
    np.save(f, arr)
    return arr


def tier1_sims(recs):
    n = len(recs)
    E = embed_texts([r["seed_question"] for r in recs] + [r["variation"] for r in recs], TIER1)
    return np.einsum("ij,ij->i", E[:n], E[n:]).astype(np.float64)


def ce_scores(recs):
    import torch
    from sentence_transformers import CrossEncoder
    ce = CrossEncoder(CROSS, device="mps" if torch.backends.mps.is_available() else "cpu")
    pairs = [(r["seed_question"], r["variation"]) for r in recs]
    return np.asarray(ce.predict(pairs, batch_size=64, show_progress_bar=True), dtype=np.float64)


def slots(q):
    nums = set(re.findall(r"\d+(?:[.,/]\d+)*", q))
    caps = set(re.findall(r"\b[A-ZĐ]{2,}\b", q))
    return nums, caps


def e_features(recs, sims):
    X = []
    for r, s in zip(recs, sims):
        q1, q2 = r["seed_question"], r["variation"]
        w1, w2 = set(q1.lower().split()), set(q2.lower().split())
        n1, c1 = slots(q1); n2, c2 = slots(q2)
        X.append([s, len(w1 & w2) / max(1, len(w1 | w2)),
                  abs(len(q1) - len(q2)) / max(len(q1), len(q2)),
                  1.0 * (n1 == n2), 1.0 * (c1 == c2)])
    return np.array(X)


def ba(pred, y):
    return (pred[y].mean() + (~pred[~y]).mean()) / 2


def best_tau(sims, y):
    return float(max(TAUS, key=lambda t: ba(sims > t, y)))


def seed_folds(recs, k, seed):
    """Seed-grouped, domain-stratified fold id per pair."""
    rng = np.random.default_rng(seed)
    by_dom = {}
    for r in recs:
        by_dom.setdefault(r["domain"], set()).add(r["seed_id"])
    fold_of = {}
    for d in sorted(by_dom):
        us = np.array(sorted(by_dom[d]))
        rng.shuffle(us)
        for rank, s in enumerate(us):
            fold_of[s] = rank % k
    return np.array([fold_of[r["seed_id"]] for r in recs])


def fit_predict(tr, te, ctx):
    """Tune every configuration on `tr`, predict `te`. Returns preds, in-band mask, params."""
    sims, y, ce, llm, slot_ok, X, dom = (ctx[k] for k in
                                         ("sims", "y", "ce", "llm", "slot_ok", "X", "dom"))
    tau = best_tau(sims[tr], y[tr])
    lo, hi = tau - HALF_BAND, tau + HALF_BAND
    band = (sims >= lo) & (sims <= hi)

    trb = tr & band
    cands = np.quantile(ce[trb], np.linspace(0.05, 0.95, 19))
    t_ce = float(max(cands, key=lambda t: ba(ce[trb] > t, y[trb])))

    preds = {}
    preds["A_threshold"] = sims[te] > tau
    preds["B_cross_encoder"] = np.where(band[te], ce[te] > t_ce, sims[te] > hi)
    llm_te = llm[te]                       # 1 SERVE, 0 REGENERATE, -1 no decision
    in_band_te = band[te]
    undecided = int((in_band_te & (llm_te < 0)).sum())
    preds["C_llm_verifier"] = np.where(in_band_te, llm_te == 1, sims[te] > hi)
    # sensitivity: undecided in-band pairs fall back to the tier-1 decision (sim > tau)
    c_alt = np.where(llm_te >= 0, llm_te == 1, sims[te] > tau)
    preds["C_llm_tier1_fallback"] = np.where(in_band_te, c_alt, sims[te] > hi)
    preds["D_slot_guard"] = (sims[te] > tau) & slot_ok[te]

    from sklearn.linear_model import LogisticRegression
    clf = LogisticRegression(max_iter=2000).fit(X[tr], y[tr])
    preds["E_learned"] = clf.predict(X[te]).astype(bool)

    dom_tau = {}
    pa = np.zeros(int(te.sum()), dtype=bool)
    dte = dom[te]
    for d in sorted(set(dom)):
        m = tr & (dom == d)
        dom_tau[d] = best_tau(sims[m], y[m]) if m.any() else tau
        pa[dte == d] = sims[te][dte == d] > dom_tau[d]
    preds["adaptive_domain"] = pa

    params = {"tau_BA": tau, "band": [round(lo, 4), round(hi, 4)], "ce_tau": t_ce,
              "domain_taus": dom_tau, "band_share_test": float(in_band_te.mean()),
              "c_undecided_in_band": undecided,
              "e_coef": dict(zip(["sim", "jaccard", "lendiff", "num_match", "cap_match"],
                                 map(float, clf.coef_[0])))}
    return preds, in_band_te, params


# ---- metrics as count statistics, so the cluster bootstrap is a weighted sum ----
STATS = ["n", "n_miss", "n_hit", "fh", "fm", "served", "miss_slope", "fh_slope",
         "miss_cliff", "fh_cliff", "band_n_miss", "band_fh", "band_n_hit", "band_fm"]


def per_seed_counts(pred, band, y, grp, seed_idx, n_seeds):
    cols = {
        "n": np.ones_like(y, dtype=float), "n_miss": ~y, "n_hit": y,
        "fh": pred & ~y, "fm": ~pred & y, "served": pred,
        "miss_slope": ~y & (grp == "slope"), "fh_slope": pred & ~y & (grp == "slope"),
        "miss_cliff": ~y & (grp == "cliff"), "fh_cliff": pred & ~y & (grp == "cliff"),
        "band_n_miss": band & ~y, "band_fh": band & pred & ~y,
        "band_n_hit": band & y, "band_fm": band & ~pred & y,
    }
    M = np.zeros((n_seeds, len(STATS)))
    for k, s in enumerate(STATS):
        M[:, k] = np.bincount(seed_idx, weights=cols[s].astype(float), minlength=n_seeds)
    return M


def metrics_from(tot):
    t = dict(zip(STATS, tot))
    div = lambda a, b: float(t[a] / t[b]) if t[b] else float("nan")
    return {"false_hit": div("fh", "n_miss"), "false_miss": div("fm", "n_hit"),
            "serve_rate": div("served", "n"), "hit_rate_on_hits": 1 - div("fm", "n_hit"),
            "false_hit_slope": div("fh_slope", "miss_slope"),
            "false_hit_cliff": div("fh_cliff", "miss_cliff"),
            "band_false_hit": div("band_fh", "band_n_miss"),
            "band_false_miss": div("band_fm", "band_n_hit"),
            "served_wrong_share": div("fh", "served")}


def evaluate(oof, band, ctx, n_boot, rng):
    y, grp, seed_idx, n_seeds = ctx["y"], ctx["grp"], ctx["seed_idx"], ctx["n_seeds"]
    counts = {c: per_seed_counts(oof[c], band, y, grp, seed_idx, n_seeds) for c in CONFIGS}
    point = {c: metrics_from(counts[c].sum(0)) for c in CONFIGS}

    # cluster bootstrap over seeds: resample seeds with replacement
    W = np.stack([np.bincount(rng.integers(n_seeds, size=n_seeds), minlength=n_seeds)
                  for _ in range(n_boot)]).astype(float)
    boot = {c: W @ counts[c] for c in CONFIGS}            # (n_boot, n_stats)

    def ci(vals):
        v = np.asarray(vals, dtype=float)
        v = v[np.isfinite(v)]
        return [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))]

    out = {}
    for c in CONFIGS:
        reps = [metrics_from(row) for row in boot[c]]
        out[c] = {k: {"value": point[c][k], "ci95": ci([r[k] for r in reps])}
                  for k in point[c]}

    # C4: relative false-hit reduction vs A, per group, and the cliff-minus-slope gap
    c4 = {}
    for c in ("B_cross_encoder", "C_llm_verifier", "D_slot_guard"):
        def red(tA, tC, g):
            a = tA[STATS.index(f"fh_{g}")] / tA[STATS.index(f"miss_{g}")]
            b = tC[STATS.index(f"fh_{g}")] / tC[STATS.index(f"miss_{g}")]
            return (a - b) / a
        tA, tC = counts["A_threshold"].sum(0), counts[c].sum(0)
        pt = {g: red(tA, tC, g) for g in ("slope", "cliff")}
        reps = [{g: red(bA, bC, g) for g in ("slope", "cliff")}
                for bA, bC in zip(boot["A_threshold"], boot[c])]
        c4[c] = {
            "rel_reduction_slope": {"value": float(pt["slope"]), "ci95": ci([r["slope"] for r in reps])},
            "rel_reduction_cliff": {"value": float(pt["cliff"]), "ci95": ci([r["cliff"] for r in reps])},
            "cliff_minus_slope": {"value": float(pt["cliff"] - pt["slope"]),
                                  "ci95": ci([r["cliff"] - r["slope"] for r in reps]),
                                  "share_reps_positive": float(np.mean(
                                      [r["cliff"] > r["slope"] for r in reps]))},
        }
    return out, c4


def c_residual(pred, band, ctx):
    """Where C's remaining false hits sit: inside the verified band vs above it."""
    y, grp = ctx["y"], ctx["grp"]
    fh = pred & ~y
    out = {"n_false_hits": int(fh.sum()),
           "share_above_band": float((fh & ~band).sum() / fh.sum()) if fh.sum() else 0.0}
    for g in ("slope", "cliff"):
        m = fh & (grp == g)
        out[f"{g}_false_hits"] = int(m.sum())
        out[f"{g}_share_above_band"] = float((m & ~band).sum() / m.sum()) if m.sum() else 0.0
        # in-band relative reduction vs threshold-only is computed from band_false_hit metrics
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--split-seed", type=int, default=20261025)
    ap.add_argument("--boot", type=int, default=2000)
    a = ap.parse_args()

    recs = load_recs()
    n = len(recs)
    dig = ids_digest(recs)
    print(f"pairs: {n} (ids digest {dig})", flush=True)

    print("tier-1 similarities (bge-m3) ...", flush=True)
    sims = cached("bge_m3_sims", dig, lambda: tier1_sims(recs))
    print("cross-encoder scores (bge-reranker-v2-m3), all pairs ...", flush=True)
    ce = cached("ce_scores", dig, lambda: ce_scores(recs))

    dec = {}
    for ln in (REPO / "data" / "06_verify_decisions.jsonl").read_text(encoding="utf-8").splitlines():
        if ln.strip():
            j = json.loads(ln)
            dec[j["pair_id"]] = 1 if j["decision"] == "SERVE" else 0
    llm = np.array([dec.get(r["id"], -1) for r in recs])

    y = np.array([r["expected_label"] == "HIT" for r in recs])
    seeds = np.array([r["seed_id"] for r in recs])
    useeds, seed_idx = np.unique(seeds, return_inverse=True)
    ctx = {"sims": sims, "y": y, "ce": ce, "llm": llm,
           "slot_ok": np.array([slots(r["seed_question"]) == slots(r["variation"]) for r in recs]),
           "dom": np.array([r["domain"] for r in recs]),
           "grp": np.array([GROUP[r["axis"]] for r in recs]),
           "seed_idx": seed_idx, "n_seeds": len(useeds)}
    print("features for E ...", flush=True)
    ctx["X"] = e_features(recs, sims)

    rng = np.random.default_rng(a.split_seed)
    results = {"generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
               "script": "scripts/rq5_heldout.py", "n_pairs": n, "n_seeds": len(useeds),
               "ids_digest": dig, "tier1": TIER1, "cross": CROSS,
               "llm_decisions_recorded": int((llm >= 0).sum()),
               "protocol": {"folds": a.folds, "grouping": "seed", "stratify": "domain",
                            "split_seed": a.split_seed, "bootstrap": f"cluster by seed, {a.boot} reps",
                            "half_band": HALF_BAND, "tau_grid": [float(TAUS[0]), float(TAUS[-1]), 0.01]}}

    # --- held-out: out-of-fold predictions ---
    fold = seed_folds(recs, a.folds, a.split_seed)
    oof = {c: np.zeros(n, dtype=bool) for c in CONFIGS}
    oof_band = np.zeros(n, dtype=bool)
    fold_params = []
    for k in range(a.folds):
        te = fold == k
        tr = ~te
        preds, band_te, params = fit_predict(tr, te, ctx)
        for c in CONFIGS:
            oof[c][te] = preds[c]
        oof_band[te] = band_te
        params.update({"fold": k, "n_test": int(te.sum()), "n_test_seeds": int(len(set(seeds[te])))})
        fold_params.append(params)
        print(f"fold {k}: tau={params['tau_BA']} band={params['band']} ce_tau={params['ce_tau']:.4f} "
              f"undecided_in_band={params['c_undecided_in_band']}", flush=True)
    m_ho, c4_ho = evaluate(oof, oof_band, ctx, a.boot, rng)
    results["held_out"] = {"folds": fold_params, "metrics": m_ho, "c4": c4_ho,
                           "c_residual": c_residual(oof["C_llm_verifier"], oof_band, ctx)}

    # --- in-sample (pre-revision protocol): tune and score on all pairs ---
    allm = np.ones(n, dtype=bool)
    preds, band_all, params = fit_predict(allm, allm, ctx)
    m_in, c4_in = evaluate(preds, band_all, ctx, a.boot, rng)
    results["in_sample"] = {"params": params, "metrics": m_in, "c4": c4_in}

    out = REPO / "results" / "rq5_heldout.json"
    out.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out}", flush=True)

    def row(m, c):
        g = lambda k: m[c][k]["value"] * 100
        return (f"{c:18s} FH {g('false_hit'):5.1f}  FM {g('false_miss'):5.1f}  serve {g('serve_rate'):5.1f}  "
                f"FHs {g('false_hit_slope'):5.1f}  FHc {g('false_hit_cliff'):5.1f}  "
                f"bandFH {g('band_false_hit'):5.1f}  bandFM {g('band_false_miss'):5.1f}")
    for name, m in (("IN-SAMPLE", m_in), ("HELD-OUT", m_ho)):
        print(f"\n== {name} ==")
        for c in CONFIGS:
            print(row(m, c))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
