#!/usr/bin/env python3
"""Gold-subset human-annotation analysis (annotation/PROTOCOL.md).

Usage: python3 human_annotation/scripts/gold_agreement.py human_annotation/annotator_*.jsonl

Computes Fleiss' kappa (gate 0.65), pairwise raw agreement, majority label vs
construction-derived label (overall / per axis / per domain), the adjudication
list (pairs without unanimity), and — if judge files exist — human<->LLM-judge
agreement for RQ2. Construction label: gid axis P* -> SAME, N* -> DIFFERENT.
"""
import json, re, sys, itertools, collections
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CATS = ["SAME", "DIFFERENT", "UNSURE"]

def load(path):
    out = {}
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        lab = r["label"].upper()
        assert lab in CATS, f"{path}: bad label {r['label']!r} for {r['gid']}"
        out[r["gid"]] = lab
    return out

def fleiss_kappa(rows):
    # rows: list of per-item category-count lists (must sum to n_raters)
    n = sum(rows[0])
    N = len(rows)
    p_cat = [sum(r[j] for r in rows) / (N * n) for j in range(len(CATS))]
    P_bar = sum(sum(c * (c - 1) for c in r) / (n * (n - 1)) for r in rows) / N
    P_e = sum(p * p for p in p_cat)
    return (P_bar - P_e) / (1 - P_e) if P_e < 1 else float("nan")

def main():
    files = sys.argv[1:]
    assert len(files) >= 2, "need >=2 annotator files"
    ann = {Path(f).stem: load(f) for f in files}
    names = list(ann)
    gids = set.intersection(*(set(a) for a in ann.values()))
    print(f"annotators: {names}   items with all labels: {len(gids)}")

    # Fleiss' kappa
    rows = []
    for g in gids:
        counts = [0] * len(CATS)
        for a in ann.values():
            counts[CATS.index(a[g])] += 1
        rows.append(counts)
    k = fleiss_kappa(rows)
    print(f"Fleiss' kappa = {k:.3f}  ({'PASSES' if k >= 0.65 else 'BELOW'} the 0.65 gate)")

    # pairwise raw agreement
    for x, y in itertools.combinations(names, 2):
        agree = sum(ann[x][g] == ann[y][g] for g in gids) / len(gids)
        print(f"raw agreement {x} <-> {y}: {agree:.1%}")

    # majority vs construction label
    def construction(g):
        return "SAME" if re.search(r"_P\d_", g) else "DIFFERENT"
    maj_ok = collections.Counter()
    per_axis = collections.defaultdict(lambda: [0, 0])
    per_dom = collections.defaultdict(lambda: [0, 0])
    adjud = []
    unsure = 0
    for g in gids:
        labs = [a[g] for a in ann.values()]
        cnt = collections.Counter(labs)
        maj, mc = cnt.most_common(1)[0]
        if len(set(labs)) > 1:
            adjud.append(g)
        if maj == "UNSURE":
            unsure += 1
            continue
        ok = maj == construction(g)
        axis = re.search(r"_([PN]\d)_", g).group(1)
        dom = g.split("_")[0]
        maj_ok[ok] += 1
        per_axis[axis][0] += ok
        per_axis[axis][1] += 1
        per_dom[dom][0] += ok
        per_dom[dom][1] += 1
    tot = maj_ok[True] + maj_ok[False]
    print(f"\nmajority label vs construction label: {maj_ok[True]/tot:.1%} "
          f"({maj_ok[True]}/{tot}; {unsure} majority-UNSURE excluded)")
    print("per axis: " + "  ".join(
        f"{a}:{per_axis[a][0]/per_axis[a][1]:.0%}" for a in sorted(per_axis)))
    print("per domain: " + "  ".join(
        f"{d}:{per_dom[d][0]/per_dom[d][1]:.0%}" for d in sorted(per_dom)))
    out = ROOT / "human_annotation" / "adjudication_needed.jsonl"
    with open(out, "w", encoding="utf-8") as fh:
        for g in sorted(adjud):
            fh.write(json.dumps({"gid": g}) + "\n")
    print(f"\n{len(adjud)} pairs lack unanimity -> {out}")

if __name__ == "__main__":
    main()
