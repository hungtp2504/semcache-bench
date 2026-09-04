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
| F3 heatmap + IO tables (RQ3a), instability (RQ3b) | `python scripts/analyze_final.py --models <9 encoders>` | `results/final_analysis.json` |
| RQ5 four configs + RQ4 τ*(ρ) + F5/F6 inputs | `python scripts/rq5_experiment.py` then `python scripts/rq5_config3.py` | `results/rq5_rq4.json` |
| RQ6 Kendall | `python scripts/rq6_analysis.py` | `results/rq6.json` |
| Friedman/Nemenyi + F7 + latency | `python scripts/stats_and_f7.py` | `results/stats_final.json` |
| Figures F1–F7 | `python scripts/make_figures.py --results results/final_analysis.json`, `make_figures2.py`, `make_f1_f2.py` | `../paper/figures/` |

## 3. Regenerating the dataset itself (needs Claude Code CLI + subscription)
Stages A → A4 → B1/B2 (→ C for RQ6, E for RQ5-config3) run
through `scripts/claude_batch.py` / `scripts/parallel_exec.py`; prompts in `prompts/`
(versioned, byte-hashed cached blocks). Sampling parameters are provider defaults
(subscription CLI); this is why the full raw logs above are part of the release.

## 4. Corpus
Raw documents are NOT redistributed (licenses vary; see `corpus/README.md` and
per-domain `index.jsonl` provenance). Fetchers: `scripts/fetch_*.py`, `scripts/prep_stage_a.py`.
