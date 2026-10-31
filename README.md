# semcache-bench

Benchmark and analysis code for **"Cliffs and Slopes: Structural Failure Modes and
Testing of Semantic Caches for LLM Applications"** (under review at IEEE Access).
The version of the code and results cited by the manuscript is tag
`access-2026-49663-submitted`; `REPLICATION.md` maps every table and figure to its script.

A semantic cache answers a new query with the stored answer of a "similar enough" past
query. This repo builds a 46,214-pair benchmark (5 domains, 2 languages, 9 transformation
axes derived from the ratio *answer-step / surface-step*) and measures where — and why —
threshold-on-similarity caching fails structurally:

- **Irreducible Overlap (IO)** — the error floor no threshold tuning can remove (RQ3a)
- **Order dependence** — thresholded similarity is not transitive, so cache behavior
  depends on query arrival order (RQ3b)
- **Cost-aware calibration** — no dominant threshold across domains/cost ratios (RQ4)
- **Second-stage verification** — evaluated held-out (5-fold, seed-grouped) with common
  denominators; the pre-registered cliff/slope asymmetry holds for the cross-encoder tier,
  not for the LLM verifier (RQ5; `scripts/rq5_heldout.py`)

**Dataset release:** the frozen 46,214-pair benchmark, taxonomy, prompts,
datasheet, and the human gold-subset annotations are published on the Hugging Face Hub:
[`tedbelford/cliffs-and-slopes-semantic-cache`](https://huggingface.co/datasets/tedbelford/cliffs-and-slopes-semantic-cache).
Code is MIT-licensed; data licensing is mixed (CC BY 4.0, d1 subset CC BY-NC-SA 4.0) — see `DATASHEET.md`.

**Human label audit:** three blind annotators independently labeled a
stratified 1,500-pair subset (`data/00_manual/`, protocol included). Fleiss'
κ = 0.76 [0.73, 0.78] (cluster-bootstrap by seed); on the n = 1,497 analysis
set the majority label agrees with the construction-derived label on 98.5% of
pairs [97.9, 99.1], ≥ 96.3% on every axis. Annotators judged question pairs
without source grounding (see paper, Threats); a source-grounded round is
prepared in `human_annotation_v2/`. Reproduce with
`python3 scripts/gold_agreement.py` → `results/human_gold.json`.

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Note: embedding evaluation needs `torch` with MPS (Apple Silicon). If no `torch` wheel
exists yet for your Python (3.14 is new), create the venv with Python 3.12/3.13 instead
(`uv venv -p 3.12` or pyenv). The risk-check scripts also run with `--mock` (numpy only)
to smoke-test logic without downloading models.

## Quick start — the two early risk checks (run before generating data)

```bash
# 1) Are transitivity violations frequent enough to carry RQ3b?
python3 scripts/risk_check_1_transitivity.py --questions data/00_manual/risk_check_pairs.jsonl

# 2) Do cliff pairs separate from slope pairs? (uses the hand-written 60 pairs)
python3 scripts/risk_check_2_cliff_separation.py
```

Both print a verdict against the pre-registered decision rules and write JSON to `results/`.
`data/00_manual/risk_check_pairs.jsonl` holds the 60 hand-written pairs used for the
second check.

## Pipeline (data generation happens in Claude Code sessions)

Stages A → A4 → B1/B2 → filter/dedupe. Every batch follows one fixed
protocol (manifest resume, append-only logging), implemented by `scripts/claude_batch.py`. State lives in
`logs/manifest.json`; raw generation logs in `logs/generation/` are part of the
replication package (Threats T1 mitigation).

## Layout

`config/` taxonomy, domains, models, record schema · `prompts/` versioned stage prompts · `data/` stage outputs and the frozen benchmark · `logs/` manifest and raw generation logs · `scripts/` pipeline and analysis · `results/` analysis outputs. Source of truth for the 9-axis taxonomy: `config/taxonomy.yaml`.
