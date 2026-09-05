# semcache-bench

Benchmark and analysis code for **"Cliffs and Slopes: Why Semantic Caches Fail
Structurally, Not Just Through Miscalibration"**.

A semantic cache answers a new query with the stored answer of a "similar enough" past
query. This repo builds a ~35,000-pair benchmark (5 domains, 2 languages, 9 transformation
axes derived from the ratio *answer-step / surface-step*) and measures where — and why —
threshold-on-similarity caching fails structurally:

- **Irreducible Overlap (IO)** — the error floor no threshold tuning can remove (RQ3a)
- **Order dependence** — thresholded similarity is not transitive, so cache behavior
  depends on query arrival order (RQ3b)
- **Cost-aware calibration** — no dominant threshold across domains/cost ratios (RQ4)
- **Second-stage verification** — predicted to help disproportionately on "cliff" axes (RQ5)

**Dataset release:** the frozen 46,214-pair benchmark, taxonomy, prompts,
datasheet, and the human gold-subset annotations are published on the Hugging Face Hub:
[`tedbelford/cliffs-and-slopes-semantic-cache`](https://huggingface.co/datasets/tedbelford/cliffs-and-slopes-semantic-cache).
Code is MIT-licensed; data licensing is mixed (CC BY 4.0, d1 subset CC BY-NC-SA 4.0) — see `DATASHEET.md`.

**Human label validation:** three independent blind annotators labeled a
stratified 1,500-pair subset (`data/00_manual/`, protocol included). Fleiss'
κ = 0.76 [0.73, 0.78]; the majority label agrees with the construction-derived
label on 98.5% of pairs [97.8, 99.0], ≥ 96.4% on every axis. Reproduce with
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

## Quick start — the two early risk checks (PLAN §9, run BEFORE generating data)

```bash
# 1) Are transitivity violations frequent enough to carry RQ3b?
python3 scripts/risk_check_1_transitivity.py --questions data/00_manual/risk_check_pairs.jsonl

# 2) Do cliff pairs separate from slope pairs? (uses the hand-written 60 pairs)
python3 scripts/risk_check_2_cliff_separation.py
```

Both print a verdict against the pre-registered decision rules and write JSON to `results/`.
**Review/edit `data/00_manual/risk_check_pairs.jsonl` first** — it ships as a draft and the
plan requires researcher-curated pairs.

## Pipeline (data generation happens in Claude Code sessions)

Stages A → A4 → B1/B2 → filter/dedupe. Every session follows
`CLAUDE.md` (session protocol, manifest resume, append-only logging). State lives in
`logs/manifest.json`; raw generation logs in `logs/generation/` are part of the
replication package (Threats T1 mitigation).

## Layout

See `CLAUDE.md` → LAYOUT. Source of truth for the 9-axis taxonomy: `config/taxonomy.yaml`.
