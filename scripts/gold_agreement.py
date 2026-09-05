#!/usr/bin/env python3
"""Gold-subset human validation analysis (PLAN §15, Month 4).

Reads the three blind annotator files in data/00_manual/annotator_*.jsonl
(schema: {"gid", "label": SAME|DIFFERENT|UNSURE}) and joins them to
data/05_final.jsonl by gid to recover axis / axis_group / domain /
expected_label. Writes results/human_gold.json.

Reported statistics:
- Fleiss' kappa (pre-registered gate 0.65), raw mean pairwise agreement, and
  Gwet's AC1 over the pairs with three definite (SAME/DIFFERENT) labels;
  bootstrap 95% CIs (2,000 resamples).
- Pairwise raw agreement / Cohen's kappa / AC1 per annotator pair.
- Majority (2-of-3) gold label vs the construction-derived expected label:
  overall, per axis, per axis group, per domain, per language, per label,
  each with a Wilson 95% CI; full disagreement list.
- Unanimity rates and the UNSURE items.

Kappa is reported alongside AC1 because chance-corrected coefficients collapse
under skewed marginals (the within-stratum prevalence artifact); see the paper's
Threats section for the same phenomenon in the judge-agreement numbers.
"""
import json
import math
import random
import argparse
import itertools
import collections
from pathlib import Path

DEFINITE = ("SAME", "DIFFERENT")


def load_jsonl(path):
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def wilson(k, n, z=1.96):
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    hw = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - hw, c + hw


