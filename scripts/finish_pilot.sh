#!/bin/bash
# Finish the pilot in PARALLEL after the sequential driver was stopped:
# remaining A4 (3 workers) -> B1 judging (4 workers, sonnet) -> B2 (4 workers, opus)
# -> §15 gate summary. Resume-safe: skips seeds already generated / items already judged.
set -uo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python

echo "== build remaining pilot seeds =="
$PY - <<'EOF'
import json
from pathlib import Path
done = set()
p = Path("data/03_variations.jsonl")
if p.exists():
    for ln in p.read_text(encoding="utf-8").splitlines():
        if ln.strip():
            done.add(json.loads(ln)["seed_id"])
out = []
for ln in Path("data/pilot_seed_input.jsonl").read_text(encoding="utf-8").splitlines():
    if ln.strip() and json.loads(ln)["seed_id"] not in done:
        out.append(ln)
Path("data/pilot_seeds_remaining.jsonl").write_text("\n".join(out) + ("\n" if out else ""), encoding="utf-8")
print(f"remaining seeds: {len(out)} (already generated: {len(done)})")
EOF

if [ -s data/pilot_seeds_remaining.jsonl ]; then
  echo "== A4 parallel (3 workers, opus) =="
  $PY scripts/parallel_exec.py --stage A4 --model claude-opus-5 \
      --input data/pilot_seeds_remaining.jsonl --per 10 --workers 3 || true
fi

echo "== B1 parallel (4 workers, sonnet — primary judge != generator) =="
$PY scripts/prep_judge_input.py --out data/judge_input_B1.jsonl --exclude data/04a_judgments_b1.jsonl
$PY scripts/parallel_exec.py --stage B1 --model claude-sonnet-5 \
    --input data/judge_input_B1.jsonl --per 60 --workers 4 || true

echo "== B2 parallel (4 workers, opus) =="
$PY scripts/prep_judge_input.py --out data/judge_input_B2.jsonl --exclude data/04b_judgments_b2.jsonl
$PY scripts/parallel_exec.py --stage B2 --model claude-opus-5 \
    --input data/judge_input_B2.jsonl --per 60 --workers 4 || true

echo "== §15 gate summary =="
$PY - <<'EOF'
import sys
sys.path.insert(0, "scripts")
from run_pipeline import gate_summary
gate_summary()
EOF
echo "== finish_pilot done =="
