#!/usr/bin/env python3
"""Dataset-analysis figures: FD1 composition, FD2 empirical spectrum, FD3 overlap."""
import json, sys
from collections import defaultdict
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from embed_utils import embed_texts

REPO = Path(__file__).resolve().parents[1]
FIG = REPO.parent / "paper" / "figures"
INK, MUT, GRID = "#1a2733", "#5b6b7a", "#e3e8ec"
BLUE, ORANGE, GREEN = "#3b6fb6", "#c2571f", "#3d8f5f"
AXES = ["P1", "P2", "P3", "N1", "N2", "N3", "N4", "N5", "N6"]
GROUPC = {"P1": GREEN, "P2": GREEN, "P3": GREEN, "N1": BLUE, "N2": BLUE,
          "N3": ORANGE, "N4": ORANGE, "N5": ORANGE, "N6": ORANGE}
DOMS = [("university_admin", "univ. admin"), ("academic_nlp", "acad. NLP"),
        ("tech_docs", "tech docs"), ("medical", "medical"),
        ("vietnamese_admin_edu", "VN admin")]

recs = [json.loads(l) for l in (REPO / "data" / "05_final.jsonl")
        .read_text(encoding="utf-8").splitlines() if l.strip()]
print("pairs:", len(recs))

def style(ax):
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    for s in ("left", "bottom"): ax.spines[s].set_color(MUT)
    ax.tick_params(colors=MUT, labelsize=8)

# ---------- FD1: composition heatmap ----------
M = np.zeros((len(AXES), len(DOMS)))
for r in recs:
    M[AXES.index(r["axis"]), [d for d, _ in DOMS].index(r["domain"])] += 1
fig, ax = plt.subplots(figsize=(5.6, 3.6))
im = ax.imshow(M, cmap="Blues", aspect="auto")
ax.set_xticks(range(len(DOMS)), [n for _, n in DOMS], fontsize=8)
ax.set_yticks(range(len(AXES)), AXES, fontsize=8)
ax.tick_params(length=0)
for s in ax.spines.values(): s.set_visible(False)
for i in range(len(AXES)):
    for j in range(len(DOMS)):
        ax.text(j, i, f"{int(M[i,j])}", ha="center", va="center", fontsize=7.5,
                color="white" if M[i, j] > M.max()*0.6 else INK)
ax.set_title("Benchmark composition: pairs per axis × domain (46,214 total)",
             fontsize=10, loc="left", color=INK)
fig.tight_layout()
for ext in ("pdf", "png"):
    fig.savefig(FIG / f"fd1_composition.{ext}", dpi=200, bbox_inches="tight")
plt.close(fig); print("FD1 done")

# ---------- shared: sims + lexical surface step ----------
print("embedding for FD2/FD3...", flush=True)
E = embed_texts([r["seed_question"] for r in recs] + [r["variation"] for r in recs],
                "BAAI/bge-m3")
n = len(recs)
sims = np.einsum("ij,ij->i", E[:n], E[n:])
def jacc(a, b):
    A, B = set(a.lower().split()), set(b.lower().split())
    return len(A & B) / max(1, len(A | B))
surf = np.array([1.0 - jacc(r["seed_question"], r["variation"]) for r in recs])

# ---------- FD2: empirical spectrum ----------
fig, ax = plt.subplots(figsize=(6.4, 4.0))
for axname in AXES:
    m = np.array([r["axis"] == axname for r in recs])
    x = float(np.median(surf[m]))                      # measured surface step
    y = 1.0 - float(np.median(sims[m]))                # embedding distance proxy
    ans = 0.0 if axname.startswith("P") else 1.0
    c = GROUPC[axname]
    ax.errorbar(x, y, xerr=[[x - np.percentile(surf[m], 25)],
                            [np.percentile(surf[m], 75) - x]],
                yerr=[[y - (1 - np.percentile(sims[m], 75))],
                      [(1 - np.percentile(sims[m], 25)) - y]],
                fmt="o", ms=9, color=c, capsize=3, lw=1.2)
    dy = 0.012 if axname not in ("N3", "N5") else -0.020
    ha = "left"
    ax.annotate(axname, (x, y), xytext=(6, 6 if dy > 0 else -14),
                textcoords="offset points", fontsize=9, color=c, ha=ha)
ax.set_xlabel("measured surface step (1 − word Jaccard), median with IQR",
              fontsize=9, color=MUT)
ax.set_ylabel("embedding distance (1 − cosine, BGE-M3), median with IQR",
              fontsize=9, color=MUT)
style(ax); ax.grid(color=GRID, lw=0.6); ax.set_axisbelow(True)
ax.set_title("The designed spectrum, recovered from data: embeddings track surface\n"
             "form — cliff axes (orange, answer flips) sit closest to the origin",
             fontsize=9.8, loc="left", color=INK)
fig.tight_layout()
for ext in ("pdf", "png"):
    fig.savefig(FIG / f"fd2_empirical_spectrum.{ext}", dpi=200, bbox_inches="tight")
plt.close(fig); print("FD2 done")

# ---------- FD3: similarity distributions per axis (HIT ref band vs MISS) ----------
fig, axes2 = plt.subplots(2, 3, figsize=(8.6, 4.4), sharex=True, sharey=True)
hit_s = sims[np.array([r["expected_label"] == "HIT" for r in recs])]
bins = np.linspace(0.55, 1.0, 46)
for k, axname in enumerate(["N1", "N2", "N3", "N4", "N5", "N6"]):
    ax = axes2[k // 3][k % 3]
    m = np.array([r["axis"] == axname for r in recs])
    ax.hist(hit_s, bins=bins, density=True, color=GREEN, alpha=0.35,
            label="same answer (P1–P3)")
    ax.hist(sims[m], bins=bins, density=True, color=GROUPC[axname], alpha=0.55,
            label=f"{axname} (different answer)")
    ax.set_title(axname, fontsize=9.5, color=GROUPC[axname])
    style(ax)
    if k == 0:
        ax.legend(frameon=False, fontsize=6.6, loc="upper left")
    if k // 3 == 1:
        ax.set_xlabel("cosine similarity", fontsize=8.5, color=MUT)
fig.suptitle("Where the irreducible overlap lives: different-answer pairs (colored) "
             "inside the same-answer distribution (green), BGE-M3",
             fontsize=9.8, color=INK, x=0.02, ha="left")
fig.tight_layout(rect=(0, 0, 1, 0.93))
for ext in ("pdf", "png"):
    fig.savefig(FIG / f"fd3_overlap_distributions.{ext}", dpi=200, bbox_inches="tight")
plt.close(fig); print("FD3 done")
