#!/bin/bash
# Post-scale-A chain: (1) sweep api_error-lost Stage A docs (2 workers) IN PARALLEL
# with (2) B2 judging rerun (2 workers); then (3) v1.1 mini-pilot: 10 fresh seeds ->
# A4 v1.1 -> judge the N4/N5 variants -> print per-axis compliance vs the 80% gate.
set -uo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python

echo "== seeds per domain before sweep =="
$PY - <<'EOF'
import json, collections
c = collections.Counter(json.loads(l)["seed_id"][:2]
                        for l in open("data/02_seeds.jsonl", encoding="utf-8") if l.strip())
print(dict(sorted(c.items())), "total", sum(c.values()))
EOF

$PY scripts/build_stage_a_remaining.py

( for d in d1 d2 d3 d4 d5; do
    f="corpus/$d/stage_a_remaining.jsonl"
    [ -s "$f" ] && $PY scripts/parallel_exec.py --stage A --model claude-sonnet-5 \
        --input "$f" --per 3 --workers 2
  done
  echo "== sweep done ==" ) &
SWEEP=$!

( $PY scripts/prep_judge_input.py --out data/judge_input_B2.jsonl --exclude data/04b_judgments_b2.jsonl
  $PY scripts/parallel_exec.py --stage B2 --model claude-opus-5 \
      --input data/judge_input_B2.jsonl --per 60 --workers 2
  echo "== B2 done ==" ) &
B2=$!
wait $SWEEP $B2

echo "== v1.1 mini-pilot: 10 fresh seeds =="
$PY - <<'EOF'
import json
pilot = {json.loads(l)["seed_id"] for l in open("data/pilot_seed_input.jsonl", encoding="utf-8") if l.strip()}
per, out = {}, []
for l in open("data/02_seeds.jsonl", encoding="utf-8"):
    if not l.strip():
        continue
    s = json.loads(l)
    d = s["seed_id"][:2]
    if s["seed_id"] in pilot or per.get(d, 0) >= 2:
        continue
    per[d] = per.get(d, 0) + 1
    out.append(l.strip())
open("data/mini_v11_seeds.jsonl", "w", encoding="utf-8").write("\n".join(out[:10]) + "\n")
print("mini seeds:", len(out[:10]), per)
EOF
$PY scripts/parallel_exec.py --stage A4 --model claude-opus-5 \
    --input data/mini_v11_seeds.jsonl --per 10 --workers 1

$PY - <<'EOF'
import json
mini = {json.loads(l)["seed_id"] for l in open("data/mini_v11_seeds.jsonl", encoding="utf-8") if l.strip()}
items = []
for l in open("data/03_variations.jsonl", encoding="utf-8"):
    if not l.strip():
        continue
    v = json.loads(l)
    if v["seed_id"] in mini and v["axis"] in ("N4", "N5"):
        items.append(json.dumps({k: v.get(k) for k in
            ("id", "axis", "seed_question", "answer", "variation", "delta")}, ensure_ascii=False))
open("data/judge_input_mini.jsonl", "w", encoding="utf-8").write("\n".join(items) + "\n")
print("mini judge items (N4/N5):", len(items))
EOF
$PY scripts/parallel_exec.py --stage B1 --model claude-sonnet-5 \
    --input data/judge_input_mini.jsonl --per 60 --workers 1

echo "== v1.1 N4/N5 compliance =="
$PY - <<'EOF'
import json, collections
mini_ids = set()
for l in open("data/judge_input_mini.jsonl", encoding="utf-8"):
    if l.strip():
        mini_ids.add(json.loads(l)["id"])
ok, tot = collections.Counter(), collections.Counter()
for l in open("data/04a_judgments_b1.jsonl", encoding="utf-8"):
    if not l.strip():
        continue
    j = json.loads(l)
    if j["id"] in mini_ids:
        ax = j["id"].rsplit("_", 2)[1]
        tot[ax] += 1
        ok[ax] += j["axis_ok"]
for ax in sorted(tot):
    r = ok[ax] / tot[ax] * 100
    print(f"v1.1 {ax}: {ok[ax]}/{tot[ax]} = {r:.0f}%  [{'PASS' if r >= 80 else 'STILL BELOW 80'}]")
EOF
echo "== finish_sweep done =="
