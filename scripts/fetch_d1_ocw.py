#!/usr/bin/env python3
"""Fetch d1 (university administration) from MIT OpenCourseWare — CC BY-NC-SA 4.0.

Why OCW: real course-administration documents (syllabi, assignments, calendars,
exam pages) under an explicit open license → no private permissions needed and the
domain becomes reproducible. Consequence recorded in the datasheet: the d1-derived
subset of the benchmark ships under CC BY-NC-SA 4.0 (ShareAlike), unlike the
CC BY domains. Deviation from the baseline's private-course setting → Threats.

Strategy: sitemap crawl → keep course pages whose path ends in /pages/syllabus/,
/pages/assignments/, /pages/calendar/, /pages/exams/ → polite throttled download →
HTML-to-text → corpus/d1/ocw/*.txt + corpus/d1/index.jsonl provenance.

  python3 scripts/fetch_d1_ocw.py --count 160
"""
import argparse
import datetime as dt
import json
import re
import time
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree as ET

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "corpus" / "d1" / "ocw"
UA = {"User-Agent": "semcache-bench research crawler (academic use; contact: repo owner)"}
WANTED = ("/pages/syllabus/", "/pages/assignments/", "/pages/calendar/", "/pages/exams/")
SM_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"


def get(url, timeout=30):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


class TextExtract(HTMLParser):
    SKIP = {"script", "style", "nav", "footer", "header", "noscript"}

    def __init__(self):
        super().__init__()
        self.parts, self._skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip += 1

    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip and data.strip():
            self.parts.append(data.strip())


def html_to_text(html: bytes) -> str:
    p = TextExtract()
    p.feed(html.decode("utf-8", errors="replace"))
    text = "\n".join(p.parts)
    return re.sub(r"\n{3,}", "\n\n", text)


def sitemap_urls():
    root = ET.fromstring(get("https://ocw.mit.edu/sitemap.xml"))
    subs = [e.text for e in root.iter(f"{SM_NS}loc") if e.text]
    for sm in subs:
        try:
            sroot = ET.fromstring(get(sm))
        except Exception:
            continue
        for e in sroot.iter(f"{SM_NS}loc"):
            u = e.text or ""
            if any(w in u for w in WANTED):
                yield u


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--count", type=int, default=160)
    ap.add_argument("--per-course", type=int, default=4, help="max pages per course")
    ap.add_argument("--throttle", type=float, default=0.5)
    a = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    today = dt.date.today().isoformat()
    per_course, saved = {}, 0
    idx = open(REPO / "corpus" / "d1" / "index.jsonl", "w", encoding="utf-8")
    for url in sitemap_urls():
        if saved >= a.count:
            break
        m = re.search(r"/courses/([^/]+)/pages/([^/]+)/", url)
        if not m:
            continue
        course, page = m.group(1), m.group(2)
        if per_course.get(course, 0) >= a.per_course:
            continue
        try:
            text = html_to_text(get(url))
        except Exception as e:
            print(f"skip {url}: {e}")
            continue
        if len(text) < 1500:  # empty stubs
            continue
        per_course[course] = per_course.get(course, 0) + 1
        saved += 1
        doc_id = f"d1_{course[:40]}_{page}"
        (OUT / f"{doc_id}.txt").write_text(text, encoding="utf-8")
        idx.write(json.dumps({
            "doc_id": doc_id, "title": f"{course} — {page}", "url": url,
            "license": "CC BY-NC-SA 4.0 (MIT OpenCourseWare)", "retrieved": today,
            "notes": "d1-derived benchmark subset must ship CC BY-NC-SA; see datasheet",
        }, ensure_ascii=False) + "\n")
        if saved % 20 == 0:
            print(f"{saved} pages ({len(per_course)} courses)", flush=True)
        time.sleep(a.throttle)
    idx.close()
    print(f"done: {saved} pages from {len(per_course)} courses -> {OUT}")
    return 0 if saved else 1


if __name__ == "__main__":
    raise SystemExit(main())