def fleiss_and_ac1(rows):
    """rows: list of (n_same, n_diff) with n_same+n_diff == 3."""
    n, r = len(rows), 3
    p_bar = sum((a * (a - 1) + b * (b - 1)) / (r * (r - 1)) for a, b in rows) / n
    p_same = sum(a for a, _ in rows) / (n * r)
    pe_kappa = p_same ** 2 + (1 - p_same) ** 2
    pe_ac1 = 2 * p_same * (1 - p_same)
    kappa = (p_bar - pe_kappa) / (1 - pe_kappa)
    ac1 = (p_bar - pe_ac1) / (1 - pe_ac1)
    return kappa, ac1, p_bar, p_same


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--boot", type=int, default=2000)
    args = ap.parse_args()
    base = Path(args.base)

    ann = {i: {r["gid"]: r["label"]
               for r in load_jsonl(base / f"data/00_manual/annotator_{i}.jsonl")}
           for i in (1, 2, 3)}
    final = {r["id"]: r for r in load_jsonl(base / "data/05_final.jsonl")}

    gids = sorted(ann[1])
    assert set(ann[1]) == set(ann[2]) == set(ann[3]), "annotator gid sets differ"
    assert all(g in final for g in gids), "gid missing from 05_final"

    unsure = sorted({g for g in gids for i in (1, 2, 3) if ann[i][g] == "UNSURE"})
    binary = [g for g in gids
              if all(ann[i][g] in DEFINITE for i in (1, 2, 3))]

    # --- agreement among annotators (binary-complete pairs) ---
    def row(g):
        a = sum(1 for i in (1, 2, 3) if ann[i][g] == "SAME")
        return (a, 3 - a)

    rows = [row(g) for g in binary]
    kappa, ac1, p_bar, p_same = fleiss_and_ac1(rows)

    random.seed(0)
    bk, ba = [], []
    for _ in range(args.boot):
        s = [rows[random.randrange(len(rows))] for _ in range(len(rows))]
        k2, a2, _, _ = fleiss_and_ac1(s)
        bk.append(k2)
        ba.append(a2)
    bk.sort(); ba.sort()
    lo_i, hi_i = int(0.025 * args.boot), int(0.975 * args.boot) - 1

    pairwise = {}
    n_b = len(binary)
    for i, j in itertools.combinations((1, 2, 3), 2):
        po = sum(ann[i][g] == ann[j][g] for g in binary) / n_b
        ci = collections.Counter(ann[i][g] for g in binary)
        cj = collections.Counter(ann[j][g] for g in binary)
        pe = sum(ci[l] * cj[l] for l in DEFINITE) / n_b ** 2
        pi = [(ci[l] + cj[l]) / (2 * n_b) for l in DEFINITE]
        pe_g = sum(p * (1 - p) for p in pi)
        pairwise[f"A{i}-A{j}"] = {
            "raw": round(po, 4),
            "cohen_kappa": round((po - pe) / (1 - pe), 4),
            "gwet_ac1": round((po - pe_g) / (1 - pe_g), 4),
        }

    unanimous = [g for g in binary if row(g)[0] in (0, 3)]

    # --- majority gold vs construction label ---
    def gold(g):
        votes = collections.Counter(ann[i][g] for i in (1, 2, 3)
                                    if ann[i][g] in DEFINITE)
        if votes["SAME"] > votes["DIFFERENT"]:
            return "HIT"
        if votes["DIFFERENT"] > votes["SAME"]:
            return "MISS"
        return None

    gold_lab = {g: gold(g) for g in gids}
    assert all(v is not None for v in gold_lab.values()), "unresolved pair"

    def bucket(keyfn):
        st = collections.defaultdict(lambda: [0, 0])
        for g in gids:
            k = keyfn(final[g])
            st[k][0] += 1
            if gold_lab[g] == final[g]["expected_label"]:
                st[k][1] += 1
        out = {}
        for k in sorted(st):
            n, a = st[k][0], st[k][1]
            lo, hi = wilson(a, n)
            out[k] = {"n": n, "agree": a, "pct": round(a / n * 100, 2),
                      "ci95": [round(lo * 100, 2), round(hi * 100, 2)]}
        return out

    n_all = len(gids)
    a_all = sum(gold_lab[g] == final[g]["expected_label"] for g in gids)
    lo, hi = wilson(a_all, n_all)

    disagreements = [{
        "gid": g, "axis": final[g]["axis"], "domain": final[g]["domain"],
        "expected": final[g]["expected_label"], "human_gold": gold_lab[g],
        "votes": {f"A{i}": ann[i][g] for i in (1, 2, 3)},
    } for g in gids if gold_lab[g] != final[g]["expected_label"]]

    per_group_desc = {}
    for grp in sorted({final[g]["axis_group"] for g in gids}):
        sub = [row(g) for g in binary if final[g]["axis_group"] == grp]
        k2, a2, pb, ps = fleiss_and_ac1(sub)
        per_group_desc[grp] = {"n": len(sub), "raw": round(pb, 4),
                               "gwet_ac1": round(a2, 4),
                               "fleiss_kappa": round(k2, 4),
                               "p_same": round(ps, 4)}

    result = {
        "n_pairs": n_all,
        "n_binary_complete": n_b,
        "unsure_items": {g: {f"A{i}": ann[i][g] for i in (1, 2, 3)} for g in unsure},
        "annotator_marginals": {
            f"A{i}": dict(collections.Counter(ann[i].values())) for i in (1, 2, 3)},
        "fleiss_kappa": round(kappa, 4),
        "fleiss_kappa_ci95": [round(bk[lo_i], 4), round(bk[hi_i], 4)],
        "gwet_ac1": round(ac1, 4),
        "gwet_ac1_ci95": [round(ba[lo_i], 4), round(ba[hi_i], 4)],
        "raw_mean_pairwise": round(p_bar, 4),
        "pairwise": pairwise,
        "unanimous": {"n": len(unanimous),
                      "pct_of_binary": round(len(unanimous) / n_b * 100, 2)},
        "gold_vs_construction": {
            "overall": {"n": n_all, "agree": a_all,
                        "pct": round(a_all / n_all * 100, 2),
                        "ci95": [round(lo * 100, 2), round(hi * 100, 2)]},
            "by_axis": bucket(lambda r: r["axis"]),
            "by_axis_group": bucket(lambda r: r["axis_group"]),
            "by_domain": bucket(lambda r: r["domain"]),
            "by_language": bucket(lambda r: "vi" if r["id"].startswith("d5") else "en"),
            "by_expected_label": bucket(lambda r: r["expected_label"]),
            "disagreements": disagreements,
        },
        "per_axis_group_agreement": per_group_desc,
    }

    out = base / "results/human_gold.json"
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {out}")
    print(f"Fleiss kappa = {kappa:.3f} "
          f"[{bk[lo_i]:.3f}, {bk[hi_i]:.3f}] (gate 0.65) over n={n_b}")
    print(f"gold vs construction: {a_all}/{n_all} = {a_all/n_all*100:.2f}% "
          f"[{lo*100:.2f}, {hi*100:.2f}]")


if __name__ == "__main__":
    main()
