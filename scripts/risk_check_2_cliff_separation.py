#!/usr/bin/env python3
"""RISK CHECK 2 (PLAN §9) — do the cliff axes separate from the slope axes?

Input: hand-written pairs (data/00_manual/risk_check_pairs.jsonl), 20 per group:
  I   invariant  (HIT)   — big surface changes, same answer
  II  slope      (MISS)  — small changes, fuzzy answer boundary
  III cliff      (MISS)  — minimal surface change, answer flips

Per model:
  - similarity distribution per group (and per axis, and per language);
  - DANGER ZONE: share of cliff pairs whose similarity exceeds the HIT group's
    25th percentile (they'd be served at any threshold that keeps most HITs);
  - mini Irreducible Overlap: IO = 1 - max_tau balanced accuracy for I-vs-III and
    I-vs-II (a preview of the paper's flagship metric);
  - II vs III separation: KS statistic + p, mean gap.

Pre-registered decision rule (PLAN §9):
  Expected: group III sims HIGH with label MISS; group I sims spread but HIT.
  If II and III distributions coincide → the cliff/slope split has no basis:
  fall back to a flat taxonomy and DROP prediction C4.

Cost: local only, no tokens.

Usage:
  python3 scripts/risk_check_2_cliff_separation.py           # real models (downloads)
  python3 scripts/risk_check_2_cliff_separation.py --mock    # logic smoke-test only
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
                         irreducible_overlap, ks_2samp)

REPO = Path(__file__).resolve().parents[1]


def load_pairs(path: Path):
    pairs = []
    for ln in path.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        o = json.loads(ln)
        pairs.append(o)
    return pairs


def stats(v):
    v = np.asarray(v, dtype=float)
    q = np.percentile(v, [25, 50, 75, 90])
    return {"n": int(v.size), "mean": float(v.mean()), "std": float(v.std()),
            "min": float(v.min()), "p25": float(q[0]), "p50": float(q[1]),
            "p75": float(q[2]), "p90": float(q[3]), "max": float(v.max())}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pairs", default=str(REPO / "data" / "00_manual" / "risk_check_pairs.jsonl"))
    ap.add_argument("--models", nargs="+", default=None)
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--out", default=str(REPO / "results" / "risk_check_2.json"))
    a = ap.parse_args()

    pairs = load_pairs(Path(a.pairs))
    models = [MOCK_MODEL_NAME] if a.mock else (a.models or DEFAULT_RISK_MODELS)
    print(f"risk check 2 — {len(pairs)} hand-written pairs"
          + ("  [MOCK — logic test only, numbers meaningless]" if a.mock else ""))

    results = {"generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
               "mock": a.mock, "n_pairs": len(pairs), "models": {}}
    drop_c4_votes = 0

    for m in models:
        print(f"\n== {m} ==")
        texts = [p["q1"] for p in pairs] + [p["q2"] for p in pairs]
        E = embed_texts(texts, m, mock=a.mock)
        n = len(pairs)
        sims = np.einsum("ij,ij->i", E[:n], E[n:])

        by_group, by_axis, by_lang = defaultdict(list), defaultdict(list), defaultdict(list)
        for p, s in zip(pairs, sims):
            by_group[p["group"]].append(float(s))
            by_axis[p["axis"]].append(float(s))
            by_lang[(p["group"], p["lang"])].append(float(s))

        gstats = {g: stats(v) for g, v in sorted(by_group.items())}
        print(f"{'group':>6} {'n':>4} {'mean':>7} {'std':>6} {'p25':>7} {'p50':>7} {'p75':>7}")
        for g, st in gstats.items():
            print(f"{g:>6} {st['n']:>4} {st['mean']:>7.3f} {st['std']:>6.3f} "
                  f"{st['p25']:>7.3f} {st['p50']:>7.3f} {st['p75']:>7.3f}")
        print("  per axis mean: " + "  ".join(
            f"{ax}:{np.mean(v):.3f}" for ax, v in sorted(by_axis.items())))
        print("  per lang mean: " + "  ".join(
            f"{g}/{l}:{np.mean(v):.3f}" for (g, l), v in sorted(by_lang.items())))

        hit = np.array(by_group["I"]); slope = np.array(by_group["II"]); cliff = np.array(by_group["III"])
        hit_p25 = float(np.percentile(hit, 25))
        danger = float((cliff > hit_p25).mean())
        io_cliff, tau_cliff = irreducible_overlap(hit, cliff)
        io_slope, tau_slope = irreducible_overlap(hit, slope)
        ks_d, ks_p = ks_2samp(slope, cliff)
        gap = float(cliff.mean() - slope.mean())

        print(f"  danger zone: {danger:.0%} of CLIFF pairs sit above HIT's p25 ({hit_p25:.3f})")
        print(f"  mini-IO  I-vs-III (cliff): {io_cliff:.3f} @ tau*={tau_cliff:.3f}")
        print(f"  mini-IO  I-vs-II  (slope): {io_slope:.3f} @ tau*={tau_slope:.3f}")
        print(f"  II vs III: mean gap = {gap:+.3f}, KS D = {ks_d:.3f}, p = {ks_p:.3g}")

        coincide = ks_p > 0.05 and abs(gap) < 0.02
        if coincide:
            drop_c4_votes += 1
        results["models"][m] = {
            "group_stats": gstats,
            "axis_means": {ax: float(np.mean(v)) for ax, v in by_axis.items()},
            "lang_means": {f"{g}/{l}": float(np.mean(v)) for (g, l), v in by_lang.items()},
            "danger_zone_share": danger, "hit_p25": hit_p25,
            "io_hit_vs_cliff": io_cliff, "io_hit_vs_slope": io_slope,
            "ks_II_vs_III": {"D": ks_d, "p": ks_p}, "mean_gap_III_minus_II": gap,
            "II_III_coincide": bool(coincide),
        }

    print("\n--- pre-registered verdict (PLAN §9) ---")
    if a.mock:
        verdict = "MOCK RUN — logic verified only; rerun with real models before deciding anything."
    elif drop_c4_votes == len(models):
        verdict = ("BAD: II and III similarity distributions coincide on every model → the "
                   "cliff/slope dichotomy has no empirical basis on these pairs. Fall back to a "
                   "flat taxonomy and DROP C4 (PLAN §9). Re-examine pairs first — they are hand-written.")
    elif drop_c4_votes > 0:
        verdict = ("MIXED: II/III coincide on some models. Expand the pair set and retest "
                   "before committing to C4.")
    else:
        verdict = ("SUPPORTED: cliff sits measurably above slope (and inside HIT's range = the "
                   "danger zone) → the cliff/slope split and prediction C4 stand for now. "
                   "Expected pattern: III high-sim + MISS, I spread + HIT.")
    print(verdict)
    results["verdict"] = verdict

    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
