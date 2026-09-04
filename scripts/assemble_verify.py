#!/usr/bin/env python3
"""Parse raw E-stage (verifier) output into decision records. Append-only."""
import argparse, datetime as dt, json, sys
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--raw", required=True); ap.add_argument("--batch-id", required=True)
ap.add_argument("--model", required=True)
ap.add_argument("--out", default=str(Path(__file__).resolve().parents[1] / "data" / "06_verify_decisions.jsonl"))
a = ap.parse_args()
ts = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
recs, bad = [], 0
for ln in Path(a.raw).read_text(encoding="utf-8").splitlines():
    ln = ln.strip().strip("`")
    if not ln.startswith("{"): continue
    try: o = json.loads(ln)
    except json.JSONDecodeError: bad += 1; continue
    if o.get("pair_id") and o.get("decision") in ("SERVE", "REGENERATE"):
        recs.append({"pair_id": o["pair_id"], "decision": o["decision"],
                     "conf": o.get("conf"), "verifier_model": a.model,
                     "batch_id": a.batch_id, "ts": ts})
    else: bad += 1
if not recs:
    print(f"NO decisions parsed (bad={bad})", file=sys.stderr); raise SystemExit(1)
with open(a.out, "a", encoding="utf-8") as f:
    for r in recs: f.write(json.dumps(r, ensure_ascii=False) + "\n")
print(f"appended {len(recs)} decisions (bad: {bad})")
