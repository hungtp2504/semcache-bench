#!/usr/bin/env python3
"""Autonomous pipeline driver: Stage A → A4 → B1/B2 through the claude CLI harness.

Registers batches in the manifest, runs them sequentially via claude_batch.py,
retries transient failures (rate limits) with sleep, keeps going past single-batch
failures, and prints the §15 quality-gate summary at the end.

  python3 scripts/run_pipeline.py --phase pilot [--dry-run]

pilot phase: 12 docs × {d2,d3,d4} → Stage A (sonnet) → first 20 seeds/domain →
A4 (opus, 10 seeds/batch) → B1 (sonnet) + B2 (opus) judge everything (60/batch).
Designed to be re-runnable: skips A/A4 work that already exists.
"""
import argparse
import json
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import manifest as mf  # noqa: E402

PY = sys.executable
SONNET = "claude-sonnet-5"
OPUS = "claude-opus-5"
MAX_RETRY = 3
RETRY_SLEEP = 600  # rate-limit ride-out
DOMS = ["d2", "d3", "d4"]


def register(stage: str, desc: str, dry: bool = False) -> str:
    if dry:
        return f"{stage}_DRY"
    m = mf.load()
    s = m["stages"].setdefault(stage, {"status": "not_started", "batches": {}})
    bid = f"{stage}_{len(s['batches']) + 1:04d}"
    s["batches"][bid] = {"status": "pending", "desc": desc, "n": None, "ts": None}
    if s["status"] in ("not_started", "done", "done_with_failures"):
        s["status"] = "in_progress"
    m["current_stage"] = stage
    mf.save(m)
    return bid


def run_batch(stage, bid, model, input_file, lines, dry=False) -> bool:
    cmd = [PY, str(REPO / "scripts" / "claude_batch.py"), "--stage", stage,
           "--batch-id", bid, "--model", model, "--input", str(input_file),
           "--lines", lines]
    if dry:
        print("DRY:", " ".join(cmd), flush=True)
        return True
    for attempt in range(1, MAX_RETRY + 1):
        print(f"\n>>> {bid} [{stage}/{model}] lines {lines} (attempt {attempt})", flush=True)
        r = subprocess.run(cmd)
        if r.returncode == 0:
            return True
        print(f"{bid} failed rc={r.returncode}; sleeping {RETRY_SLEEP}s", flush=True)
        time.sleep(RETRY_SLEEP)
    return False


def count_lines(path: Path, pred=None) -> int:
    if not path.exists():
        return 0
    n = 0
    for ln in path.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        if pred is None:
            n += 1
        else:
            try:
                if pred(json.loads(ln)):
                    n += 1
            except json.JSONDecodeError:
                pass
    return n


