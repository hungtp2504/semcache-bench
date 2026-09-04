#!/usr/bin/env python3
"""Run one generation batch through the Claude Code CLI (headless `claude -p`).

Implements the CLAUDE.md session protocol mechanically:
  render prompt (cached block first, byte-hashed) → call claude -p --output-format json
  → save logs/generation/<batch>.raw.md + <batch>.cli.json + <batch>.meta.json
  → (A4/C stages) assemble records → validate → mark manifest.

The CLI JSON result is the T1 log: it records the exact model string, usage, and
session id for every batch.

Usage (smoke test, nothing written to data/ or manifest):
  python3 scripts/claude_batch.py --stage A4 --batch-id SMOKE_0001 \
      --model claude-haiku-4-5-20251001 --input /path/seeds.jsonl --lines 1:2 \
      --workdir /tmp/x --no-mark --out /tmp/x/out.jsonl

Production (A4):
  python3 scripts/claude_batch.py --stage A4 --batch-id A4_0001 \
      --model claude-opus-5 --input data/02_seeds.jsonl --lines 1:20
"""
import argparse
import datetime as dt
import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
from render_prompt import split_prompt  # noqa: E402

STAGE_PROMPT = {
    "A": "prompts/A_extract.md",
    "A4": "prompts/A4_variation.md",
    "B1": "prompts/B_judge.md",
    "B2": "prompts/B_judge.md",
    "C": "prompts/A4_variation.md",
    "E": "prompts/E_verify.md",
}
SLOTS = ("{{seeds}}", "{{documents}}", "{{items}}", "{{pairs}}")


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stage", required=True, choices=sorted(STAGE_PROMPT))
    ap.add_argument("--batch-id", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--input", required=True, help="JSONL with batch items")
    ap.add_argument("--lines", required=True, help="1-based inclusive range, e.g. 1:20")
    ap.add_argument("--workdir", default=str(REPO.parent / ".claude_gen_workdir"),
                    help="empty cwd OUTSIDE the repo for the CLI call (so the repo's "
                         "pipeline CLAUDE.md never enters the generation context)")
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--no-mark", action="store_true", help="skip manifest marking (smoke tests)")
    ap.add_argument("--out", default=None, help="override assemble output (smoke tests)")
    a = ap.parse_args()

    # 1) render prompt
    prompt_file = REPO / STAGE_PROMPT[a.stage]
    text = prompt_file.read_text(encoding="utf-8")
    cached, tail = split_prompt(text)
    sha = hashlib.sha256(cached.encode("utf-8")).hexdigest()
    version = next((ln.split(":", 1)[1].strip().strip('"') for ln in text.splitlines()
                    if ln.startswith("version:")), "?")
    lo, hi = (int(x) for x in a.lines.split(":"))
    lines = [ln for ln in Path(a.input).read_text(encoding="utf-8").splitlines() if ln.strip()]
    batch_lines = lines[lo - 1: hi]
    if not batch_lines:
        print("empty batch — check --lines", file=sys.stderr)
        return 2
    body = tail.replace("{{batch_id}}", a.batch_id)
    for slot in SLOTS:
        body = body.replace(slot, "\n".join(batch_lines))
    prompt = cached.strip() + "\n" + body

    # 2) call claude CLI headless from a neutral cwd
    workdir = Path(a.workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    ts_start = now()
    proc = subprocess.run(
        ["claude", "-p", "--model", a.model, "--output-format", "json"],
        input=prompt, capture_output=True, text=True, timeout=a.timeout, cwd=workdir,
    )
    ts_end = now()

    gen = REPO / "logs" / "generation"
    gen.mkdir(parents=True, exist_ok=True)
    (gen / f"{a.batch_id}.prompt.txt").write_text(prompt, encoding="utf-8")

    if proc.returncode != 0:
        (gen / f"{a.batch_id}.cli_error.txt").write_text(proc.stdout + "\n--stderr--\n" + proc.stderr,
                                                         encoding="utf-8")
        print(f"claude CLI failed rc={proc.returncode}: {proc.stderr[:400]}", file=sys.stderr)
        if not a.no_mark:
            subprocess.run([sys.executable, str(REPO / "scripts" / "manifest.py"), "mark",
                            a.batch_id, "--status", "failed", "--note", f"cli rc={proc.returncode}"])
        return 1

    cli = json.loads(proc.stdout)
    result_text = cli.get("result", "")
    (gen / f"{a.batch_id}.cli.json").write_text(json.dumps(cli, ensure_ascii=False, indent=2),
                                                encoding="utf-8")
    (gen / f"{a.batch_id}.raw.md").write_text(result_text, encoding="utf-8")
    meta = {
        "batch_id": a.batch_id, "stage": a.stage,
        "model_requested": a.model,
        "model_reported": sorted((cli.get("modelUsage") or {}).keys()) or cli.get("model"),
        "prompt_file": str(prompt_file.relative_to(REPO)), "prompt_version": version,
        "cached_block_sha256": sha,
        "input_file": a.input, "input_lines": a.lines, "n_input": len(batch_lines),
        "ts_start": ts_start, "ts_end": ts_end,
        "cli_session_id": cli.get("session_id"),
        "usage": cli.get("usage"), "cost_usd": cli.get("total_cost_usd"),
    }
    (gen / f"{a.batch_id}.meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2),
                                                 encoding="utf-8")
    print(f"CLI ok: model={meta['model_reported']} session={meta['cli_session_id']}")

    # 3) stage-specific assemble + mark
    rc = 0
    n_records = None
    raw_path = str(gen / f"{a.batch_id}.raw.md")
    if a.stage in ("A4", "C"):
        cmd = [sys.executable, str(REPO / "scripts" / "assemble_variations.py"),
               "--raw", raw_path, "--seeds", a.input,
               "--batch-id", a.batch_id, "--model", a.model]
        if a.out:
            cmd += ["--out", a.out]
    elif a.stage == "A":
        cmd = [sys.executable, str(REPO / "scripts" / "assemble_extract.py"),
               "--raw", raw_path, "--batch-id", a.batch_id, "--model", a.model]
    elif a.stage in ("B1", "B2"):
        default_out = REPO / "data" / ("04a_judgments_b1.jsonl" if a.stage == "B1"
                                       else "04b_judgments_b2.jsonl")
        cmd = [sys.executable, str(REPO / "scripts" / "assemble_judgments.py"),
               "--raw", raw_path, "--batch-id", a.batch_id, "--model", a.model,
               "--out", a.out or str(default_out)]
    elif a.stage == "E":
        cmd = [sys.executable, str(REPO / "scripts" / "assemble_verify.py"),
               "--raw", raw_path, "--batch-id", a.batch_id, "--model", a.model]
        if a.out:
            cmd += ["--out", a.out]
    else:
        cmd = None
        print("(no assembler wired for this stage yet — raw + meta logs written)")
    if cmd:
        r = subprocess.run(cmd, capture_output=True, text=True)
        sys.stdout.write(r.stdout)
        sys.stderr.write(r.stderr)
        rc = r.returncode
        for tok in r.stdout.split():
            if tok.isdigit():
                n_records = int(tok)
                break

    if not a.no_mark:
        status = "done" if rc == 0 else "failed"
        cmd = [sys.executable, str(REPO / "scripts" / "manifest.py"), "mark", a.batch_id,
               "--status", status]
        if n_records is not None:
            cmd += ["--n", str(n_records)]
        subprocess.run(cmd)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
