#!/usr/bin/env python3
"""Build Stage A input files from the local corpus (NOT committed — corpus licensing).

Writes corpus/<dom>/stage_a_input.jsonl: {"doc_id","domain","title","text"} per line,
text trimmed to --max-chars. Deterministic selection (sorted order, skip tiny files).

  python3 scripts/prep_stage_a.py --domain d2 --count 12
  python3 scripts/prep_stage_a.py --domain d3 --count 12
  python3 scripts/prep_stage_a.py --domain d4 --count 12
"""
import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DOMAIN_KEY = {"d1": "university_admin", "d2": "academic_nlp", "d3": "tech_docs",
              "d4": "medical", "d5": "vietnamese_admin_edu"}


def _txt_dir(root, n, max_chars, min_chars=1500):
    out = []
    for p in sorted(root.glob("*.txt")):
        if len(out) >= n:
            break
        text = p.read_text(encoding="utf-8", errors="replace")
        if len(text) < min_chars:
            continue
        out.append({"doc_id": p.stem[:60], "title": p.stem, "text": text[:max_chars]})
    return out


def docs_d1(n, max_chars):
    return _txt_dir(REPO / "corpus" / "d1" / "ocw", n, max_chars)


def docs_d5(n, max_chars):
    return _txt_dir(REPO / "corpus" / "d5" / "luatvietnam", n, max_chars, min_chars=800)


def docs_d2(n, max_chars):
    src = REPO / "corpus" / "d2" / "qasper_docs.jsonl"
    out = []
    for ln in src.read_text(encoding="utf-8").splitlines():
        if len(out) >= n:
            break
        d = json.loads(ln)
        text = (d.get("abstract") or "") + "\n\n"
        for s in d.get("sections") or []:
            text += f"== {s.get('section') or ''} ==\n{s.get('text') or ''}\n"
            if len(text) > max_chars:
                break
        if len(text) < 1500:
            continue
        out.append({"doc_id": d["doc_id"], "title": d.get("title") or d["doc_id"],
                    "text": text[:max_chars]})
    return out


def docs_d3(n, max_chars):
    roots = [(REPO / "corpus" / "d3" / "django", "*.txt", "d3_django"),
             (REPO / "corpus" / "d3" / "react", "*.md", "d3_react")]
    out = []
    per_src = (n + 1) // 2
    for root, pat, prefix in roots:
        got = 0
        for p in sorted(root.rglob(pat)):
            if got >= per_src or len(out) >= n:
                break
            text = p.read_text(encoding="utf-8", errors="replace")
            if len(text) < 3000:
                continue
            out.append({"doc_id": f"{prefix}_{p.stem}"[:60], "title": p.stem,
                        "text": text[:max_chars]})
            got += 1
    return out[:n]


def docs_d4(n, max_chars):
    root = REPO / "corpus" / "d4" / "MedQuAD"
    out = []
    for p in sorted(root.rglob("*.xml")):
        if len(out) >= n:
            break
        try:
            tree = ET.parse(p)
        except ET.ParseError:
            continue
        r = tree.getroot()
        title = (r.findtext(".//Focus") or p.stem).strip()
        parts = []
        for qa in r.iter("QAPair"):
            q = (qa.findtext("Question") or "").strip()
            ans = (qa.findtext("Answer") or "").strip()
            if q and ans:
                parts.append(f"Q: {q}\nA: {ans}")
        text = f"Topic: {title}\n\n" + "\n\n".join(parts)
        if len(parts) < 3 or len(text) < 1500:
            continue
        out.append({"doc_id": f"d4_{p.stem}"[:60], "title": title, "text": text[:max_chars]})
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--domain", required=True, choices=["d1", "d2", "d3", "d4", "d5"])
    ap.add_argument("--count", type=int, default=12)
    ap.add_argument("--skip", type=int, default=0,
                    help="skip the first N selected docs (already processed)")
    ap.add_argument("--max-chars", type=int, default=7000)
    ap.add_argument("--out-name", default="stage_a_input.jsonl")
    a = ap.parse_args()

    docs = {"d1": docs_d1, "d2": docs_d2, "d3": docs_d3, "d5": docs_d5,
            "d4": docs_d4}[a.domain](a.skip + a.count, a.max_chars)[a.skip:]
    out = REPO / "corpus" / a.domain / a.out_name
    with open(out, "w", encoding="utf-8") as f:
        for d in docs:
            d["domain"] = DOMAIN_KEY[a.domain]
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
    print(f"{out}: {len(docs)} docs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
