#!/usr/bin/env python3
"""Compare the opaque-identifier verifier rerun with the original stage-E decisions.

On the stratified sample (100 originally decided pairs per axis) it reports, per axis
group (inv = P1-P3, expected HIT; slope = N1-N2; cliff = N3-N6, expected MISS):
  - agreement between original and opaque decisions;
  - SERVE rate under each protocol (on HIT pairs 1 - SERVE is the in-band false-miss
    rate, on MISS pairs SERVE is the in-band false-hit rate);
  - the relative change in the cliff-minus-slope false-hit gap.
It also counts how many of the missing pairs received a decision.
Outputs results/rq5_opaque.json.
"""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
GROUP = {"N1": "slope", "N2": "slope", "N3": "cliff", "N4": "cliff", "N5": "cliff", "N6": "cliff",
         "P1": "inv", "P2": "inv", "P3": "inv"}


def jl(p):
    return [json.loads(l) for l in (REPO / p).read_text(encoding="utf-8").splitlines() if l.strip()]


def main() -> int:
    orig = {j["pair_id"]: j["decision"] == "SERVE" for j in jl("data/06_verify_decisions.jsonl")}
    key = {j["opaque_id"]: j for j in jl("data/rq5_opaque_key.jsonl")}
    new = {}
    for j in jl("data/06b_verify_decisions_opaque.jsonl"):
        if j["pair_id"] in key:
            new[j["pair_id"]] = j["decision"] == "SERVE"
    axis_of = lambda pid: pid.split("_")[2]
    out = {"n_key": len(key), "n_decided": len(new), "groups": {}, "axes": {}}
    rows = {}
    for oid, k in key.items():
        if k["role"] != "sample" or oid not in new:
            continue
        ax = axis_of(k["pair_id"])
        rows.setdefault(ax, []).append((orig[k["pair_id"]], new[oid]))
    for ax, rr in sorted(rows.items()):
        out["axes"][ax] = {"n": len(rr), "agree": sum(a == b for a, b in rr) / len(rr),
                           "serve_original": sum(a for a, _ in rr) / len(rr),
                           "serve_opaque": sum(b for _, b in rr) / len(rr)}
    for g in ("inv", "slope", "cliff"):
        rr = [x for ax, v in rows.items() if GROUP[ax] == g for x in v]
        out["groups"][g] = {"n": len(rr), "agree": sum(a == b for a, b in rr) / len(rr),
                            "serve_original": sum(a for a, _ in rr) / len(rr),
                            "serve_opaque": sum(b for _, b in rr) / len(rr)}
    miss = [oid for oid, k in key.items() if k["role"] == "missing"]
    out["missing"] = {"n": len(miss), "decided": sum(1 for o in miss if o in new)}
    allr = [x for v in rows.values() for x in v]
    out["overall_agree"] = sum(a == b for a, b in allr) / len(allr)
    (REPO / "results" / "rq5_opaque.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({k: out[k] for k in ("n_decided", "overall_agree", "groups", "missing")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
