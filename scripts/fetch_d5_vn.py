#!/usr/bin/env python3
"""Fetch d5 (Vietnamese administrative/educational documents) from luatvietnam.vn.

Legal basis: văn bản quy phạm pháp luật are exempt from copyright (Điều 15 Luật Sở
hữu trí tuệ) — only the SOURCE portal needs provenance credit, recorded per doc.
Fetching uses local curl with a browser UA (the portal serves full text to normal
VN traffic; server-side fetchers are WAF-blocked).

Each document is split by "Điều N." into chunks of ~3 articles → Stage A doc units.

  python3 scripts/fetch_d5_vn.py
"""
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
from fetch_d1_ocw import html_to_text  # noqa: E402

OUT = REPO / "corpus" / "d5" / "luatvietnam"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

DOCS = [
    ("tt40_2026_cong_tac_sinh_vien", "Thông tư 40/2026/TT-BGDĐT — Quy định công tác sinh viên",
     "https://luatvietnam.vn/giao-duc/thong-tu-40-2026-tt-bgddt-quy-dinh-cong-tac-sinh-vien-hieu-luc-tu-30-06-2026-434663-d1.html"),
    ("tt53_2026_tuyen_sinh_sau_dh", "Thông tư 53/2026/TT-BGDĐT — Quy chế tuyển sinh và đào tạo sau đại học",
     "https://luatvietnam.vn/giao-duc/thong-tu-53-2026-tt-bgddt-quy-che-tuyen-sinh-va-dao-tao-sau-dai-hoc-moi-nhat-440236-d1.html"),
    ("tt56_2026_quy_che_dao_tao_dh", "Thông tư 56/2026/TT-BGDĐT — Quy chế đào tạo trình độ đại học",
     "https://luatvietnam.vn/giao-duc/thong-tu-56-2026-tt-bgddt-quy-che-dao-tao-trinh-do-dai-hoc-moi-nhat-tu-bo-giao-duc-442198-d1.html"),
    ("nd81_2021_hoc_phi", "Nghị định 81/2021/NĐ-CP — Cơ chế thu, quản lý học phí; miễn, giảm học phí",
     "https://luatvietnam.vn/tai-chinh/nghi-dinh-81-2021-nd-cp-ve-co-che-thu-quan-ly-va-chinh-sach-mien-giam-hoc-phi-208409-d1.html"),
    ("vbhn07_2023_hoc_phi", "Văn bản hợp nhất 07/VBHN-BGDĐT 2023 — Thu, quản lý học phí",
     "https://luatvietnam.vn/thue/van-ban-hop-nhat-07-vbhn-bgddt-2023-co-che-thu-quan-ly-hoc-phi-doi-voi-co-so-giao-duc-262855-d5.html"),
    ("ct20_2026_thi_tn_thpt", "Chỉ thị 20/CT-TTg 2026 — Kỳ thi tốt nghiệp THPT và tuyển sinh",
     "https://luatvietnam.vn/giao-duc/chi-thi-20-ct-ttg-2026-to-chuc-ky-thi-tot-nghiep-thpt-va-tuyen-sinh-dai-hoc-giao-duc-nghe-nghiep-434893-d1.html"),
    ("nq29_2026_chi_phi_thi", "Nghị quyết 29/2026/NQ-HĐND Tuyên Quang — Chi phí tổ chức kỳ thi",
     "https://luatvietnam.vn/giao-duc/nghi-quyet-29-2026-nq-hdnd-tuyen-quang-quy-dinh-chi-phi-to-chuc-ky-thi-giao-duc-438384-d2.html"),
]
DIEU_RE = re.compile(r"(?=\nĐiều \d+\s*[\.:])")


def fetch(url: str) -> str:
    r = subprocess.run(["curl", "-sL", "--max-time", "40", "-A", UA, url],
                       capture_output=True)
    return r.stdout.decode("utf-8", errors="replace")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    today = dt.date.today().isoformat()
    idx = open(REPO / "corpus" / "d5" / "index.jsonl", "w", encoding="utf-8")
    total_sub = 0
    for slug, title, url in DOCS:
        html = fetch(url)
        text = html_to_text(html.encode("utf-8"))
        parts = DIEU_RE.split("\n" + text)
        articles = [p.strip() for p in parts[1:] if p.strip().startswith("Điều")]
        if len(articles) < 5:
            print(f"WARN {slug}: only {len(articles)} 'Điều' found ({len(text)} chars) — "
                  f"page may be truncated for guests; skipping", flush=True)
            continue
        # chunks of 3 articles, prefixed with the document title for context
        n_sub = 0
        for i in range(0, len(articles), 3):
            chunk = f"{title}\n\n" + "\n\n".join(articles[i:i + 3])
            if len(chunk) < 800:
                continue
            n_sub += 1
            doc_id = f"d5_{slug}_p{n_sub:02d}"
            (OUT / f"{doc_id}.txt").write_text(chunk, encoding="utf-8")
            idx.write(json.dumps({
                "doc_id": doc_id, "title": f"{title} (phần {n_sub})", "url": url,
                "license": "VBQPPL — không thuộc phạm vi bảo hộ bản quyền (Điều 15 Luật SHTT); nguồn: luatvietnam.vn",
                "retrieved": today, "notes": f"articles {i+1}-{min(i+3, len(articles))} of {len(articles)}",
            }, ensure_ascii=False) + "\n")
        total_sub += n_sub
        print(f"{slug}: {len(articles)} điều -> {n_sub} subdocs", flush=True)
    idx.close()
    print(f"done: {total_sub} subdocs -> {OUT}")
    return 0 if total_sub else 1


if __name__ == "__main__":
    raise SystemExit(main())
