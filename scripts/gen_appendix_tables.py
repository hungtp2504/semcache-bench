#!/usr/bin/env python3
"""Generate real LaTeX tables for the appendix from results JSONs."""
import json
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO.parent / "paper" / "sections" / "appendix_tables.tex"
AXES = ["N1", "N2", "N3", "N4", "N5", "N6"]
ORDER = [("distilbert/distilbert-base-uncased", "DistilBERT"),
         ("albert/albert-base-v2", "ALBERT"),
         ("sentence-transformers/all-MiniLM-L6-v2", "MiniLM-L6"),
         ("intfloat/e5-large-v2", "E5-large-v2"),
         ("thenlper/gte-large", "GTE-large"),
         ("nomic-ai/nomic-embed-text-v1.5", "Nomic-v1.5"),
         ("BAAI/bge-m3", "BGE-M3"),
         ("intfloat/multilingual-e5-large", "mE5-large"),
         ("keepitreal/vietnamese-sbert", "Vi-SBERT")]
DOMS = [("university_admin", "univ.\\ admin"), ("academic_nlp", "acad.\\ NLP"),
        ("tech_docs", "tech docs"), ("medical", "medical"),
        ("vietnamese_admin_edu", "VN admin")]

fa = json.loads((REPO / "results" / "final_analysis.json").read_text())
r5 = json.loads((REPO / "results" / "rq5_rq4.json").read_text())
r6 = json.loads((REPO / "results" / "rq6.json").read_text())

L = []
# ---- Table C1: IO per encoder x axis ----
L.append(r"""\begin{table}[t]
\centering\small
\caption{Irreducible Overlap per encoder $\times$ change axis on the frozen
benchmark (numeric version of Figure~\ref{fig:io-heatmap}). Lower is better;
0.50 is chance.}
\label{tab:io-full}
\begin{tabular}{@{}l""" + "c" * 6 + r"""@{}}
\toprule
Encoder & N1 & N2 & N3 & N4 & N5 & N6 \\
\midrule""")
for mid, name in ORDER:
    io = fa["models"][mid]["rq3a"]["io_per_axis"]
    L.append(name + " & " + " & ".join(f"{io[a]['io']:.3f}" for a in AXES) + r" \\")
L.append(r"""\bottomrule
\end{tabular}
\end{table}""")

# ---- Table C2: IO per domain (BGE-M3) ----
per_dom = fa["models"]["BAAI/bge-m3"]["rq3a_per_domain"]
L.append(r"""\begin{table}[t]
\centering\small
\caption{Irreducible Overlap per domain $\times$ change axis for the
best-ranked encoder (BGE-M3).}
\label{tab:io-domain}
\begin{tabular}{@{}l""" + "c" * 6 + r"""@{}}
\toprule
Domain & N1 & N2 & N3 & N4 & N5 & N6 \\
\midrule""")
for dom, dname in DOMS:
    io = per_dom[dom]
    row = " & ".join(f"{io[a]['io']:.3f}" if a in io else "--" for a in AXES)
    L.append(dname + " & " + row + r" \\")
L.append(r"""\bottomrule
\end{tabular}
\end{table}""")

# ---- Table C3: tau* at selected rho ----
L.append(r"""\begin{table}[t]
\centering\small
\caption{Utility-optimal threshold $\tau^\ast$ per domain at selected cost
ratios $\rho$ (BGE-M3 tier-1; numeric version of Figure~\ref{fig:taustar}).}
\label{tab:taustar}
\begin{tabular}{@{}lcccc@{}}
\toprule
Domain & $\rho{=}1$ & $\rho{=}10$ & $\rho{=}100$ & $\rho{=}1000$ \\
\midrule""")
for dom, dname in DOMS:
    curve = {c["rho"]: c["tau_star"] for c in r5["rq4_tau_star"][dom]}
    def at(r):
        k = min(curve, key=lambda x: abs(x - r))
        return f"{curve[k]:.2f}"
    L.append(f"{dname} & {at(1)} & {at(10)} & {at(100)} & {at(1000)} \\\\")
L.append(r"""\bottomrule
\end{tabular}
\end{table}""")

# ---- Table C4: RQ5 configurations ----
c = r5["configs"]
t0 = c["threshold_only"]["0.89"]; ce = c["cross_encoder"]["rates"]; lv = c["llm_verifier"]
L.append(r"""\begin{table}[t]
\centering\small
\caption{RQ5: false-hit rates of the four cache configurations (tier-1 BGE-M3;
verifiers act on the danger band $[0.83, 0.95]$). LLM-verifier rows are measured
on the band itself.}
\label{tab:rq5}
\begin{tabular}{@{}lccc@{}}
\toprule
Configuration & overall FH & FH slope & FH cliff \\
\midrule""")
L.append(f"threshold only ($\\tau^\\ast{{=}}0.89$) & {t0['false_hit']*100:.1f}\\% & {t0['false_hit_slope']*100:.1f}\\% & {t0['false_hit_cliff']*100:.1f}\\% \\\\")
L.append(f"$+$ cross-encoder & {ce['false_hit']*100:.1f}\\% & {ce['false_hit_slope']*100:.1f}\\% & {ce['false_hit_cliff']*100:.1f}\\% \\\\")
L.append(f"$+$ LLM verifier (in band) & {lv['band_false_hit']*100:.1f}\\% & {lv['band_false_hit_slope']*100:.1f}\\% & {lv['band_false_hit_cliff']*100:.1f}\\% \\\\")
L.append(r"""\bottomrule
\end{tabular}
\end{table}""")

# ---- Table C5: RQ6 mean IO + Kendall ----
gens = ["opus", "sonnet", "haiku"]
encs = list(r6["per_generator"]["opus"].keys())
L.append(r"""\begin{table}[t]
\centering\small
\caption{RQ6: mean change-axis IO per encoder under each generator tier
(781-seed subset), with Kendall's $\tau$ between the induced rankings:
opus--haiku 0.87 ($p{=}.017$), sonnet--haiku 0.73, opus--sonnet 0.60.}
\label{tab:rq6}
\begin{tabular}{@{}lccc@{}}
\toprule
Encoder & Opus & Sonnet & Haiku \\
\midrule""")
for e in encs:
    short = e.split("/")[-1].replace("all-MiniLM-L6-v2", "MiniLM-L6") \
                            .replace("nomic-embed-text-v1.5", "Nomic-v1.5") \
                            .replace("multilingual-e5-large", "mE5-large")
    vals = " & ".join(f"{r6['per_generator'][g][e]['mean_io']:.3f}" for g in gens)
    L.append(f"{short} & {vals} \\\\")
L.append(r"""\bottomrule
\end{tabular}
\end{table}""")

OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
print(f"wrote {OUT} ({len(L)} lines, 5 tables)")
