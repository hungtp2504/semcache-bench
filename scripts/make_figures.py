#!/usr/bin/env python3
"""Generate paper figures from results/. Currently: F3 (IO heatmap, pilot version).

Design rules (dataviz): IO is a magnitude -> single-hue sequential ramp (light->dark),
every cell direct-labeled (lookup figure, grayscale-print safe), recessive axes,
neutral ink for text. Pilot version is clearly labeled; the final F3 re-runs this
script on the full-benchmark results.

  python3 scripts/make_figures.py --pilot
"""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

REPO = Path(__file__).resolve().parents[1]
FIGDIR = REPO.parent / "paper" / "figures"

AXES = ["N1", "N2", "N3", "N4", "N5", "N6"]
GROUP = {"N1": "slope", "N2": "slope", "N3": "cliff", "N4": "cliff",
         "N5": "cliff", "N6": "cliff"}
# display order: legacy tier first (baseline lineage), then modern, then multilingual
ORDER = [
    ("distilbert/distilbert-base-uncased", "DistilBERT (legacy)"),
    ("albert/albert-base-v2", "ALBERT (legacy)"),
    ("sentence-transformers/all-MiniLM-L6-v2", "MiniLM-L6"),
    ("intfloat/e5-large-v2", "E5-large-v2"),
    ("thenlper/gte-large", "GTE-large"),
    ("nomic-ai/nomic-embed-text-v1.5", "Nomic-v1.5"),
    ("jinaai/jina-embeddings-v3", "Jina-v3"),
    ("BAAI/bge-m3", "BGE-M3"),
    ("intfloat/multilingual-e5-large", "mE5-large"),
    ("keepitreal/vietnamese-sbert", "Vi-SBERT"),
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--results", default=str(REPO / "results" / "pilot_analysis_allmodels.json"))
    ap.add_argument("--pilot", action="store_true")
    a = ap.parse_args()

    data = json.loads(Path(a.results).read_text(encoding="utf-8"))["models"]
    rows = [(label, mid) for mid, label in ORDER if mid in data]
    M = np.full((len(rows), len(AXES)), np.nan)
    for i, (_, mid) in enumerate(rows):
        io = data[mid]["rq3a"]["io_per_axis"]
        for j, ax in enumerate(AXES):
            if ax in io:
                M[i, j] = io[ax]["io"]

    fig, axp = plt.subplots(figsize=(7.0, 4.4))
    im = axp.imshow(M, cmap="Blues", vmin=0.0, vmax=0.5, aspect="auto")
    axp.set_xticks(range(len(AXES)),
                   [f"{x}\n({GROUP[x]})" for x in AXES], fontsize=9)
    axp.set_yticks(range(len(rows)), [r[0] for r in rows], fontsize=9)
    axp.tick_params(length=0)
    for s in axp.spines.values():
        s.set_visible(False)
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            v = M[i, j]
            if np.isnan(v):
                continue
            axp.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=8.5,
                     color="white" if v > 0.30 else "#1a2733")
    cb = fig.colorbar(im, ax=axp, shrink=0.85, pad=0.02)
    cb.set_label("Irreducible Overlap (higher = no threshold can separate)", fontsize=9)
    cb.outline.set_visible(False)
    title = "IO per change axis × embedding model"
    if a.pilot:
        title += "  —  PILOT (~1,330 judged pairs; final: full benchmark)"
    axp.set_title(title, fontsize=10, loc="left", pad=10)
    fig.tight_layout()
    FIGDIR.mkdir(parents=True, exist_ok=True)
    stem = "f3_io_heatmap" + ("_pilot" if a.pilot else "")
    for ext in ("pdf", "png"):
        fig.savefig(FIGDIR / f"{stem}.{ext}", dpi=200, bbox_inches="tight")
    print(f"wrote {FIGDIR}/{stem}.pdf/.png  ({len(rows)} models × {len(AXES)} axes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
