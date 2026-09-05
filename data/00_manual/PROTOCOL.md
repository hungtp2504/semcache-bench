# Human annotation protocol — gold-subset validation (PLAN §15, Month 4)

> **Status (2026-09-05): executed.** Three annotators (university-educated
> colleagues of the authors, unpaid volunteers, all reading Vietnamese) labeled
> all 1,500 pairs. Outputs: `data/00_manual/annotator_{1,2,3}.jsonl`; analysis:
> `scripts/gold_agreement.py` → `results/human_gold.json`. Result: Fleiss'
> κ = 0.76 [0.73, 0.78] (gate 0.65 passed); majority label vs construction
> label 1,478/1,500 = 98.5% [97.8, 99.0]. Paths below reflect the new layout;
> the annotator-facing guide `HUONG_DAN.md` is kept verbatim as distributed.

Validates the benchmark's construction-derived labels with independent human
judgment. Input: `data/00_manual/gold_input.jsonl` — 1,500 pairs stratified over the
9 axes × 5 domains grid (164–168 per axis, ~300 per domain), **blind**: each
record carries only `{gid, qa, qb}`; no expected label, no axis, no judge
output; A/B order already randomized per pair.

## Design (do not cut corners)

- **3 independent annotators** (minimum: 2 + a referee for disagreements —
  never 1). d5 pairs are Vietnamese: at least the annotators covering d5 must
  read Vietnamese.
- Each annotator labels **all 1,500 pairs**, independently, blind to the other
  annotators, to the construction labels, and to the paper's hypotheses.
- Gate: **Fleiss' κ ≥ 0.65** across the three annotators.
- Disagreements → discussion → adjudicated **gold label** (referee decides if
  discussion does not converge).
- Deliverable per annotator: one JSONL file, one line per pair:
  `{"gid": "...", "label": "SAME" | "DIFFERENT" | "UNSURE"}`
  Name it `data/00_manual/annotator_<n>.jsonl`.

## The one question

For each pair, answer exactly one question:

> **"Should these two questions receive the same answer?"**

That is: would one single answer fully and correctly serve BOTH questions?
Assume both questions are asked against the same knowledge source (a course
document, product documentation, a medical fact sheet, or a regulation).

- **SAME** — any complete, correct answer to one is also a complete, correct
  answer to the other (typos, phrasing, register, missing diacritics do not
  matter).
- **DIFFERENT** — a correct answer to one would be wrong, incomplete, or
  misleading for the other (different entity, flipped polarity, different
  quantity or extreme, different facet or scope, different presupposed fact).
- **UNSURE** — only when, after careful thought, reasonable people would
  genuinely disagree. Use it sparingly.

Judge each pair independently. Do not assume any pattern in the data.

## Analysis

`python3 scripts/gold_agreement.py` (writes `results/human_gold.json`) computes:
Fleiss' κ with bootstrap CI (gate 0.65), pairwise raw agreement / Cohen's κ /
Gwet's AC1, unanimity, majority label vs the construction-derived label
(overall + per axis + per axis group + per domain + per language, Wilson CIs),
and the full disagreement list with per-annotator votes.

## What this buys the paper (with n = 1,500)

- Overall construction-label accuracy: 95% Wilson CI ±0.9 pp at 97% observed
  agreement (±1.5 pp even at 90%).
- Per-axis accuracy: ~167 pairs/axis → per-axis 95% CI roughly ±3–7 pp — enough
  to state "every axis ≥ X%" claims.
- Lifts the paper's stated main limitation (LLM-only validation, Threats
  §"LLM-only validation"): reword T3, add κ and human-agreement numbers to
  RQ1–RQ2, and strengthen the abstract's validation sentence.

Smaller designs, if 1,500×3 is infeasible: 900 pairs (100/axis) keeps per-axis
CIs ≤ ±9 pp; 500 pairs supports only the overall-accuracy claim (±1.9 pp at
95% observed) and weakens per-axis statements — the stratified 1,500 input is
already built, so subsample by taking the first k per axis if needed.
