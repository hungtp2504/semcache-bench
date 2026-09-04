#!/usr/bin/env python3
"""Publication-quality regeneration of F1, F2, F4, F5, F6, F7 — collision-free.

Layout rules enforced: no text over text, no text over marks, labels either in
dedicated whitespace or in legends; consistent palette; recessive axes."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

REPO = Path(__file__).resolve().parents[1]
FIG = REPO.parent / "paper" / "figures"
INK, MUT, GRID = "#1a2733", "#5b6b7a", "#e3e8ec"
BLUE, ORANGE, GREEN, PURPLE, RED = "#3b6fb6", "#c2571f", "#3d8f5f", "#8256a8", "#a8323e"
plt.rcParams.update({"font.size": 9, "axes.titlesize": 10.5, "axes.titlelocation": "left",
                     "axes.titlecolor": INK, "text.color": INK})


def style(ax, ygrid=True):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(MUT)
    ax.tick_params(colors=MUT, labelsize=8.5)
    if ygrid:
        ax.grid(axis="y", color=GRID, lw=0.7)
    ax.set_axisbelow(True)


def save(fig, stem):
    for ext in ("pdf", "png"):
        fig.savefig(FIG / f"{stem}.{ext}", dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(stem, "done")


# ================= F1: concept =================
fig, ax = plt.subplots(figsize=(6.9, 3.1))
ax.axis("off"); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
seed = (0.10, 0.42)
ax.scatter(*seed, s=150, color=INK, zorder=5)
ax.text(0.02, 0.86, "seed: “deadline for Assignment 1?”",
        fontsize=9, color=INK, ha="left")
ax.plot([0.055, seed[0] - 0.004], [0.81, seed[1] + 0.045], color="#9db4c8", lw=0.8)
# invariant arrow (long)
g_end = (0.60, 0.72)
ax.annotate("", xy=g_end, xytext=(seed[0] + 0.015, seed[1] + 0.035),
            arrowprops=dict(arrowstyle="-|>", color=GREEN, lw=2))
ax.scatter(*g_end, s=120, color=GREEN, zorder=5)
ax.text(g_end[0] + 0.025, g_end[1] + 0.055, "“as1 deadline khi nao v”",
        fontsize=9, color=GREEN, ha="left")
ax.text(g_end[0] + 0.025, g_end[1] - 0.045, "huge surface step — SAME answer",
        fontsize=8.5, color=GREEN, ha="left")
# cliff arrow (tiny)
o_end = (0.235, 0.30)
ax.annotate("", xy=o_end, xytext=(seed[0] + 0.015, seed[1] - 0.03),
            arrowprops=dict(arrowstyle="-|>", color=ORANGE, lw=2))
ax.scatter(*o_end, s=120, color=ORANGE, zorder=5)
ax.text(o_end[0] + 0.03, o_end[1] + 0.045, "“deadline for Assignment 2?”",
        fontsize=9, color=ORANGE, ha="left")
ax.text(o_end[0] + 0.03, o_end[1] - 0.055, "one-character step — answer TOTALLY different",
        fontsize=8.5, color=ORANGE, ha="left")
ax.text(0.02, 0.02, "Embeddings are trained for smoothness (nearby text → nearby vectors);"
                    " answer equivalence has cliffs.", fontsize=8.5, color=MUT)
ax.set_title("Surface distance is not answer distance")
save(fig, "f1_cliff_concept")

# ================= F2: spectrum =================
AX = [  # (name, sx, ay, label, label dx, dy, ha)
    ("P1", 0.45, 0.02, "P1 lexical", 0, 0.07, "center"),
    ("P2", 0.70, 0.02, "P2 syntactic", 0, 0.07, "center"),
    ("P3", 0.92, 0.02, "P3 surface noise", 0, 0.07, "center"),
    ("N1", 0.22, 0.45, "N1 aspect", 0.03, -0.005, "left"),
    ("N2", 0.20, 0.55, "N2 scope", 0.03, 0.01, "left"),
    ("N6", 0.30, 0.86, "N6 presupposition", 0.03, -0.01, "left"),
    ("N3", 0.07, 0.955, "N3 entity", 0.03, -0.015, "left"),
    ("N5", 0.065, 0.875, "N5 quantifier", 0.03, -0.02, "left"),
    ("N4", 0.05, 1.03, "N4 polarity", 0.03, 0.005, "left"),
]
fig, ax = plt.subplots(figsize=(6.4, 4.2))
ax.axhspan(-0.06, 0.14, color=GREEN, alpha=0.07)
ax.axhspan(0.36, 0.66, color=BLUE, alpha=0.06)
ax.axhspan(0.80, 1.12, color=ORANGE, alpha=0.07)
# group captions in dedicated right-side whitespace, vertically centered in band
ax.text(0.02, 0.04, "INVARIANT\ncache must hit", fontsize=8, color=GREEN,
        ha="left", va="center", fontweight="bold", linespacing=1.3)
ax.text(1.03, 0.51, "SLOPE\nmust miss,\nfuzzy boundary", fontsize=8, color=BLUE,
        ha="right", va="center", fontweight="bold", linespacing=1.3)
ax.text(1.03, 0.70, "CLIFF\nminimal edit flips\nthe answer", fontsize=8, color=ORANGE,
        ha="right", va="bottom", fontweight="bold", linespacing=1.3)
for name, sx, ay, lbl, dx, dy, ha in AX:
    grp = GREEN if name.startswith("P") else (BLUE if name in ("N1", "N2") else ORANGE)
    ax.scatter([sx], [ay], s=130, color=grp, zorder=5)
    ax.text(sx + dx, ay + dy, lbl, fontsize=8.5, color=grp, ha=ha,
            va="bottom" if ha == "center" else "center")
ax.set_xlabel("surface step (how much the text changes)", fontsize=9, color=MUT)
ax.set_ylabel("answer step (how much the correct answer changes)", fontsize=9, color=MUT)
ax.set_xlim(0, 1.05); ax.set_ylim(-0.06, 1.12)
ax.set_yticks([0, 0.5, 1.0]); ax.set_xticks([0, 0.5, 1.0])
style(ax, ygrid=False)
ax.set_title("The nine axes are one spectrum, not a list")
save(fig, "f2_taxonomy_spectrum")

# ================= F4: order dependence =================
fa = json.loads((REPO / "results" / "final_analysis.json").read_text())
MODERN = [("BAAI/bge-m3", "BGE-M3", BLUE),
          ("sentence-transformers/all-MiniLM-L6-v2", "MiniLM-L6", ORANGE),
          ("nomic-ai/nomic-embed-text-v1.5", "Nomic-v1.5", GREEN)]
fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.3), sharex=True)
for k, (metric, title) in enumerate((("answer_instability", "Order-dependent answers"),
                                     ("false_answer_rate_mean", "Wrong answers served"))):
    ax = axes[k]
    for mid, label, col in MODERN:
        rb = fa["models"][mid]["rq3b"]
        taus = sorted(rb, key=float)
        ax.plot([float(t) for t in taus], [rb[t][metric] * 100 for t in taus],
                "-o", color=col, lw=2, ms=5, label=label)
    top = ax.get_ylim()[1]
    ax.axvline(0.9, color=MUT, lw=0.9, ls=":")
    ax.set_title(title)
    ax.set_xlabel("threshold τ", fontsize=9, color=MUT)
    if k == 0:
        ax.set_ylabel("% of queries", fontsize=9, color=MUT)
    style(ax)
    ax.set_xticks([0.85, 0.90, 0.95])
    ax.set_xlim(0.835, 0.965)
axes[0].annotate("recommended\nτ = 0.9", xy=(0.9, 58), xytext=(0.915, 72),
                 fontsize=8, color=MUT,
                 arrowprops=dict(arrowstyle="->", color=MUT, lw=0.8))
axes[0].legend(frameon=False, fontsize=8.5, loc="lower left")
fig.tight_layout()
save(fig, "f4_order_dependence")

# ================= F5: tau*(rho) =================
r5 = json.loads((REPO / "results" / "rq5_rq4.json").read_text())
DOMS = [("university_admin", "university admin", BLUE),
        ("academic_nlp", "academic NLP", ORANGE),
        ("tech_docs", "tech docs", GREEN),
        ("medical", "medical", PURPLE),
        ("vietnamese_admin_edu", "Vietnamese admin", RED)]
fig, ax = plt.subplots(figsize=(6.6, 3.6))
for dom, lbl, col in DOMS:
    curve = r5["rq4_tau_star"][dom]
    ax.plot([c["rho"] for c in curve], [c["tau_star"] for c in curve],
            "-", color=col, lw=2, label=lbl)
ax.set_xscale("log")
ax.set_xlabel("cost ratio ρ = C_err / C_llm (log scale)", fontsize=9, color=MUT)
ax.set_ylabel("optimal threshold τ*", fontsize=9, color=MUT)
ax.set_xlim(1, 1000)
ax.set_ylim(0.79, 1.005)
ax.legend(frameon=False, fontsize=8.5, loc="lower right", ncol=1,
          borderaxespad=1.2)
style(ax)
ax.set_title("The optimal threshold depends on domain and error cost (RQ4)")
save(fig, "f5_tau_star")

# ================= F6: C4 asymmetry =================
c1 = r5["configs"]["threshold_only"]["0.89"]
c2 = r5["configs"]["cross_encoder"]["rates"]
groups = ["slope", "cliff"]
b1 = [c1[f"false_hit_{g}"] * 100 for g in groups]
b2 = [c2[f"false_hit_{g}"] * 100 for g in groups]
fig, ax = plt.subplots(figsize=(6.2, 3.5))
x = np.arange(2); w = 0.36
r1 = ax.bar(x - w / 2, b1, w, color="#9db4c8", label="threshold only ($τ^*_{BA}$ = 0.89)")
r2 = ax.bar(x + w / 2, b2, w, color=BLUE, label="+ cross-encoder verifier")
for r in list(r1) + list(r2):
    ax.annotate(f"{r.get_height():.1f}%", (r.get_x() + r.get_width() / 2, r.get_height() + 0.5),
                ha="center", va="bottom", fontsize=9, color=INK)
for i in range(2):
    rel = (b1[i] - b2[i]) / b1[i] * 100
    ax.annotate(f"−{rel:.0f}%", (i + w / 2, b2[i] / 2), ha="center", va="center",
                fontsize=10.5, color="white", fontweight="bold")
ax.set_xticks(x, ["slope axes (N1–N2)\nintrinsically fuzzy",
                  "cliff axes (N3–N6)\ndiscrete flips"], fontsize=9)
ax.set_ylabel("false-hit rate (%)", fontsize=9, color=MUT)
ax.set_ylim(0, 38)   # headroom so the legend never touches the bars
ax.legend(frameon=False, fontsize=8.5, loc="upper left", ncol=1,
          bbox_to_anchor=(0.0, 1.0))
style(ax)
ax.set_title("Verification helps disproportionately on cliff axes (C4)")
save(fig, "f6_c4_asymmetry")

# ================= F7: CD diagram (proper two-column layout) =================
st = json.loads((REPO / "results" / "stats_final.json").read_text())
ranks = st["avg_ranks"]; cd = st["critical_difference"]
items = sorted(ranks.items(), key=lambda kv: kv[1])
k = len(items)
fig, ax = plt.subplots(figsize=(7.4, 3.0))
ax.axis("off")
ax.set_xlim(-2.2, 11.2); ax.set_ylim(-0.15, 1.18)
# axis line
ax.plot([1, 9], [0.86, 0.86], color=MUT, lw=1.2)
for t in range(1, 10):
    ax.plot([t, t], [0.84, 0.88], color=MUT, lw=1.2)
    ax.text(t, 0.93, str(t), ha="center", fontsize=8.5, color=MUT)
# CD bar
best = items[0][1]
ax.plot([best, best + cd], [1.08, 1.08], color=INK, lw=3, solid_capstyle="butt")
ax.text(best + cd / 2, 1.12, f"CD = {cd:.2f}", ha="center", fontsize=8.5, color=INK)
# left column = best half, right column = worst half, elbow connectors
left = items[: (k + 1) // 2]; right = items[(k + 1) // 2:]
ys_l = np.linspace(0.62, 0.02, len(left))
ys_r = np.linspace(0.02, 0.62, len(right))
for (name, r), y in zip(left, ys_l):
    ax.plot([r, r, -0.1], [0.84, y, y], color="#9db4c8", lw=0.9)
    ax.text(-0.25, y, f"{name} ({r:.2f})", ha="right", va="center", fontsize=8.5, color=INK)
for (name, r), y in zip(right[::-1], ys_r):
    ax.plot([r, r, 10.1], [0.84, y, y], color="#9db4c8", lw=0.9)
    ax.text(10.25, y, f"{name} ({r:.2f})", ha="left", va="center", fontsize=8.5, color=INK)
ax.set_title("Mean IO rank across change axes (lower = better), Nemenyi CD at α = .05", pad=14)
save(fig, "f7_cd_diagram")
