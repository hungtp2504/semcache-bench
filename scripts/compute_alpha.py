#!/usr/bin/env python3
"""Inter-judge agreement (PLAN §15 gate: Krippendorff's alpha >= 0.70).

Joins 04a (B1/sonnet) and 04b (B2/opus) by variant id on the binary axis_ok
decision; reports alpha (nominal), raw agreement, and per-axis breakdown.
"""
import json
from collections import Counter
from pathlib import Path

import krippendorff
import numpy as np

REPO = Path(__file__).resolve().parents[1]


def load(path):
    out = {}
    for ln in (REPO / "data" / path).read_text(encoding="utf-8").splitlines():
        if ln.strip():
            j = json.loads(ln)
            out[j["id"]] = 1 if j["axis_ok"] else 0
    return out


def main() -> int:
    b1, b2 = load("04a_judgments_b1.jsonl"), load("04b_judgments_b2.jsonl")
    ids = sorted(set(b1) & set(b2))
    if not ids:
        print("no overlapping judgments")
        return 1
    m = np.array([[b1[i] for i in ids], [b2[i] for i in ids]], dtype=float)
    alpha = krippendorff.alpha(reliability_data=m, level_of_measurement="nominal")
    agree = float((m[0] == m[1]).mean())
    print(f"n={len(ids)} joint-judged variants")
    print(f"Krippendorff alpha (nominal): {alpha:.3f}  "
          f"[{'PASS' if alpha >= 0.70 else 'BELOW 0.70 GATE'}]")
    print(f"raw agreement: {agree:.1%}")
    per = Counter()
    tot = Counter()
    for k, i in enumerate(ids):
        ax = i.rsplit("_", 2)[1]
        tot[ax] += 1
        per[ax] += int(m[0][k] == m[1][k])
    print("per-axis raw agreement: " +
          "  ".join(f"{ax}:{per[ax]/tot[ax]*100:.0f}%" for ax in sorted(tot)))
    # judge marginals — who is stricter?
    print(f"axis_ok rates: B1/sonnet {m[0].mean():.1%}  B2/opus {m[1].mean():.1%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
