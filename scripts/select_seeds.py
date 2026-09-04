#!/usr/bin/env python3
"""Select the balanced seed set for A4 scale (PLAN §15: pool -> 400/domain -> 2,000).

Stratified: per domain, round-robin across source documents (diversity over
first-come), skipping seeds already used in the pilot (their variants exist).

  python3 scripts/select_seeds.py --per-domain 400 --out data/scale_seed_input.jsonl
"""
import argparse
import json
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--per-domain", type=int, default=400)
    ap.add_argument("--out", default=str(REPO / "data" / "scale_seed_input.jsonl"))
    a = ap.parse_args()

    done = set()
    pilot = REPO / "data" / "pilot_seed_input.jsonl"
    if pilot.exists():
        for ln in pilot.read_text(encoding="utf-8").splitlines():
            if ln.strip():
                done.add(json.loads(ln)["seed_id"])
    # also skip anything already varied (mini-pilot etc.)
    vars_f = REPO / "data" / "03_variations.jsonl"
    if vars_f.exists():
        for ln in vars_f.read_text(encoding="utf-8").splitlines():
            if ln.strip():
                done.add(json.loads(ln)["seed_id"])

    by_dom_doc = defaultdict(lambda: defaultdict(list))
    for ln in (REPO / "data" / "02_seeds.jsonl").read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        s = json.loads(ln)
        if s["seed_id"] in done:
            continue
        by_dom_doc[s["seed_id"][:2]][s.get("doc_id")].append(ln)

    out_lines, report = [], {}
    for dom in sorted(by_dom_doc):
        docs = list(by_dom_doc[dom].values())
        picked, i = [], 0
        while len(picked) < a.per_domain and any(docs):
            for d in docs:
                if i < len(d) and len(picked) < a.per_domain:
                    picked.append(d[i])
            i += 1
            if i > max(len(d) for d in docs):
                break
        out_lines += picked
        report[dom] = len(picked)

    Path(a.out).write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    print(f"{a.out}: {len(out_lines)} seeds  {report}")
    print(f"(pilot/mini seeds excluded: {len(done)}; their variants already exist)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
