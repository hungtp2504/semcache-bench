#!/usr/bin/env python3
"""Illustration figures: F1 redesign (no text/graphic overlap), F9 order-dependence
timelines, F10 two-tier architecture, F11 decision procedure flowchart."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from pathlib import Path

FIG = Path(__file__).resolve().parents[2] / "paper" / "figures"
INK, MUT = "#1a2733", "#5b6b7a"
BLUE, ORANGE, GREEN, RED, LBLUE = "#3b6fb6", "#c2571f", "#3d8f5f", "#a8323e", "#9db4c8"

def box(ax, x, y, w, h, text, fc, ec, fs=8.5, tc=INK, lw=1.2):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.10",
                                fc=fc, ec=ec, lw=lw))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=fs, color=tc, linespacing=1.4)

def arr(ax, x1, y1, x2, y2, color=MUT, lw=1.6, style="-|>", ls="-"):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style, color=color,
                                 lw=lw, linestyle=ls, mutation_scale=13))

def save(fig, stem):
    for ext in ("pdf", "png"):
        fig.savefig(FIG / f"{stem}.{ext}", dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(stem, "done")

# ============ F1 redesign: generous whitespace, zero crossings ============
fig, ax = plt.subplots(figsize=(7.4, 3.4))
ax.axis("off"); ax.set_xlim(0, 10); ax.set_ylim(0, 6)
seed = (2.2, 2.6)
ax.scatter(*seed, s=170, color=INK, zorder=5)
ax.text(seed[0] - 0.35, seed[1], "seed\n“deadline for\nAssignment 1?”",
        ha="right", va="center", fontsize=8.5, color=INK, linespacing=1.4)
# green: long arrow up-right; label block fully right of dot, clear of arrow
g = (7.0, 4.8)
arr(ax, seed[0] + 0.22, seed[1] + 0.18, g[0] - 0.18, g[1] - 0.12, color=GREEN, lw=2.2)
ax.scatter(*g, s=140, color=GREEN, zorder=5)
ax.text(g[0] + 0.35, g[1] + 0.05, "“as1 deadline khi nao v”", fontsize=9,
        color=GREEN, va="center")
ax.text(g[0] + 0.35, g[1] - 0.62, "huge surface step — SAME answer", fontsize=8.5,
        color=GREEN, va="center")
ax.text(4.6, 4.35, "invariance", fontsize=8.5, color=GREEN, style="italic",
        rotation=23, rotation_mode="anchor")
# orange: tiny arrow down-right; labels below-right, clear of everything
o = (3.6, 1.7)
arr(ax, seed[0] + 0.2, seed[1] - 0.16, o[0] - 0.16, o[1] + 0.14, color=ORANGE, lw=2.2)
ax.scatter(*o, s=140, color=ORANGE, zorder=5)
ax.text(o[0] + 0.35, o[1] + 0.05, "“deadline for Assignment 2?”", fontsize=9,
        color=ORANGE, va="center")
ax.text(o[0] + 0.35, o[1] - 0.62, "one-character step — answer TOTALLY different",
        fontsize=8.5, color=ORANGE, va="center")
ax.text(2.75, 2.45, "cliff", fontsize=8.5, color=ORANGE, style="italic",
        rotation=-33, rotation_mode="anchor")
ax.text(0.15, 0.25, "Embeddings are trained for smoothness (nearby text → nearby "
                    "vectors); answer equivalence has cliffs.",
        fontsize=8.5, color=MUT)
ax.set_title("Surface distance is not answer distance", fontsize=10.5,
             loc="left", color=INK)
save(fig, "f1_cliff_concept")

# ============ F9: order dependence — two timelines ============
fig, ax = plt.subplots(figsize=(7.6, 4.6))
ax.axis("off"); ax.set_xlim(0, 12); ax.set_ylim(0, 9.6)
ax.text(0.1, 9.1, "sim(A,B) = 0.93 > τ      sim(B,C) = 0.93 > τ      "
                  "sim(A,C) = 0.84 ≤ τ", fontsize=9.5, color=INK)
def timeline(y, title, events):
    ax.text(0.1, y + 1.05, title, fontsize=9.5, color=INK, style="italic")
    arr(ax, 0.3, y, 11.7, y, color=MUT, lw=1.2)
    x = 1.6
    for name, action, color, note in events:
        ax.scatter([x], [y], s=95, color=color, zorder=5)
        ax.text(x, y + 0.30, name, ha="center", va="bottom", fontsize=10, color=color)
        ax.text(x, y - 0.35, action, ha="center", va="top", fontsize=8,
                color=color, linespacing=1.35)
        if note:
            ax.text(x, y - 1.55, note, ha="center", va="top", fontsize=8.5, color=RED)
        x += 3.6
timeline(6.6, "Arrival order 1:  A, B, C",
         [("A", "miss → LLM\nstore (A, ans$_A$)", MUT, ""),
          ("B", "hits A → serves ans$_A$\n(B not stored)", BLUE, ""),
          ("C", "no match (0.84 ≤ τ)\nmiss → LLM → ans$_C$", GREEN, "C gets its own answer ✓")])
timeline(2.6, "Arrival order 2:  B, C, A",
         [("B", "miss → LLM\nstore (B, ans$_B$)", MUT, ""),
          ("C", "hits B (0.93 > τ)\nserves ans$_B$", ORANGE, "C gets B's answer ✗"),
          ("A", "hits B → serves ans$_B$", BLUE, "")])
ax.set_title("Non-transitivity makes the served answer depend on arrival order "
             "(Proposition 1)", fontsize=10.5, loc="left", color=INK)
save(fig, "f9_order_timelines")

# ============ F10: two-tier architecture ============
fig, ax = plt.subplots(figsize=(7.8, 3.6))
ax.axis("off"); ax.set_xlim(0, 13); ax.set_ylim(0, 6.8)
box(ax, 0.2, 2.8, 2.0, 1.2, "incoming\nquery $q_i$", "#f4f6f8", MUT)
arr(ax, 2.3, 3.4, 3.1, 3.4)
box(ax, 3.2, 2.8, 2.5, 1.2, "tier 1: bi-encoder\nsim to best stored\n(1.9 ms)", "#e8eef6", BLUE, fs=8)
# three outcomes stacked on the right of tier1
arr(ax, 5.8, 3.85, 6.7, 5.35)
box(ax, 6.8, 5.0, 2.6, 0.95, "sim $> \\tau_{hi}$ (confident)\nserve cached answer", "#eaf3ee", GREEN, fs=8)
arr(ax, 5.8, 3.4, 6.7, 3.4)
box(ax, 6.8, 2.85, 2.6, 1.1, "danger band $[\\tau_{lo}, \\tau_{hi}]$\n49% of pairs live here", "#fdf1e7", ORANGE, fs=8)
arr(ax, 5.8, 2.95, 6.7, 1.35)
box(ax, 6.8, 0.6, 2.6, 0.95, "sim $< \\tau_{lo}$ (confident)\ncall the LLM", "#f4f6f8", MUT, fs=8)
# tier 2 to the right of the band
arr(ax, 9.5, 3.4, 10.2, 3.4)
box(ax, 10.3, 2.75, 2.5, 1.3, "tier 2 verifier\nreads BOTH texts\nCE 3.8 ms / LLM ~1.4 s", "#e8eef6", BLUE, fs=8)
arr(ax, 11.55, 4.1, 9.5, 5.45, color=GREEN, lw=1.4)
ax.text(10.9, 5.0, "SERVE", fontsize=8, color=GREEN, ha="center")
arr(ax, 11.55, 2.7, 9.5, 1.1, color=RED, lw=1.4)
ax.text(10.95, 1.7, "REGENERATE", fontsize=8, color=RED, ha="center")
ax.text(0.2, 0.15, "False hits among band pairs: 27.5% (no verifier) → 18.4% (cross-encoder) → 2.7% (LLM verifier).",
        fontsize=8.5, color=MUT)
ax.set_title("The two-tier remedy: verify only where the threshold cannot decide",
             fontsize=10.5, loc="left", color=INK)
save(fig, "f10_two_tier")

# ============ F11: decision procedure flowchart ============
fig, ax = plt.subplots(figsize=(7.4, 4.2))
ax.axis("off"); ax.set_xlim(0, 12); ax.set_ylim(0, 8)
box(ax, 3.7, 6.7, 4.6, 1.0, "sample your workload's query pairs;\nclassify against the taxonomy", "#f4f6f8", MUT)
arr(ax, 6.0, 6.65, 6.0, 6.05)
box(ax, 3.7, 4.9, 4.6, 1.05, "cliff share $c$ high?\nerror cost $\\rho$ high?", "#e8eef6", BLUE)
# left: no
arr(ax, 3.6, 5.4, 2.3, 4.0, color=GREEN)
ax.text(1.75, 4.55, "no / no", fontsize=8.5, color=GREEN)
box(ax, 0.4, 2.8, 3.4, 1.15, "tuning suffices:\ncalibrate $\\tau^*(\\rho)$ from the\nutility model; re-check on drift", "#eaf3ee", GREEN, fs=8)
# right: yes
arr(ax, 8.4, 5.4, 9.7, 4.0, color=ORANGE)
ax.text(9.35, 4.85, "either yes", fontsize=8.5, color=ORANGE)
box(ax, 8.2, 2.8, 3.5, 1.15, "tuning is futile (IO floor):\nadd a tier-2 verifier in the band,\nor key on discrete slots", "#fdf1e7", ORANGE, fs=8)
# bottom: reproducibility
arr(ax, 6.0, 4.85, 6.0, 1.85)
box(ax, 3.4, 0.55, 5.2, 1.25, "answers must be reproducible\n(compliance, healthcare, grading)?\n→ a bare threshold cache is disqualified:\norder dependence is intrinsic", "#f7ecec", RED, fs=8)
ax.set_title("Decision procedure for practitioners", fontsize=10.5, loc="left", color=INK)
save(fig, "f11_decision_procedure")