def phase_pilot(dry: bool) -> int:
    seeds_f = REPO / "data" / "02_seeds.jsonl"
    fails = 0

    # ---- Stage A ----
    for dom in DOMS:
        inp = REPO / "corpus" / dom / "stage_a_input.jsonl"
        subprocess.run([PY, str(REPO / "scripts" / "prep_stage_a.py"),
                        "--domain", dom, "--count", "12"], check=True)
        have = count_lines(seeds_f, lambda o, d=dom: o.get("doc_id", "").startswith(d) or
                           o.get("domain") == {"d2": "academic_nlp", "d3": "tech_docs",
                                               "d4": "medical"}[d])
        if have >= 20:
            print(f"Stage A {dom}: {have} seeds already present — skip", flush=True)
            continue
        n_docs = count_lines(inp)
        for lo in range(1, n_docs + 1, 3):
            hi = min(lo + 2, n_docs)
            bid = register("A", f"pilot {dom} docs {lo}:{hi}", dry)
            if not run_batch("A", bid, SONNET, inp, f"{lo}:{hi}", dry):
                fails += 1
                if fails >= 4:
                    print("too many consecutive failures — stopping (resume later)", flush=True)
                    return 1
            else:
                fails = 0

    # ---- Stage A4 on first 20 seeds/domain ----
    pilot_seeds = REPO / "data" / "pilot_seed_input.jsonl"
    per_dom = defaultdict(list)
    if seeds_f.exists():
        for ln in seeds_f.read_text(encoding="utf-8").splitlines():
            if not ln.strip():
                continue
            s = json.loads(ln)
            key = s["seed_id"][:2]
            if len(per_dom[key]) < 20:
                per_dom[key].append(ln)
    lines_all = [ln for k in sorted(per_dom) for ln in per_dom[k]]
    pilot_seeds.write_text("\n".join(lines_all) + "\n", encoding="utf-8")
    print(f"pilot seeds: {len(lines_all)}", flush=True)

    vars_f = REPO / "data" / "03_variations.jsonl"
    done_seed_ids = set()
    if vars_f.exists():
        for ln in vars_f.read_text(encoding="utf-8").splitlines():
            try:
                done_seed_ids.add(json.loads(ln)["seed_id"])
            except Exception:
                pass
    for lo in range(1, len(lines_all) + 1, 10):
        hi = min(lo + 9, len(lines_all))
        chunk_ids = {json.loads(x)["seed_id"] for x in lines_all[lo - 1:hi]}
        if chunk_ids and chunk_ids <= done_seed_ids:
            print(f"A4 lines {lo}:{hi} already generated — skip", flush=True)
            continue
        bid = register("A4", f"pilot seeds lines {lo}:{hi}", dry)
        if not run_batch("A4", bid, OPUS, pilot_seeds, f"{lo}:{hi}", dry):
            fails += 1
            if fails >= 4:
                return 1
        else:
            fails = 0

    # ---- Judging: B1 (sonnet, primary != generator) then B2 (opus) ----
    for stage, model, out in (("B1", SONNET, "04a_judgments_b1.jsonl"),
                              ("B2", OPUS, "04b_judgments_b2.jsonl")):
        ji = REPO / "data" / f"judge_input_{stage}.jsonl"
        subprocess.run([PY, str(REPO / "scripts" / "prep_judge_input.py"),
                        "--out", str(ji), "--exclude", str(REPO / "data" / out)],
                       check=True)
        n_items = count_lines(ji)
        for lo in range(1, n_items + 1, 60):
            hi = min(lo + 59, n_items)
            bid = register(stage, f"pilot judge lines {lo}:{hi}", dry)
            if not run_batch(stage, bid, model, ji, f"{lo}:{hi}", dry):
                fails += 1
                if fails >= 4:
                    return 1
            else:
                fails = 0

    # ---- §15 gate summary ----
    if not dry:
        gate_summary()
    return 0


def gate_summary():
    vars_f = REPO / "data" / "03_variations.jsonl"
    axis_of = {}
    for ln in vars_f.read_text(encoding="utf-8").splitlines():
        if ln.strip():
            v = json.loads(ln)
            axis_of[v["id"]] = v["axis"]
    print("\n===== §15 PILOT GATE SUMMARY (>=80% axis compliance required) =====")
    for name, f in (("B1/sonnet", "04a_judgments_b1.jsonl"), ("B2/opus", "04b_judgments_b2.jsonl")):
        p = REPO / "data" / f
        if not p.exists():
            continue
        ok, tot = Counter(), Counter()
        for ln in p.read_text(encoding="utf-8").splitlines():
            if not ln.strip():
                continue
            j = json.loads(ln)
            ax = axis_of.get(j["id"], "?")
            tot[ax] += 1
            if j["axis_ok"]:
                ok[ax] += 1
        overall = sum(ok.values()) / max(1, sum(tot.values()))
        per = "  ".join(f"{ax}:{ok[ax]/tot[ax]*100:.0f}%" for ax in sorted(tot))
        flag = "PASS" if overall >= 0.80 else "FAIL -> fix prompts before scaling"
        print(f"{name}: overall {overall*100:.1f}% [{flag}]\n  {per}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--phase", default="pilot", choices=["pilot"])
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    return phase_pilot(a.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
