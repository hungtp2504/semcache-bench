#!/usr/bin/env python3
"""Gold-subset human label audit analysis (PLAN §15, Month 4).

Reads the three blind annotator files in data/00_manual/annotator_*.jsonl
(schema: {"gid", "label": SAME|DIFFERENT|UNSURE}) and joins them to
data/05_final.jsonl by gid to recover axis / axis_group / domain /
expected_label. Writes results/human_gold.json.

Analysis rules (applied identically everywhere):
- Analysis set: pairs with three definite (SAME/DIFFERENT) labels. Pairs
  carrying any UNSURE vote are EXCLUDED from all statistics and reported
  separately (kappa requires three definite labels; using the same set for
  label accuracy keeps the two analyses on the same n). In the round-1 data
  the excluded pairs are exactly the three rated UNSURE by two annotators.
- Gold label: 2-of-3 majority of the three definite votes.
- CIs: the subset clusters by seed (1,060 seeds for 1,500 pairs, up to 4
  pairs/seed), so pair-level i.i.d. intervals can be optimistic. Headline CIs
  for Fleiss' kappa, Gwet's AC1, and overall label agreement use a
  nonparametric percentile CLUSTER bootstrap resampling seeds (10,000
  replicates, seed=0). Per-stratum proportions additionally carry Wilson 95%
  intervals (computed at pair level; flagged as such).

Kappa is reported alongside AC1 because chance-corrected coefficients collapse
under skewed marginals (the within-stratum prevalence artifact); see the
paper's Threats section for the same phenomenon in the judge-agreement numbers.
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


def seed_of(gid):
    return "_".join(gid.split("_")[:2])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--boot", type=int, default=10000)
    ap.add_argument("--prefix", default="data/00_manual/annotator_",
                    help="annotator file prefix relative to --base "
                         "(files <prefix>1.jsonl .. <prefix>3.jsonl)")
    ap.add_argument("--out", default="results/human_gold.json",
                    help="output JSON path relative to --base")
    args = ap.parse_args()
    base = Path(args.base)

    ann = {i: {r["gid"]: r["label"]
               for r in load_jsonl(base / f"{args.prefix}{i}.jsonl")}
           for i in (1, 2, 3)}
    final = {r["id"]: r for r in load_jsonl(base / "data/05_final.jsonl")}

    all_gids = sorted(ann[1])
    assert set(ann[1]) == set(ann[2]) == set(ann[3]), "annotator gid sets differ"
    assert all(g in final for g in all_gids), "gid missing from 05_final"

    def votes(g):
        return collections.Counter(ann[i][g] for i in (1, 2, 3)
                                   if ann[i][g] in DEFINITE)

    def gold(g):
        v = votes(g)
        if v["SAME"] >= 2:
            return "HIT"
        if v["DIFFERENT"] >= 2:
            return "MISS"
        return None

    def all_definite(g):
        return all(ann[i][g] in DEFINITE for i in (1, 2, 3))

    gold_lab = {g: gold(g) for g in all_gids}
    excluded = sorted(g for g in all_gids if not all_definite(g))
    gids = [g for g in all_gids if all_definite(g)]
    assert all(gold_lab[g] is not None for g in gids)
    n = len(gids)

    def row(g):
        a = sum(1 for i in (1, 2, 3) if ann[i][g] == "SAME")
        return (a, 3 - a)

    rows = {g: row(g) for g in gids}
    kappa, ac1, p_bar, p_same = fleiss_and_ac1(list(rows.values()))

    agree = {g: gold_lab[g] == final[g]["expected_label"] for g in gids}
    n_agree = sum(agree.values())

    # --- cluster bootstrap by seed (kappa, AC1, overall agreement) ---
    by_seed = collections.defaultdict(list)
    for g in gids:
        by_seed[seed_of(g)].append(g)
    seed_list = sorted(by_seed)
    random.seed(0)
    bk, ba, bp = [], [], []
    for _ in range(args.boot):
        sample = [g for _ in range(len(seed_list))
                  for g in by_seed[seed_list[random.randrange(len(seed_list))]]]
        k2, a2, _, _ = fleiss_and_ac1([rows[g] for g in sample])
        bk.append(k2)
        ba.append(a2)
        bp.append(sum(agree[g] for g in sample) / len(sample))
    for b in (bk, ba, bp):
        b.sort()
    lo_i, hi_i = int(0.025 * args.boot), int(0.975 * args.boot) - 1

    pairwise = {}
    for i, j in itertools.combinations((1, 2, 3), 2):
        po = sum(ann[i][g] == ann[j][g] for g in gids) / n
        ci = collections.Counter(ann[i][g] for g in gids)
        cj = collections.Counter(ann[j][g] for g in gids)
        pe = sum(ci[l] * cj[l] for l in DEFINITE) / n ** 2
        pi = [(ci[l] + cj[l]) / (2 * n) for l in DEFINITE]
        pe_g = sum(p * (1 - p) for p in pi)
        pairwise[f"A{i}-A{j}"] = {
            "raw": round(po, 4),
            "cohen_kappa": round((po - pe) / (1 - pe), 4),
            "gwet_ac1": round((po - pe_g) / (1 - pe_g), 4),
        }

    unanimous = [g for g in gids if rows[g][0] in (0, 3)]
    unan_agree = sum(agree[g] for g in unanimous)

    def bucket(keyfn):
        st = collections.defaultdict(lambda: [0, 0])
        for g in gids:
            k = keyfn(final[g])
            st[k][0] += 1
            if agree[g]:
                st[k][1] += 1
        out = {}
        for k in sorted(st):
            m, a = st[k]
            lo, hi = wilson(a, m)
            out[k] = {"n": m, "agree": a, "pct": round(a / m * 100, 2),
                      "wilson_ci95": [round(lo * 100, 2), round(hi * 100, 2)]}
        return out

    lo_w, hi_w = wilson(n_agree, n)

    disagreements = [{
        "gid": g, "axis": final[g]["axis"], "domain": final[g]["domain"],
        "expected": final[g]["expected_label"], "human_gold": gold_lab[g],
        "votes": {f"A{i}": ann[i][g] for i in (1, 2, 3)},
    } for g in gids if not agree[g]]

    per_group_desc = {}
    for grp in sorted({final[g]["axis_group"] for g in gids}):
        sub = [rows[g] for g in gids if final[g]["axis_group"] == grp]
        k2, a2, pb, ps = fleiss_and_ac1(sub)
        per_group_desc[grp] = {"n": len(sub), "raw": round(pb, 4),
                               "gwet_ac1": round(a2, 4),
                               "fleiss_kappa": round(k2, 4),
                               "human_p_same": round(ps, 4)}

    result = {
        "analysis_rules": {
            "analysis_set": "pairs with three definite (SAME/DIFFERENT) "
                            "labels; pairs carrying any UNSURE vote are "
                            "excluded from all statistics",
            "gold_label": "2-of-3 majority of definite votes",
            "bootstrap": f"nonparametric percentile cluster bootstrap over "
                         f"seeds ({len(seed_list)} clusters, "
                         f"{args.boot} replicates, RNG seed 0)",
        },
        "n_pairs_annotated": len(all_gids),
        "n_analysis_set": n,
        "n_seed_clusters": len(seed_list),
        "excluded_pairs": {g: {f"A{i}": ann[i][g] for i in (1, 2, 3)}
                           for g in excluded},
        "annotator_marginals": {
            f"A{i}": dict(collections.Counter(ann[i].values())) for i in (1, 2, 3)},
        "fleiss_kappa": round(kappa, 4),
        "fleiss_kappa_ci95_cluster": [round(bk[lo_i], 4), round(bk[hi_i], 4)],
        "gwet_ac1": round(ac1, 4),
        "gwet_ac1_ci95_cluster": [round(ba[lo_i], 4), round(ba[hi_i], 4)],
        "raw_mean_pairwise": round(p_bar, 4),
        "human_p_same": round(p_same, 4),
        "pairwise": pairwise,
        "unanimous": {"n": len(unanimous),
                      "pct": round(len(unanimous) / n * 100, 2),
                      "agree_with_construction": unan_agree,
                      "agree_pct": round(unan_agree / len(unanimous) * 100, 2)},
        "gold_vs_construction": {
            "overall": {"n": n, "agree": n_agree,
                        "pct": round(n_agree / n * 100, 2),
                        "wilson_ci95": [round(lo_w * 100, 2), round(hi_w * 100, 2)],
                        "cluster_boot_ci95": [round(bp[lo_i] * 100, 2),
                                              round(bp[hi_i] * 100, 2)]},
            "by_axis": bucket(lambda r: r["axis"]),
            "by_axis_group": bucket(lambda r: r["axis_group"]),
            "by_domain": bucket(lambda r: r["domain"]),
            "by_language": bucket(lambda r: "vi" if r["id"].startswith("d5") else "en"),
            "by_expected_label": bucket(lambda r: r["expected_label"]),
            "disagreements": disagreements,
        },
        "per_axis_group_agreement": per_group_desc,
    }

    out = base / args.out
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {out}")
    print(f"analysis set n={n} (excluded {len(excluded)}: {excluded})")
    print(f"Fleiss kappa = {kappa:.3f} cluster-boot CI "
          f"[{bk[lo_i]:.3f}, {bk[hi_i]:.3f}] (gate 0.65)")
    print(f"AC1 = {ac1:.3f} [{ba[lo_i]:.3f}, {ba[hi_i]:.3f}]  raw={p_bar:.4f}")
    print(f"gold vs construction: {n_agree}/{n} = {n_agree/n*100:.2f}% "
          f"wilson [{lo_w*100:.2f}, {hi_w*100:.2f}] "
          f"cluster-boot [{bp[lo_i]*100:.2f}, {bp[hi_i]*100:.2f}]")
    print(f"unanimous: {len(unanimous)} ({len(unanimous)/n*100:.1f}%), "
          f"of which agree {unan_agree} ({unan_agree/len(unanimous)*100:.2f}%)")
    for k, v in result["gold_vs_construction"]["by_axis"].items():
        print(f"  {k}: {v['agree']}/{v['n']} = {v['pct']}% {v['wilson_ci95']}")


if __name__ == "__main__":
    main()
