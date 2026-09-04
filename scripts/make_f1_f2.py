#!/usr/bin/env python3
"""F1 (cliff vs slope concept) and F2 (taxonomy on the answer/surface spectrum)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

FIG = Path(__file__).resolve().parents[2] / "paper" / "figures"
INK, MUT, BLUE, ORANGE, GREEN = "#1a2733", "#5b6b7a", "#3b6fb6", "#c2571f", "#3d8f5f"

# ---------- F1: surface distance vs answer change — anisotropy ----------
fig, ax = plt.subplots(figsize=(6.8, 3.2))
ax.axis("off")
# seed at center-left
ax.scatter([0.08], [0.5], s=140, color=INK, zorder=5)
ax.annotate("seed:\n“deadline for\nAssignment 1?”", (0.08, 0.5), xytext=(0.02, 0.76),
            fontsize=8.5, color=INK, ha="left")
# invariant direction: long arrow, same answer
ax.annotate("", xy=(0.62, 0.80), xytext=(0.10, 0.53),
            arrowprops=dict(arrowstyle="-|>", color=GREEN, lw=2))
ax.scatter([0.62], [0.80], s=110, color=GREEN, zorder=5)
ax.annotate("“as1 deadline khi nao v”\nHUGE surface step — SAME answer",
            (0.63, 0.80), fontsize=8.5, color=GREEN, va="center")
# cliff direction: tiny arrow, answer flips
ax.annotate("", xy=(0.20, 0.38), xytext=(0.10, 0.47),
            arrowprops=dict(arrowstyle="-|>", color=ORANGE, lw=2))
ax.scatter([0.20], [0.38], s=110, color=ORANGE, zorder=5)
ax.annotate("“deadline for Assignment 2?”\nONE-CHARACTER step — answer TOTALLY different",
            (0.22, 0.36), fontsize=8.5, color=ORANGE, va="center")
ax.text(0.02, 0.06, "Embeddings are trained to be smooth: nearby text → nearby vectors.\n"
                    "Answer equivalence is not smooth: some directions are cliffs, others are plains.",
        fontsize=8.5, color=MUT)
ax.set_xlim(0, 1); ax.set_ylim(0, 1)
ax.set_title("Surface distance is not answer distance", fontsize=10.5, loc="left", color=INK)
fig.tight_layout()
for ext in ("pdf", "png"):
    fig.savefig(FIG / f"f1_cliff_concept.{ext}", dpi=200, bbox_inches="tight")
print("F1 done")

# ---------- F2: nine axes on the answer-step / surface-step spectrum ----------
AX = [("P3", 0.92, 0.02, "surface noise"), ("P2", 0.70, 0.02, "syntactic"),
      ("P1", 0.45, 0.02, "lexical"),
      ("N1", 0.22, 0.45, "aspect"), ("N2", 0.20, 0.55, "scope"),
      ("N6", 0.30, 0.88, "presupposition"),
      ("N3", 0.06, 0.97, "entity"), ("N5", 0.06, 0.90, "quantifier"),
      ("N4", 0.05, 1.0, "polarity")]
fig, ax = plt.subplots(figsize=(6.2, 4.0))
for name, sx, ay, lbl in AX:
    grp = GREEN if name.startswith("P") else (BLUE if name in ("N1", "N2") else ORANGE)
    ax.scatter([sx], [ay], s=120, color=grp, zorder=5)
    dx = 0.025 if name != "N4" else 0.02
    ax.annotate(f"{name} {lbl}", (sx, ay), xytext=(sx + dx, ay + 0.015), fontsize=8.5, color=grp)
ax.axhspan(-0.05, 0.12, color=GREEN, alpha=0.07)
ax.axhspan(0.35, 0.65, color=BLUE, alpha=0.06)
ax.axhspan(0.8, 1.08, color=ORANGE, alpha=0.07)
ax.text(0.99, 0.05, "invariant: cache MUST hit", fontsize=8.5, color=GREEN, ha="right")
ax.text(0.99, 0.50, "slope: must miss, fuzzy boundary", fontsize=8.5, color=BLUE, ha="right")
ax.text(0.99, 0.95, "cliff: minimal edit flips the answer", fontsize=8.5, color=ORANGE, ha="right")
ax.set_xlabel("surface step (how much the text changes)", fontsize=9, color=MUT)
ax.set_ylabel("answer step (how much the correct answer changes)", fontsize=9, color=MUT)
ax.set_xlim(0, 1.02); ax.set_ylim(-0.05, 1.08)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
for s in ("left", "bottom"):
    ax.spines[s].set_color(MUT)
ax.tick_params(colors=MUT, labelsize=8)
ax.set_title("The nine axes are one spectrum, not a list", fontsize=10.5, loc="left", color=INK)
fig.tight_layout()
for ext in ("pdf", "png"):
    fig.savefig(FIG / f"f2_taxonomy_spectrum.{ext}", dpi=200, bbox_inches="tight")
print("F2 done")
