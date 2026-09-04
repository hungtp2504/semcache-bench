#!/usr/bin/env python3
"""Figures F4 (instability & false answers vs tau), F5 (tau* vs rho per domain),
F6 (verifier improvement by axis group — the C4 figure). From final results JSONs.

Design (dataviz): categorical hues fixed per entity, direct labels, one axis per
chart, recessive grid, neutral ink."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

REPO = Path(__file__).resolve().parents[1]
FIG = REPO.parent / "paper" / "figures"
INK, MUT = "#1a2733", "#5b6b7a"
CAT = ["#3b6fb6", "#c2571f", "#3d8f5f", "#8256a8", "#a8323e"]  # fixed order

fa = json.loads((REPO / "results" / "final_analysis.json").read_text())
r5 = json.loads((REPO / "results" / "rq5_rq4.json").read_text())


def style(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(MUT)
    ax.tick_params(colors=MUT, labelsize=9)
    ax.grid(axis="y", color="#e3e8ec", lw=0.7)
    ax.set_axisbelow(True)


# ---------- F4: instability + false-answer rate vs tau (modern encoders) ----------
MODERN = {"BAAI/bge-m3": "BGE-M3", "sentence-transformers/all-MiniLM-L6-v2": "MiniLM-L6",
          "nomic-ai/nomic-embed-text-v1.5": "Nomic-v1.5"}
fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.4), sharex=True)
for k, (metric, title) in enumerate((("answer_instability", "Order-dependent answers"),
                                     ("false_answer_rate_mean", "Wrong answers served"))):
    ax = axes[k]
    for i, (mid, label) in enumerate(MODERN.items()):
        rb = fa["models"][mid]["rq3b"]
        taus = sorted(rb, key=float)
        ys = [rb[t][metric] * 100 for t in taus]
        ax.plot([float(t) for t in taus], ys, "-o", color=CAT[i], lw=2, ms=5, label=label)
        ax.annotate(label, (float(taus[-1]), ys[-1]), xytext=(4, 0),
                    textcoords="offset points", fontsize=8.5, color=CAT[i], va="center")
    ax.axvline(0.9, color=MUT, lw=0.8, ls=":")
    ax.text(0.9, ax.get_ylim()[1] * 0.02, " recommended τ=0.9", fontsize=7.5, color=MUT)
    ax.set_title(title, fontsize=10, color=INK, loc="left")
    ax.set_xlabel("threshold τ", fontsize=9, color=MUT)
    ax.set_ylabel("% of queries", fontsize=9, color=MUT)
    style(ax)
    ax.set_xlim(0.84, 0.985)
fig.suptitle("")
fig.tight_layout()
for ext in ("pdf", "png"):
    fig.savefig(FIG / f"f4_order_dependence.{ext}", dpi=200, bbox_inches="tight")
print("F4 done")

# ---------- F5: tau*(rho) per domain ----------
fig, ax = plt.subplots(figsize=(6.4, 3.6))
DOM_LABEL = {"academic_nlp": "academic NLP", "medical": "medical",
             "tech_docs": "tech docs", "university_admin": "university admin",
             "vietnamese_admin_edu": "Vietnamese admin"}
for i, (dom, curve) in enumerate(sorted(r5["rq4_tau_star"].items())):
    rhos = [c["rho"] for c in curve]
    ts = [c["tau_star"] for c in curve]
    ax.plot(rhos, ts, "-", color=CAT[i], lw=2, label=DOM_LABEL[dom])
    ax.annotate(DOM_LABEL[dom], (rhos[-1], ts[-1]), xytext=(5, 0),
                textcoords="offset points", fontsize=8, color=CAT[i], va="center")
ax.set_xscale("log")
ax.set_xlabel("cost ratio ρ = C_err / C_llm (log scale)", fontsize=9, color=MUT)
ax.set_ylabel("optimal threshold τ*", fontsize=9, color=MUT)
ax.set_title("The optimal threshold depends on domain and error cost (RQ4)",
             fontsize=10, color=INK, loc="left")
style(ax)
ax.set_xlim(1, 4000)
fig.tight_layout()
for ext in ("pdf", "png"):
    fig.savefig(FIG / f"f5_tau_star.{ext}", dpi=200, bbox_inches="tight")
print("F5 done")

# ---------- F6: C4 — false-hit by axis group across configs ----------
c1 = r5["configs"]["threshold_only"]["0.89"]
c2 = r5["configs"]["cross_encoder"]["rates"]
groups = ["slope", "cliff"]
fig, ax = plt.subplots(figsize=(6.2, 3.4))
x = np.arange(2)
w = 0.38
b1 = [c1[f"false_hit_{g}"] * 100 for g in groups]
b2 = [c2[f"false_hit_{g}"] * 100 for g in groups]
r_1 = ax.bar(x - w / 2, b1, w, color="#9db4c8", label="threshold only (τ*=0.89)")
r_2 = ax.bar(x + w / 2, b2, w, color=CAT[0], label="+ cross-encoder verifier")
for r in list(r_1) + list(r_2):
    ax.annotate(f"{r.get_height():.1f}%", (r.get_x() + r.get_width() / 2, r.get_height()),
                ha="center", va="bottom", fontsize=9, color=INK)
for i, g in enumerate(groups):
    rel = (b1[i] - b2[i]) / b1[i] * 100
    ax.annotate(f"−{rel:.0f}%", (i + w / 2, b2[i] / 2), ha="center", fontsize=10,
                color="white", fontweight="bold")
ax.set_xticks(x, ["slope axes (N1–N2)\nintrinsically fuzzy", "cliff axes (N3–N6)\ndiscrete flips"],
              fontsize=9)
ax.set_ylabel("false-hit rate (%)", fontsize=9, color=MUT)
ax.set_title("Verification helps disproportionately on cliff axes (C4)",
             fontsize=10, color=INK, loc="left")
ax.legend(frameon=False, fontsize=8.5, loc="upper left")
style(ax)
fig.tight_layout()
for ext in ("pdf", "png"):
    fig.savefig(FIG / f"f6_c4_asymmetry.{ext}", dpi=200, bbox_inches="tight")
print("F6 done")
