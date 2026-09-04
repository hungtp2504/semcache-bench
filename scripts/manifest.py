#!/usr/bin/env python3
"""Manifest CLI — the resume mechanism (PLAN §14). One turn = one batch = one mark.

Usage:
  python3 scripts/manifest.py status
  python3 scripts/manifest.py next A4
  python3 scripts/manifest.py add-batches A4 --count 100 --desc "seeds {i0}-{i1}" --per 20
  python3 scripts/manifest.py mark A4_0003 --status done --n 480
  python3 scripts/manifest.py mark A4_0004 --status failed --note "malformed json, salvaged 210"
  python3 scripts/manifest.py note "free-text note appended with date"

Stdlib only. Writes are atomic (temp file + os.replace).
"""
import argparse
import datetime as dt
import fcntl
import json
import os
import sys
from contextlib import contextmanager
from pathlib import Path

MANIFEST = Path(__file__).resolve().parents[1] / "logs" / "manifest.json"
LOCKFILE = MANIFEST.parent / ".manifest.lock"
STATUSES = {"pending", "running", "done", "failed"}


@contextmanager
def manifest_lock():
    """Cross-process exclusive lock held across load-modify-save (parallel jobs)."""
    with open(LOCKFILE, "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        yield


def today() -> str:
    return dt.date.today().isoformat()


def load() -> dict:
    with open(MANIFEST, encoding="utf-8") as f:
        return json.load(f)


def save(m: dict) -> None:
    m["updated"] = today()
    tmp = MANIFEST.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(m, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, MANIFEST)


def cmd_status(m: dict) -> int:
    print(f"project: {m['project']}   updated: {m['updated']}   current_stage: {m['current_stage']}")
    for stage, s in m["stages"].items():
        batches = s.get("batches", {})
        counts = {}
        for b in batches.values():
            counts[b["status"]] = counts.get(b["status"], 0) + 1
        summary = ", ".join(f"{k}:{v}" for k, v in sorted(counts.items())) or "no batches"
        print(f"  {stage:<9} {s['status']:<12} {summary}")
    nxt = first_pending(m)
    if nxt:
        stage, bid, b = nxt
        print(f"\nNEXT PENDING → {bid} ({stage}): {b.get('desc', '')}")
    else:
        print("\nNo pending batches.")
    if m.get("notes"):
        print("\nnotes:")
        for n in m["notes"][-5:]:
            print(f"  - {n}")
    return 0


def first_pending(m: dict):
    for stage, s in m["stages"].items():
        for bid in sorted(s.get("batches", {})):
            b = s["batches"][bid]
            if b["status"] == "pending":
                return stage, bid, b
    return None


def cmd_next(m: dict, stage: str) -> int:
    s = m["stages"].get(stage)
    if s is None:
        print(f"unknown stage {stage!r}", file=sys.stderr)
        return 2
    for bid in sorted(s.get("batches", {})):
        if s["batches"][bid]["status"] == "pending":
            print(bid)
            print(json.dumps(s["batches"][bid], ensure_ascii=False))
            return 0
    print(f"no pending batch in {stage}")
    return 1


def cmd_add_batches(m: dict, stage: str, count: int, desc: str, per: int) -> int:
    s = m["stages"].setdefault(stage, {"status": "not_started", "batches": {}})
    existing = len(s["batches"])
    for i in range(count):
        n = existing + i + 1
        bid = f"{stage}_{n:04d}"
        if bid in s["batches"]:
            print(f"{bid} already exists, aborting (no partial add)", file=sys.stderr)
            return 2
        i0, i1 = (n - 1) * per + 1, n * per
        s["batches"][bid] = {
            "status": "pending",
            "desc": desc.format(i0=i0, i1=i1, n=n),
            "n": None,
            "ts": None,
        }
    if s["status"] == "not_started":
        s["status"] = "in_progress"
    m["current_stage"] = stage
    save(m)
    print(f"added {count} pending batches to {stage} ({stage}_{existing+1:04d}..{stage}_{existing+count:04d})")
    return 0


def cmd_mark(m: dict, batch_id: str, status: str, n, note) -> int:
    if status not in STATUSES:
        print(f"status must be one of {sorted(STATUSES)}", file=sys.stderr)
        return 2
    stage = batch_id.rsplit("_", 1)[0]
    s = m["stages"].get(stage)
    if s is None or batch_id not in s.get("batches", {}):
        print(f"unknown batch {batch_id!r}", file=sys.stderr)
        return 2
    b = s["batches"][batch_id]
    b["status"] = status
    b["ts"] = today()
    if n is not None:
        b["n"] = n
    if note:
        b["note"] = note
    statuses = {x["status"] for x in s["batches"].values()}
    if statuses <= {"done"}:
        s["status"] = "done"
    elif statuses <= {"done", "failed"}:
        s["status"] = "done_with_failures"
    save(m)
    print(f"{batch_id} → {status}" + (f" (n={n})" if n is not None else ""))
    return 0


def cmd_note(m: dict, text: str) -> int:
    m.setdefault("notes", []).append(f"{today()} {text}")
    save(m)
    print("noted.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    p = sub.add_parser("next"); p.add_argument("stage")
    p = sub.add_parser("add-batches")
    p.add_argument("stage"); p.add_argument("--count", type=int, required=True)
    p.add_argument("--desc", default="items {i0}-{i1}"); p.add_argument("--per", type=int, default=1)
    p = sub.add_parser("mark")
    p.add_argument("batch_id"); p.add_argument("--status", required=True)
    p.add_argument("--n", type=int); p.add_argument("--note")
    p = sub.add_parser("note"); p.add_argument("text")
    a = ap.parse_args()

    if a.cmd == "status":
        return cmd_status(load())
    if a.cmd == "next":
        return cmd_next(load(), a.stage)
    # mutating commands: lock across load-modify-save
    with manifest_lock():
        m = load()
        if a.cmd == "add-batches":
            return cmd_add_batches(m, a.stage, a.count, a.desc, a.per)
        if a.cmd == "mark":
            return cmd_mark(m, a.batch_id, a.status, a.n, a.note)
        if a.cmd == "note":
            return cmd_note(m, a.text)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
