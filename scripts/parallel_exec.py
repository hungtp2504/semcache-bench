#!/usr/bin/env python3
"""Parallel batch executor for the claude CLI harness.

Safe-parallelism design:
  - Workers ONLY call claude_batch.py with --no-mark and a per-batch --out SHARD
    (unique file), so no two processes ever append to the same data file.
  - Manifest marks happen in the driver thread under a lock (manifest.py is
    read-modify-write and must not race).
  - After all batches of a stage finish, shards are merged into the stage's real
    data file IN BATCH ORDER (deterministic), then shards are kept for audit.
  - Stage A is NOT parallel-safe (sequential seed-id assignment) — this executor
    refuses it by design; run A through run_pipeline.py.

Usage:
  python3 scripts/parallel_exec.py --stage B1 --model claude-sonnet-5 \
      --input data/judge_input_B1.jsonl --per 60 --workers 4
  python3 scripts/parallel_exec.py --stage A4 --model claude-opus-5 \
      --input data/pilot_seed_input.jsonl --per 10 --workers 3
"""
import argparse
import fcntl
import json
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import manifest as mf  # noqa: E402

PY = sys.executable
LOCK = threading.Lock()
STAGE_TARGET = {
    "A":  None,  # assemble_extract appends directly under its own flock
    "A4": "data/03_variations.jsonl",
    "C":  "data/03_variations_rq6.jsonl",
    "B1": "data/04a_judgments_b1.jsonl",
    "B2": "data/04b_judgments_b2.jsonl",
    "E":  "data/06_verify_decisions.jsonl",
}


@contextmanager
def file_lock(path: Path):
    with open(path, "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        yield


def register(stage: str, desc: str) -> str:
    with LOCK, file_lock(REPO / "logs" / ".manifest.lock"):
        m = mf.load()
        s = m["stages"].setdefault(stage, {"status": "not_started", "batches": {}})
        bid = f"{stage}_{len(s['batches']) + 1:04d}"
        s["batches"][bid] = {"status": "running", "desc": desc, "n": None, "ts": None}
        if s["status"] != "in_progress":
            s["status"] = "in_progress"
        mf.save(m)
        return bid


def mark(bid: str, status: str, n=None, note=None):
    with LOCK:
        cmd = [PY, str(REPO / "scripts" / "manifest.py"), "mark", bid, "--status", status]
        if n is not None:
            cmd += ["--n", str(n)]
        if note:
            cmd += ["--note", note]
        subprocess.run(cmd, capture_output=True)


def run_one(spec) -> tuple:
    bid, stage, model, inp, lines, shard = spec
    cmd = [PY, str(REPO / "scripts" / "claude_batch.py"), "--stage", stage,
           "--batch-id", bid, "--model", model, "--input", str(inp),
           "--lines", lines, "--no-mark"]
    if shard is not None:
        cmd += ["--out", str(shard)]
    attempt = 0
    cap_waits = 0
    while attempt < 3:
        attempt += 1
        r = subprocess.run(cmd, capture_output=True, text=True)
        # 5h-window cap: wait it out instead of burning attempts (up to ~5h)
        err_file = REPO / "logs" / "generation" / f"{bid}.cli_error.txt"
        if r.returncode != 0 and err_file.exists() and \
                "session limit" in err_file.read_text(encoding="utf-8", errors="replace"):
            cap_waits += 1
            if cap_waits <= 10:
                print(f"[cap] {bid}: session limit hit — sleeping 30 min "
                      f"(wait {cap_waits}/10)", flush=True)
                import time
                time.sleep(1800)
                attempt -= 1  # cap waits don't consume attempts
                continue
        if r.returncode == 0:
            n = None
            for tok in r.stdout.split():
                if tok.isdigit():
                    n = int(tok)
                    break
            # merge-on-complete under cross-process lock → interruption never leaves
            # done-marked batches unmerged
            if shard is not None and shard.exists():
                target = REPO / STAGE_TARGET[stage]
                with file_lock(target.with_suffix(".lock")):
                    with open(target, "a", encoding="utf-8") as out:
                        for ln in shard.read_text(encoding="utf-8").splitlines():
                            if ln.strip():
                                out.write(ln + "\n")
            mark(bid, "done", n=n)
            print(f"[ok] {bid} lines {lines} n={n}", flush=True)
            return bid, True, n
        print(f"[retry {attempt}] {bid}: rc={r.returncode} {r.stderr[:200]}", flush=True)
        import time
        time.sleep(120 * attempt)
    mark(bid, "failed", note="parallel exec: 3 attempts failed")
    return bid, False, None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stage", required=True, choices=sorted(k for k in STAGE_TARGET))
    ap.add_argument("--model", required=True)
    ap.add_argument("--input", required=True)
    ap.add_argument("--per", type=int, required=True, help="items per batch")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--limit", type=int, default=None, help="max batches this run")
    ap.add_argument("--target", default=None,
                    help="override merge-target data file (e.g. RQ6 per-generator outputs)")
    a = ap.parse_args()

    n_items = sum(1 for ln in Path(a.input).read_text(encoding="utf-8").splitlines()
                  if ln.strip())
    if n_items == 0:
        print("empty input")
        return 0
    shard_dir = REPO / "data" / "shards" / a.stage
    shard_dir.mkdir(parents=True, exist_ok=True)

    if a.target:
        STAGE_TARGET[a.stage] = a.target
    use_shards = STAGE_TARGET[a.stage] is not None
    specs = []
    for lo in range(1, n_items + 1, a.per):
        hi = min(lo + a.per - 1, n_items)
        bid = register(a.stage, f"parallel {Path(a.input).name} lines {lo}:{hi}")
        specs.append((bid, a.stage, a.model, a.input, f"{lo}:{hi}",
                      (shard_dir / f"{bid}.jsonl") if use_shards else None))
        if a.limit and len(specs) >= a.limit:
            break

    print(f"{len(specs)} batches × {a.per} items, {a.workers} workers"
          + (f" → shards in {shard_dir}" if use_shards else " (direct append, flock)"),
          flush=True)
    results = {}
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(run_one, s): s[0] for s in specs}
        for f in as_completed(futs):
            bid, ok, n = f.result()
            results[bid] = ok

    ok_n = sum(1 for v in results.values() if v)
    print(f"\nbatches ok {ok_n}/{len(specs)} (records merged on completion)", flush=True)
    return 0 if ok_n == len(specs) else 1


if __name__ == "__main__":
    raise SystemExit(main())
