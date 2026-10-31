# Replication guide — semcache-bench

Everything in the paper regenerates from this repository. One-time setup:

```bash
uv venv --python 3.13 .venv && uv pip install --python .venv/bin/python -r requirements.txt
```

## 1. The frozen benchmark
`data/05_final.jsonl` — 46,214 pairs (schema: `config/record.schema.json`).
Rebuild from raw stages: `python scripts/build_final.py` (deterministic).
Raw provenance: every generation batch has `logs/generation/<batch>.{prompt.txt,raw.md,cli.json,meta.json}`
with the exact model string, token usage, timestamps, and the SHA-256 of the cached
prompt block (T1 mitigation). `logs/manifest.json` is the batch ledger.

## 2. Headline analyses (local, MPS/CPU)
| Paper artifact | Command | Output |
|---|---|---|
| F3 heatmap + IO tables (RQ3a), instability (RQ3b) | Two runs, merged (one generator, `rng(42)`, is shared by the sample and the models in order, so the order matters for exact RQ3b values): `python scripts/analyze_final.py --models sentence-transformers/all-MiniLM-L6-v2 BAAI/bge-m3 distilbert/distilbert-base-uncased albert/albert-base-v2 intfloat/e5-large-v2` and `python scripts/analyze_final.py --models thenlper/gte-large nomic-ai/nomic-embed-text-v1.5 intfloat/multilingual-e5-large keepitreal/vietnamese-sbert --out results/final_analysis_part2.json` | `results/final_analysis.json` (+ `_part2`) |
| RQ4 τ*(ρ) + F5 inputs; pre-revision in-sample RQ5 (emits the band pairs for the E stage) | `python scripts/rq5_experiment.py` then `python scripts/rq5_config3.py` | `results/rq5_rq4.json` |
| **RQ5 / Table 1 (revision): held-out, same-denominator evaluation of A–E + F6 inputs** — 5-fold seed-grouped CV, every threshold/band/cutoff/model tuned on training folds; also reruns the in-sample protocol (reproduces 27.5% / 18.4% / band 2.7%) | `python scripts/rq5_heldout.py` (reads the stage-E verifier decisions `data/06_verify_decisions.jsonl`, produced by the stage-E batches via `claude_batch.py`/`assemble_verify.py`) | `results/rq5_heldout.json` |
| C4 reference points (perfect in-band verifier; §V-E) | `python scripts/c4_reference.py` | `results/c4_reference.json` |
| LLM-verifier rerun with opaque pair identifiers, shuffled batches (missing held-out decisions + 100 pairs per axis); Threats, Supp. S.7 | `python scripts/rq5_opaque_prepare.py`, `python scripts/rq5_opaque_run.py` (Claude Code CLI, stage E prompt/model), `python scripts/rq5_opaque_analyze.py`, `python scripts/rq5_heldout.py --fill-missing --out results/rq5_heldout_filled.json` | `data/rq5_opaque_*.jsonl`, `data/06b_verify_decisions_opaque.jsonl`, `results/rq5_opaque.json`, `results/rq5_heldout_filled.json` |
| Fold-assignment robustness (Supp. S.7) | `for s in 1 2 3; do python scripts/rq5_heldout.py --split-seed $s --out results/rq5_heldout_split$s.json; done` | `results/rq5_heldout_split*.json` |
| Table 1 OS column: A/B/D simulated with their Table 1 decision rules at the operating point tuned on all pairs | `python scripts/order_architectures.py` (after `rq3b_answer_identity.py` has cached the workload embeddings) | `results/architectures.json` |
| Latency inputs (Table 1, cost model) | `python scripts/costs.py` (after `stats_and_f7.py`) | `results/costs.json` |
| RQ3b answer-identity analysis (revision): classifies wrong serves by what the verdict rests on (label-backed / MISS–MISS same- and different-axis / cross-seed by seed pair); lower, stress and intermediate bounds | `python scripts/rq3b_answer_identity.py` | `results/rq3b_answer_identity.json` |
| Order-dependence robustness sweeps (size, τ × 3 encoders, Zipf skew, eviction; Supp. Fig. S5) — on the same five-domain workload as RQ3b | `python scripts/order_systematic.py` | `results/order_systematic.json` |
| RQ6 Kendall | `python scripts/rq6_analysis.py` | `results/rq6.json` |
| Friedman/Nemenyi + latency (`--keep-latency` reuses the recorded timings) | `python scripts/stats_and_f7.py` | `results/stats_final.json` |
| Human gold-subset validation (κ, per-axis label agreement) | `python scripts/gold_agreement.py` | `results/human_gold.json` |
| Figures F1–F7 (pre-revision drafts; superseded by the publication row below, e.g. `make_figures2.py` draws the in-sample F6) | `python scripts/make_figures.py --results results/final_analysis.json`, `make_figures2.py`, `make_f1_f2.py` | `../paper/figures/` |
| Publication figures (final) | `python scripts/make_figures_final.py` (F7 with non-significance bars), `make_f8.py` (Supp. S5), `make_dataset_figs.py`, `make_central_fig.py`, then `python scripts/make_illustrations.py` (run last: its F1 supersedes); set `FIG_OUT=<dir>` to write elsewhere | `../paper/figures/` |

## 3. Regenerating the dataset itself (needs Claude Code CLI + subscription)
Stages A → A4 → B1/B2 (→ C for RQ6, E for RQ5-config3) run
through `scripts/claude_batch.py` / `scripts/parallel_exec.py`; prompts in `prompts/`
(versioned, byte-hashed cached blocks). Sampling parameters are provider defaults
(subscription CLI); this is why the full raw logs above are part of the release.

## 4. Corpus
Raw documents are NOT redistributed (licenses vary; see `corpus/README.md` and
per-domain `index.jsonl` provenance). Fetchers: `scripts/fetch_*.py`, `scripts/prep_stage_a.py`.
