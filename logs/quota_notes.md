# Quota calibration (PLAN §13) — real numbers

## /usage snapshot — 2026-08-12, Asia/Saigon (user-provided)

- Current 5h session window: 0% (resets 14:39)
- Current week, all models: **2% used** — INCLUDING both heavy scaffold/risk-check
  sessions of 2026-08-11/12
- **+50% weekly-limit promo through Aug 19** → front-load generation THIS week
- Insight from usage panel: 75% of past usage was at >150k context (long interactive
  sessions). Headless `claude -p` batches run at ~5k fresh context each → the
  claude_batch.py harness is far cheaper per generated token than in-session
  generation. Keep interactive sessions lean; push volume through the harness.

## First per-batch data point (SMOKE_0001, haiku, 2 seeds → 48 variants)

- output_tokens: 16,111 (≈335 tok/variant — ~10× PLAN §13's ~33 tok/variant estimate;
  headless runs include thinking tokens)
- cache_creation (1h): 16,945 · cache_read: 18,446 · input: 9
- cost-equivalent: $0.116

**Implication:** PLAN §13's per-turn token estimates are low for headless runs.
Batch sizes adjusted: A4 runs at 10 seeds/batch (240 variants) instead of 20 until
real Opus numbers land. Record output_tokens from every .meta.json and recalibrate
after the pilot. Track weekly-% delta after each generation day — /usage shows
percentages, not tokens, so the empirical (tokens generated ↔ Δ%) pair is the only
reliable exchange rate.

## Schedule implication

At 2%/week baseline with the promo active, quota is NOT the binding constraint —
wall-clock time per CLI call is (~2–10 min each). The §13 fear of a 12-week Max-5x
schedule does not apply to this account at current usage; generation is gated by the
§15 quality gates, not by tokens.
