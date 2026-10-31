#!/usr/bin/env python3
"""Run the opaque-identifier verifier rerun (stage E, batches E2_0001..) through
claude_batch.py: 50 pairs per call from data/rq5_opaque_input.jsonl, same prompt and
model as the original stage E. Each batch writes its own shard; shards are merged in
batch order into data/06b_verify_decisions_opaque.jsonl. Raw output, CLI json and
meta for every batch land in logs/generation/ as for every other stage.
Re-running skips batches whose shard already exists.
"""
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MODEL, PER, WORKERS = "claude-haiku-4-5-20251001", 50, 4
INP = REPO / "data" / "rq5_opaque_input.jsonl"
SHARDS = REPO / "data" / "shards" / "E2"
OUT = REPO / "data" / "06b_verify_decisions_opaque.jsonl"


def run(k, lo, hi):
    bid = f"E2_{k:04d}"
    shard = SHARDS / f"{bid}.jsonl"
    if shard.exists() and shard.stat().st_size > 0:
        return bid, "skip"
    r = subprocess.run([sys.executable, str(REPO / "scripts" / "claude_batch.py"), "--stage", "E",
                        "--batch-id", bid, "--model", MODEL, "--input", str(INP),
                        "--lines", f"{lo}:{hi}", "--no-mark", "--out", str(shard)],
                       capture_output=True, text=True)
    return bid, (r.stdout.strip().splitlines() or ["?"])[-1] + (f" rc={r.returncode}" if r.returncode else "")


def main() -> int:
    n = sum(1 for l in INP.read_text(encoding="utf-8").splitlines() if l.strip())
    SHARDS.mkdir(parents=True, exist_ok=True)
    jobs = [(k + 1, lo, min(lo + PER - 1, n)) for k, lo in enumerate(range(1, n + 1, PER))]
    with ThreadPoolExecutor(WORKERS) as ex:
        for bid, msg in ex.map(lambda j: run(*j), jobs):
            print(bid, msg, flush=True)
    missing = [f"E2_{k:04d}" for k, _, _ in jobs if not (SHARDS / f"E2_{k:04d}.jsonl").exists()]
    if missing:
        print("incomplete batches:", missing)
        return 1
    with open(OUT, "w", encoding="utf-8") as f:
        for k, _, _ in jobs:
            f.write((SHARDS / f"E2_{k:04d}.jsonl").read_text(encoding="utf-8"))
    print("merged", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
