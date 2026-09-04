#!/usr/bin/env python3
"""Freeze the benchmark: 03_variations + 04a/04b judgments → data/05_final.jsonl.

Steps (PLAN §15 T12, CLAUDE.md):
  1. Join both judgments onto each variation record (judge1 = B1/primary, judge2 = B2).
  2. Filter: keep records with judge1.axis_ok == True (pre-registered primary-judge rule).
  3. N4/N5 (overgenerated ×4 in v1.2): keep at most the TOP-2 judge1-passed candidates
     per seed×axis, ranked by judge1 conf (ties: lower v index for determinism).
  4. MinHash dedupe within each seed's variant set AND globally on (seed_id, variation)
     near-duplicates (character 3-gram MinHash, Jaccard ≥ 0.9 → drop later one).
  5. Report per-axis/domain distribution, HIT:MISS balance, ≥8%-per-axis gate.

Idempotent: overwrites 05_final.jsonl (a BUILD artifact, not append-only history).
"""
import json
from collections import Counter, defaultdict
from pathlib import Path

from datasketch import MinHash, MinHashLSH

REPO = Path(__file__).resolve().parents[1]


def load_judgments(path):
    out = {}
    for ln in (REPO / "data" / path).read_text(encoding="utf-8").splitlines():
        if ln.strip():
            j = json.loads(ln)
            out[j["id"]] = {"model": j["judge_model"], "axis_ok": j["axis_ok"],
                            "conf": j.get("conf"), "issue": j.get("issue")}
    return out


def minhash(text, num_perm=64):
    m = MinHash(num_perm=num_perm)
    t = text.lower()
    for i in range(max(1, len(t) - 2)):
        m.update(t[i:i + 3].encode("utf-8"))
    return m


def main() -> int:
    b1 = load_judgments("04a_judgments_b1.jsonl")
    b2 = load_judgments("04b_judgments_b2.jsonl")
    records = []
    for ln in (REPO / "data" / "03_variations.jsonl").read_text(encoding="utf-8").splitlines():
        if ln.strip():
            r = json.loads(ln)
            r["judge1"] = b1.get(r["id"])
            r["judge2"] = b2.get(r["id"])
            records.append(r)
    print(f"variations: {len(records)}; judged by B1: {sum(1 for r in records if r['judge1'])}, "
          f"B2: {sum(1 for r in records if r['judge2'])}")

    # 2. primary-judge filter
    passed = [r for r in records if r["judge1"] and r["judge1"]["axis_ok"]]
    print(f"pass primary judge: {len(passed)} ({len(passed)/len(records)*100:.1f}%)")

    # 3. top-2 for overgenerated N4/N5
    by_seed_axis = defaultdict(list)
    keep = []
    for r in passed:
        if r["axis"] in ("N4", "N5"):
            by_seed_axis[(r["seed_id"], r["axis"])].append(r)
        else:
            keep.append(r)
    trimmed = 0
    for (_, _), lst in by_seed_axis.items():
        lst.sort(key=lambda r: (-(r["judge1"]["conf"] or 0), r["id"]))
        keep.extend(lst[:2])
        trimmed += max(0, len(lst) - 2)
    print(f"N4/N5 top-2 trim: removed {trimmed} extra candidates")

    # 4. MinHash dedupe on variation text within seed (near-identical variants)
    lsh = MinHashLSH(threshold=0.9, num_perm=64)
    final, dropped = [], 0
    keep.sort(key=lambda r: r["id"])
    for r in keep:
        key = r["id"]
        m = minhash(r["seed_id"] + " || " + r["variation"])
        if any(True for _ in lsh.query(m)):
            dropped += 1
            continue
        lsh.insert(key, m)
        final.append(r)
    print(f"dedupe: dropped {dropped} near-duplicates")

    out = REPO / "data" / "05_final.jsonl"
    with open(out, "w", encoding="utf-8") as f:
        for r in final:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    axes = Counter(r["axis"] for r in final)
    labels = Counter(r["expected_label"] for r in final)
    doms = Counter(r["domain"] for r in final)
    n = len(final)
    weakest = min(axes, key=axes.get)
    print(f"\n=== FROZEN: {n} pairs -> {out} ===")
    print("labels:", dict(labels), f"(HIT share {labels['HIT']/n*100:.1f}%)")
    print("axes:  ", "  ".join(f"{a}:{c}" for a, c in sorted(axes.items())))
    print(f"weakest axis: {weakest} = {axes[weakest]/n*100:.1f}% (gate >=8%)")
    print("domains:", "  ".join(f"{d}:{c}" for d, c in sorted(doms.items())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
