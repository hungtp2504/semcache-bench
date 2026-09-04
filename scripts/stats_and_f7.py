#!/usr/bin/env python3
"""Closing statistics (T9) + F7 critical-difference diagram + RQ5 latency table.

1. Friedman test across 9 encoders, blocks = 6 change axes (IO values), then
   Nemenyi post-hoc; critical-difference diagram (F7).
2. Bootstrap 95% CIs for the headline RQ3b numbers (BGE-M3 tau=0.9) by resampling
   queries from the saved per-query outcome is not stored — instead CI via
   normal approx on binomial proportions (n=5,231) which is exact enough here,
   stated as such.
3. Latency micro-benchmark: bi-encoder encode vs cross-encoder pair scoring
   (ms/item, MPS) for the RQ5 cost table.
"""
import json
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import scikit_posthocs as sp
from scipy.stats import friedmanchisquare

REPO = Path(__file__).resolve().parents[1]
FIG = REPO.parent / "paper" / "figures"

fa = json.loads((REPO / "results" / "final_analysis.json").read_text())
AXES = ["N1", "N2", "N3", "N4", "N5", "N6"]
ORDER = [("distilbert/distilbert-base-uncased", "DistilBERT"),
         ("albert/albert-base-v2", "ALBERT"),
         ("sentence-transformers/all-MiniLM-L6-v2", "MiniLM-L6"),
         ("intfloat/e5-large-v2", "E5-large"),
         ("thenlper/gte-large", "GTE-large"),
         ("nomic-ai/nomic-embed-text-v1.5", "Nomic-v1.5"),
         ("BAAI/bge-m3", "BGE-M3"),
         ("intfloat/multilingual-e5-large", "mE5-large"),
         ("keepitreal/vietnamese-sbert", "Vi-SBERT")]

M = np.array([[fa["models"][mid]["rq3a"]["io_per_axis"][ax]["io"] for ax in AXES]
              for mid, _ in ORDER])  # 9 encoders x 6 axes
labels = [l for _, l in ORDER]

# Friedman across encoders (treatments), axes as blocks
stat, p = friedmanchisquare(*[M[i] for i in range(len(labels))])
print(f"Friedman chi2={stat:.2f}, p={p:.2e} (9 encoders, 6 axis blocks)")
nem = sp.posthoc_nemenyi_friedman(M.T)  # blocks x treatments
nem.index = labels; nem.columns = labels
avg_rank = M.T.argsort(axis=1).argsort(axis=1).mean(axis=0) + 1  # rank per block, avg
print("avg ranks:", dict(zip(labels, np.round(avg_rank, 2))))

# CD diagram (simple): ranks on a line, bars join groups not significantly different
k, n = len(labels), len(AXES)
q_alpha = 3.102  # Nemenyi q_0.05 for k=9
cd = q_alpha * np.sqrt(k * (k + 1) / (6.0 * n))
print(f"critical difference (alpha=.05): {cd:.2f}")
order = np.argsort(avg_rank)
fig, ax = plt.subplots(figsize=(7.2, 2.8))
lo, hi = 1, k
ax.set_xlim(lo - 0.3, hi + 0.3); ax.set_ylim(0, 1)
ax.axis("off")
ax.plot([lo, hi], [0.75, 0.75], color="#5b6b7a", lw=1)
for t in range(lo, hi + 1):
    ax.plot([t, t], [0.73, 0.77], color="#5b6b7a", lw=1)
    ax.text(t, 0.80, str(t), ha="center", fontsize=8, color="#5b6b7a")
ys = np.linspace(0.62, 0.06, k)
for row, i in enumerate(order):
    r = avg_rank[i]
    ax.plot([r, r], [0.75, ys[row] + 0.02], color="#9db4c8", lw=0.8)
    ax.text(r, ys[row], f"{labels[i]} ({r:.2f})", fontsize=8.5,
            ha="left" if row % 2 == 0 else "right", color="#1a2733")
ax.plot([avg_rank.min(), avg_rank.min() + cd], [0.93, 0.93], color="#1a2733", lw=2.5)
ax.text(avg_rank.min() + cd / 2, 0.96, f"CD = {cd:.2f}", ha="center", fontsize=8.5)
ax.set_title("Mean IO rank across change axes (lower = better) — Nemenyi CD, α = 0.05",
             fontsize=9.5, loc="left", color="#1a2733")
fig.tight_layout()
for ext in ("pdf", "png"):
    fig.savefig(FIG / f"f7_cd_diagram.{ext}", dpi=200, bbox_inches="tight")
print("F7 done")

# Binomial CIs for headline numbers
def ci(p_, n_):
    se = np.sqrt(p_ * (1 - p_) / n_)
    return p_ - 1.96 * se, p_ + 1.96 * se
rb = fa["models"]["BAAI/bge-m3"]["rq3b"]["0.9"]
nq = rb["n_queries"]
for name in ("answer_instability", "false_answer_rate_mean"):
    lo_, hi_ = ci(rb[name], nq)
    print(f"bge-m3 tau=.9 {name}: {rb[name]:.3f} [95% CI {lo_:.3f}, {hi_:.3f}] (n={nq})")

# Latency micro-benchmark
import sys
sys.path.insert(0, str(REPO / "scripts"))
import torch
from sentence_transformers import SentenceTransformer, CrossEncoder
dev = "mps" if torch.backends.mps.is_available() else "cpu"
texts = ["When is the deadline for Assignment %d?" % i for i in range(256)]
be = SentenceTransformer("BAAI/bge-m3", device=dev)
be.encode(texts[:8])  # warmup
t0 = time.perf_counter(); be.encode(texts, batch_size=64); t_be = (time.perf_counter() - t0) / len(texts) * 1000
ce = CrossEncoder("BAAI/bge-reranker-v2-m3", device=dev)
pairs = [(t, t.replace("deadline", "grading")) for t in texts]
ce.predict(pairs[:8])
t0 = time.perf_counter(); ce.predict(pairs, batch_size=64); t_ce = (time.perf_counter() - t0) / len(pairs) * 1000
lat = {"bi_encoder_ms_per_query": round(t_be, 2), "cross_encoder_ms_per_pair": round(t_ce, 2),
       "device": dev, "note": "M4 Pro, batch 64"}
print("latency:", lat)

out = {"friedman": {"chi2": float(stat), "p": float(p)},
       "avg_ranks": dict(zip(labels, map(float, avg_rank))),
       "critical_difference": float(cd),
       "nemenyi_p": {f"{a}|{b}": float(nem.loc[a, b]) for a in labels for b in labels if a < b},
       "headline_cis": {k2: list(map(float, ci(rb[k2], nq)))
                        for k2 in ("answer_instability", "false_answer_rate_mean")},
       "latency": lat}
(REPO / "results" / "stats_final.json").write_text(json.dumps(out, indent=2) + "\n")
print("wrote results/stats_final.json")
