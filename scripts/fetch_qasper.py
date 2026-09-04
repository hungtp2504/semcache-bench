#!/usr/bin/env python3
"""Fetch Qasper v0.3 (CC BY 4.0) from AllenAI's S3 into corpus/d2.

datasets>=3 dropped script-based HF datasets, so we take the original release:
  https://qasper-dataset.s3.us-west-2.amazonaws.com/qasper-train-dev-v0.3.tgz

Writes:
  corpus/d2/qasper_docs.jsonl   one line per paper: doc_id, title, abstract, sections
  corpus/d2/questions.txt       all human-written questions (input for risk check 1)
  corpus/d2/index.jsonl         provenance per corpus/README.md
"""
import datetime as dt
import json
import tarfile
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "corpus" / "d2"
URL = "https://qasper-dataset.s3.us-west-2.amazonaws.com/qasper-train-dev-v0.3.tgz"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    tgz = OUT / "qasper-train-dev-v0.3.tgz"
    if not tgz.exists():
        print(f"downloading {URL} ...", flush=True)
        urllib.request.urlretrieve(URL, tgz)
    papers = {}  # arxiv_id -> (split, paper)
    with tarfile.open(tgz) as tf:
        for member in tf.getmembers():
            if not member.name.endswith(".json"):
                continue
            split = "train" if "train" in member.name else "dev"
            data = json.load(tf.extractfile(member))
            for aid, paper in data.items():
                papers[aid] = (split, paper)
    today = dt.date.today().isoformat()
    n_docs = n_q = 0
    with open(OUT / "qasper_docs.jsonl", "w", encoding="utf-8") as fd, \
         open(OUT / "questions.txt", "w", encoding="utf-8") as fq, \
         open(OUT / "index.jsonl", "w", encoding="utf-8") as fi:
        for aid in sorted(papers):
            split, p = papers[aid]
            n_docs += 1
            doc_id = f"d2_doc{n_docs:04d}"
            sections = [{"section": s.get("section_name"), "text": "\n".join(s.get("paragraphs") or [])}
                        for s in (p.get("full_text") or [])]
            fd.write(json.dumps({
                "doc_id": doc_id, "arxiv_id": aid, "split": split,
                "title": p.get("title"), "abstract": p.get("abstract"),
                "sections": sections,
            }, ensure_ascii=False) + "\n")
            fi.write(json.dumps({
                "doc_id": doc_id, "title": p.get("title"),
                "url": f"https://arxiv.org/abs/{aid}",
                "license": "CC BY 4.0 (Qasper v0.3)", "retrieved": today,
                "notes": f"qasper split={split}",
            }, ensure_ascii=False) + "\n")
            for qa in p.get("qas") or []:
                q = (qa.get("question") or "").strip().replace("\n", " ")
                if q:
                    fq.write(q + "\n")
                    n_q += 1
    print(f"qasper: {n_docs} docs, {n_q} questions -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
