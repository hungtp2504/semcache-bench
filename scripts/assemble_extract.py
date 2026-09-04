#!/usr/bin/env python3
"""Parse raw Stage A output into data/01_facts.jsonl + data/02_seeds.jsonl.

Seed/fact ids are assigned HERE, sequentially per domain, from current file counts.
Salvage-friendly; append-only.

  python3 scripts/assemble_extract.py --raw logs/generation/A_0001.raw.md \
      --batch-id A_0001 --model claude-sonnet-5
"""
import argparse
import datetime as dt
import fcntl
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
LOCKFILE = REPO / "data" / ".stage_a.lock"
DOM_NUM = {"university_admin": 1, "academic_nlp": 2, "tech_docs": 3,
           "medical": 4, "vietnamese_admin_edu": 5}


def next_index(path: Path, domain: str, field: str) -> int:
    if not path.exists():
        return 1
    n = 0
    for ln in path.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        try:
            o = json.loads(ln)
        except json.JSONDecodeError:
            continue
        if o.get("domain") == domain:
            n += 1
    return n + 1


def infer_domain(doc_id: str) -> str:
    for key, num in DOM_NUM.items():
        if doc_id.startswith(f"d{num}"):
            return key
    return "?"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raw", required=True)
    ap.add_argument("--batch-id", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--facts-out", default=str(REPO / "data" / "01_facts.jsonl"))
    ap.add_argument("--seeds-out", default=str(REPO / "data" / "02_seeds.jsonl"))
    a = ap.parse_args()

    # cross-process lock: id assignment counts existing lines, so counting + appending
    # must be atomic w.r.t. other Stage A assemblies (enables parallel Stage A)
    lk = open(LOCKFILE, "w")
    fcntl.flock(lk, fcntl.LOCK_EX)

    ts = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    facts, seeds, bad = [], [], 0
    # per-doc fact index -> fact_id mapping (fact_refs are 0-based per doc)
    doc_fact_ids = {}
    fact_ctr, seed_ctr = {}, {}

    for ln in Path(a.raw).read_text(encoding="utf-8").splitlines():
        ln = ln.strip().strip("`")
        if not ln.startswith("{"):
            continue
        try:
            o = json.loads(ln)
        except json.JSONDecodeError:
            bad += 1
            continue
        doc_id = o.get("doc_id") or ""
        dom = infer_domain(doc_id)
        if dom == "?":
            bad += 1
            continue
        dnum = DOM_NUM[dom]
        if o.get("type") == "fact" and o.get("statement"):
            if dom not in fact_ctr:
                fact_ctr[dom] = next_index(Path(a.facts_out), dom, "fact_id")
            fid = f"d{dnum}_f{fact_ctr[dom]:05d}"
            fact_ctr[dom] += 1
            doc_fact_ids.setdefault(doc_id, []).append(fid)
            facts.append({"fact_id": fid, "domain": dom, "doc_id": doc_id,
                          "statement": o["statement"], "source_span": o.get("source_span"),
                          "batch_id": a.batch_id, "ts": ts})
        elif o.get("type") == "seed" and o.get("question") and o.get("answer"):
            if dom not in seed_ctr:
                seed_ctr[dom] = next_index(Path(a.seeds_out), dom, "seed_id")
            sid = f"d{dnum}_s{seed_ctr[dom]:04d}"
            seed_ctr[dom] += 1
            refs = o.get("fact_refs") or []
            fids = [doc_fact_ids.get(doc_id, [])[i] for i in refs
                    if isinstance(i, int) and i < len(doc_fact_ids.get(doc_id, []))]
            seeds.append({"seed_id": sid, "domain": dom, "doc_id": doc_id,
                          "fact_ids": fids, "question": o["question"].strip(),
                          "answer": o["answer"].strip(),
                          "generator_model": a.model, "batch_id": a.batch_id, "ts": ts})
        else:
            bad += 1

    if not seeds:
        print(f"NO seeds parsed (bad={bad}) — mark batch failed", file=sys.stderr)
        return 1
    with open(a.facts_out, "a", encoding="utf-8") as f:
        for r in facts:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(a.seeds_out, "a", encoding="utf-8") as f:
        for r in seeds:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"appended {len(seeds)} seeds, {len(facts)} facts (bad lines: {bad})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
