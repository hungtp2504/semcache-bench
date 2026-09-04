#!/usr/bin/env python3
"""Convert one annotator CSV sheet (human_annotation/sheets/annotator_N.csv) to the
JSONL format gold_agreement.py expects (human_annotation/annotator_N.jsonl).

Usage: python3 human_annotation/scripts/sheet_to_jsonl.py human_annotation/sheets/annotator_1.csv
Refuses to convert if any row is unlabeled or a label is not SAME/DIFFERENT/UNSURE.
"""
import csv, json, sys
from pathlib import Path

CATS = {"SAME", "DIFFERENT", "UNSURE"}

def main():
    src = Path(sys.argv[1])
    rows, errors = [], []
    with open(src, encoding="utf-8-sig", newline="") as fh:
        for i, row in enumerate(csv.DictReader(fh), 2):  # header = line 1
            gid = row["gid"].strip()
            label = row.get("nhan (SAME/DIFFERENT/UNSURE)", "").strip().upper()
            if not label:
                errors.append(f"line {i} ({gid}): missing label")
            elif label not in CATS:
                errors.append(f"line {i} ({gid}): bad label {label!r}")
            else:
                rows.append({"gid": gid, "label": label})
    if errors:
        print(f"{src.name}: {len(errors)} problem(s), NOT converted:")
        for e in errors[:20]:
            print("  " + e)
        if len(errors) > 20:
            print(f"  ... and {len(errors)-20} more")
        sys.exit(1)
    out = src.parents[1] / (src.stem + ".jsonl")
    with open(out, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"{src.name}: {len(rows)} labels -> {out}")

if __name__ == "__main__":
    main()
