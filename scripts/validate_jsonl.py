#!/usr/bin/env python3
"""Validate a stage's JSONL file and print distribution stats (quality gates, PLAN §15).

Usage:
  python3 scripts/validate_jsonl.py --stage risk_pairs data/00_manual/risk_check_pairs.jsonl
  python3 scripts/validate_jsonl.py --stage seeds      data/02_seeds.jsonl
  python3 scripts/validate_jsonl.py --stage variations data/03_variations.jsonl
  python3 scripts/validate_jsonl.py --stage judgments  data/04a_judgments_b1.jsonl

Exit code 0 = clean, 1 = errors found. Stdlib only.
Axis constants mirror config/taxonomy.yaml v1.0 — keep in sync on version bumps.
"""
import argparse
import json
import re
import sys
from collections import Counter

AXES = {"P1", "P2", "P3", "N1", "N2", "N3", "N4", "N5", "N6"}
AXIS_GROUP = {
    "P1": "invariant", "P2": "invariant", "P3": "invariant",
    "N1": "slope", "N2": "slope",
    "N3": "cliff", "N4": "cliff", "N5": "cliff", "N6": "cliff",
}
LABEL = {"invariant": "HIT", "slope": "MISS", "cliff": "MISS"}
GROUP_ROMAN = {"I": "invariant", "II": "slope", "III": "cliff"}
DOMAINS = {"university_admin", "academic_nlp", "tech_docs", "medical", "vietnamese_admin_edu"}
SEED_RE = re.compile(r"^d[1-5]_s\d{4}$")
VAR_RE = re.compile(r"^d[1-5]_s\d{4}_(P[1-3]|N[1-6])_v\d+$")


def err(errors, i, msg):
    errors.append(f"  line {i}: {msg}")


def check_risk_pair(o, i, errors):
    for f in ("pair_id", "group", "axis", "lang", "q1", "q2", "expected"):
        if not o.get(f):
            err(errors, i, f"missing {f}")
            return
    if o["group"] not in GROUP_ROMAN:
        err(errors, i, f"group must be I/II/III, got {o['group']}")
        return
    if o["axis"] not in AXES:
        err(errors, i, f"unknown axis {o['axis']}")
        return
    g = GROUP_ROMAN[o["group"]]
    if AXIS_GROUP[o["axis"]] != g:
        err(errors, i, f"axis {o['axis']} not in group {o['group']}")
    if o["expected"] != LABEL[g]:
        err(errors, i, f"expected must be {LABEL[g]} for group {o['group']}")
    if o["lang"] not in {"en", "vi"}:
        err(errors, i, f"lang must be en|vi")
    if o["q1"].strip() == o["q2"].strip():
        err(errors, i, "q1 == q2")


def check_seed(o, i, errors):
    for f in ("seed_id", "domain", "question", "answer"):
        if not o.get(f):
            err(errors, i, f"missing {f}")
            return
    if not SEED_RE.match(o["seed_id"]):
        err(errors, i, f"bad seed_id {o['seed_id']}")
    if o["domain"] not in DOMAINS:
        err(errors, i, f"unknown domain {o['domain']}")


def check_variation(o, i, errors):
    for f in ("id", "seed_id", "variation", "axis", "axis_group", "expected_label",
              "generator_model", "batch_id"):
        if o.get(f) in (None, ""):
            err(errors, i, f"missing {f}")
            return
    if not VAR_RE.match(o["id"]):
        err(errors, i, f"bad id {o['id']}")
    ax = o["axis"]
    if ax not in AXES:
        err(errors, i, f"unknown axis {ax}")
        return
    if o["axis_group"] != AXIS_GROUP[ax]:
        err(errors, i, f"axis_group inconsistent with axis {ax}")
    if o["expected_label"] != LABEL[AXIS_GROUP[ax]]:
        err(errors, i, f"expected_label inconsistent with axis {ax} — labels are derived, never model-set")
    if ax.startswith("N") and not o.get("delta"):
        err(errors, i, f"N-axis record missing delta")


def check_judgment(o, i, errors):
    for f in ("id", "judge_model", "batch_id"):
        if not o.get(f):
            err(errors, i, f"missing {f}")
            return
    if not isinstance(o.get("axis_ok"), bool):
        err(errors, i, "axis_ok must be boolean")
    c = o.get("conf")
    if not isinstance(c, (int, float)) or not (0 <= c <= 1):
        err(errors, i, "conf must be in [0,1]")


CHECKS = {"risk_pairs": check_risk_pair, "seeds": check_seed,
          "variations": check_variation, "judgments": check_judgment}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stage", required=True, choices=sorted(CHECKS))
    ap.add_argument("file")
    a = ap.parse_args()

    errors, rows = [], []
    with open(a.file, encoding="utf-8") as f:
        for i, ln in enumerate(f, 1):
            ln = ln.strip()
            if not ln:
                continue
            try:
                o = json.loads(ln)
            except json.JSONDecodeError as e:
                err(errors, i, f"invalid JSON: {e}")
                continue
            CHECKS[a.stage](o, i, errors)
            rows.append(o)

    print(f"{a.file}: {len(rows)} records, {len(errors)} problems")
    for e in errors[:30]:
        print(e)
    if len(errors) > 30:
        print(f"  ... and {len(errors) - 30} more")

    if rows:
        def dist(key):
            c = Counter(r.get(key, "?") for r in rows)
            return "  ".join(f"{k}:{v}" for k, v in sorted(c.items()))
        if a.stage == "risk_pairs":
            print(f"  groups: {dist('group')}\n  axes:   {dist('axis')}\n  lang:   {dist('lang')}")
        elif a.stage == "seeds":
            print(f"  domains: {dist('domain')}")
        elif a.stage == "variations":
            print(f"  axes:   {dist('axis')}\n  labels: {dist('expected_label')}")
            c = Counter(r["axis"] for r in rows if r.get("axis") in AXES)
            if c:
                total = sum(c.values())
                weakest = min(c, key=c.get)
                share = c[weakest] / total * 100
                flag = "OK" if share >= 8 else "BELOW 8% GATE (PLAN §15)"
                print(f"  weakest axis: {weakest} at {share:.1f}% — {flag}")
        elif a.stage == "judgments":
            ok = sum(1 for r in rows if r.get("axis_ok") is True)
            print(f"  axis_ok rate: {ok}/{len(rows)} = {ok/len(rows)*100:.1f}% (pilot gate: >=80%, PLAN §15)")
            print(f"  judges: {dist('judge_model')}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
