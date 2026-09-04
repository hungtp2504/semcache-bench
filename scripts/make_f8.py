#!/usr/bin/env python3
"""F8: systematic characterization of order dependence (4 panels)."""
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

REPO = Path(__file__).resolve().parents[1]
FIG = REPO.parent / "paper" / "figures"
INK, MUT, GRID = "#1a2733", "#5b6b7a", "#e3e8ec"
BLUE, ORANGE, GREEN = "#3b6fb6", "#c2571f", "#3d8f5f"
o = json.loads((REPO / "results" / "order_systematic.json").read_text())

def style(ax):
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    for s in ("left", "bottom"): ax.spines[s].set_color(MUT)
    ax.tick_params(colors=MUT, labelsize=8)
    ax.grid(axis="y", color=GRID, lw=0.6); ax.set_axisbelow(True)

fig, axes = plt.subplots(1, 4, figsize=(11.2, 2.9))

# (a) OS vs workload size
ax = axes[0]
sz = o["sweeps"]["size"]
ax.plot([r["N"] for r in sz], [r["OS"]*100 for r in sz], "-o", color=BLUE, lw=2, ms=5)
ax.set_xscale("log"); ax.set_xlabel("workload size N", fontsize=8.5, color=MUT)
ax.set_ylabel("order-dependent queries (%)", fontsize=8.5, color=MUT)
ax.set_title("(a) vs. workload size", fontsize=9.5, color=INK)
ax.set_ylim(0, 60); style(ax)

# (b) OS vs tau, 3 encoders
ax = axes[1]
for (name, rows), col in zip(o["sweeps"]["tau"].items(), (BLUE, ORANGE, GREEN)):
    ax.plot([r["tau"] for r in rows], [r["OS"]*100 for r in rows], "-", lw=2,
            color=col, label=name)
ax.set_xlabel("threshold τ", fontsize=8.5, color=MUT)
ax.set_title("(b) vs. threshold, 3 encoders", fontsize=9.5, color=INK)
ax.legend(frameon=False, fontsize=7.5, loc="lower left")
ax.set_ylim(0, 100); style(ax)

# (c) OS vs Zipf skew
ax = axes[2]
z = o["sweeps"]["zipf"]
ax.plot([r["alpha"] for r in z], [r["OS"]*100 for r in z], "-o", color=BLUE, lw=2, ms=5)
ax.set_xlabel("workload skew  Zipf α", fontsize=8.5, color=MUT)
ax.set_title("(c) vs. arrival skew", fontsize=9.5, color=INK)
ax.set_ylim(0, 60); style(ax)

# (d) OS vs eviction
ax = axes[3]
ev = o["sweeps"]["eviction"]
labels, vals = [], []
labels.append("unbounded"); vals.append(ev[0]["OS"]*100)
for r in ev[1:]:
    labels.append(f"{r['policy'].upper()}-{r['capacity']}"); vals.append(r["OS"]*100)
xs = np.arange(len(labels))
ax.bar(xs, vals, 0.62, color=["#9db4c8"] + [BLUE]*3 + [GREEN]*3)
ax.set_xticks(xs, labels, rotation=45, ha="right", fontsize=7)
ax.set_title("(d) vs. eviction policy", fontsize=9.5, color=INK)
ax.set_ylim(0, 60); style(ax)

fig.suptitle("Order dependence is intrinsic: stable across size, skew, and eviction; governed by τ and encoder  (BGE-M3, τ=0.90 unless varied; 50 orders)",
             fontsize=9.5, color=INK, x=0.01, ha="left")
fig.tight_layout(rect=(0, 0, 1, 0.92))
for ext in ("pdf", "png"):
    fig.savefig(FIG / f"f8_order_characterization.{ext}", dpi=200, bbox_inches="tight")
print("F8 done")
