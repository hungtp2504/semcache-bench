#!/usr/bin/env python3
"""Central figure (review point 8): similarity pipeline vs answer equivalence."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from pathlib import Path

FIG = Path(__file__).resolve().parents[2] / "paper" / "figures"
INK, MUT, BLUE, ORANGE, GREEN, RED = "#1a2733", "#5b6b7a", "#3b6fb6", "#c2571f", "#3d8f5f", "#a8323e"

fig, ax = plt.subplots(figsize=(7.2, 3.6))
ax.axis("off"); ax.set_xlim(0, 10); ax.set_ylim(0, 6.4)

def box(x, y, w, h, text, fc, ec, fs=9, tc=INK):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.12",
                                fc=fc, ec=ec, lw=1.2))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=fs, color=tc, linespacing=1.4)

def arrow(x1, y1, x2, y2, color=MUT, style="-|>", lw=1.6, ls="-"):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style,
                                 color=color, lw=lw, linestyle=ls,
                                 mutation_scale=14))

# left column: what the cache computes (levels 1-2)
box(0.3, 4.9, 3.2, 1.1, "queries $q_i,\\ q_s$\n(level 1: lexical form $L$)", "#f4f6f8", MUT)
arrow(1.9, 4.85, 1.9, 4.15)
box(0.3, 3.0, 3.2, 1.1, "embedding space\nlevel 2: similarity $S(q_i,q_s)$\nsmooth, continuous", "#e8eef6", BLUE)
arrow(1.9, 2.95, 1.9, 2.25)
ax.text(2.05, 2.6, "threshold $\\tau$", fontsize=9, color=MUT, ha="left")
box(0.3, 1.1, 3.2, 1.1, "cache decision\nHIT / MISS", "#e8eef6", BLUE)

# right column: what correctness requires (level 3)
box(6.5, 3.0, 3.2, 1.1, "level 3: answer equivalence\n$E(q_i,q_s)$ --- binary, transitive", "#eaf3ee", GREEN)
arrow(8.1, 2.95, 8.1, 2.25)
box(6.5, 1.1, 3.2, 1.1, "ground truth\nSAME / DIFFERENT answer", "#eaf3ee", GREEN)

# the mismatch link
arrow(3.6, 1.65, 6.4, 1.65, color=RED, style="<|-|>", lw=2)
ax.text(5.0, 1.95, "$E \\not\\equiv S_{>\\tau}$", fontsize=11, color=RED, ha="center")
ax.text(5.0, 0.45, "irreducible overlap (no $\\tau$ separates)  +  non-transitivity (order dependence)",
        fontsize=8.5, color=RED, ha="center")
ax.text(5.15, 4.55, "the cache decides with level 2;\ncorrectness is defined at level 3",
        fontsize=9.5, color=INK, ha="center", style="italic", linespacing=1.5)
ax.set_title("Three levels of query relatedness --- and where semantic caching breaks",
             fontsize=10.5, loc="left", color=INK)
fig.tight_layout()
for ext in ("pdf", "png"):
    fig.savefig(FIG / f"f0_three_levels.{ext}", dpi=200, bbox_inches="tight")
print("central figure done")
