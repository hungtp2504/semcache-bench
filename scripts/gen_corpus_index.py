#!/usr/bin/env python3
"""Generate corpus/dN/index.jsonl provenance files for locally fetched sources.

d2 writes its own index in fetch_qasper.py. d1/d5 are collected manually.
One line per document file, per corpus/README.md. Re-running overwrites (indexes are
derived from what is on disk, not append-only data).
"""
import datetime as dt
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TODAY = dt.date.today().isoformat()

SOURCES = [
    # (domain dir, subdir, glob, url_base, license, notes)
    ("d3", "django", "**/*.txt", "https://github.com/django/django/tree/main/docs",
     "BSD-3-Clause (django/django)", "official Django docs, reST source"),
    ("d3", "react", "**/*.md", "https://github.com/reactjs/react.dev/tree/main/src/content",
     "CC BY 4.0 (react.dev content)", "official React docs, markdown source"),
    ("d4", "MedQuAD", "**/*.xml", "https://github.com/abachaa/MedQuAD",
     "CC BY 4.0 (MedQuAD; verify per subsource)",
     "NIH QA collection; MedlinePlus answers removed upstream for copyright — use subsets with answers"),
]


def main() -> int:
    for dom, sub, pat, url, lic, notes in SOURCES:
        root = REPO / "corpus" / dom / sub
        files = sorted(p for p in root.glob(pat) if p.is_file())
        idx = REPO / "corpus" / dom / f"index_{sub}.jsonl"
        with open(idx, "w", encoding="utf-8") as f:
            for i, p in enumerate(files, 1):
                f.write(json.dumps({
                    "doc_id": f"{dom}_{sub}_{i:05d}",
                    "title": p.stem,
                    "local_path": str(p.relative_to(REPO / "corpus")),
                    "url": url, "license": lic, "retrieved": TODAY, "notes": notes,
                }, ensure_ascii=False) + "\n")
        print(f"{idx.name}: {len(files)} docs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
