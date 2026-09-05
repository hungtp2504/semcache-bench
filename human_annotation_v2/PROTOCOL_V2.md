# Human annotation protocol v2 — source-grounded label audit

> **Status: prepared, not yet run.** Fix this protocol (including the analysis
> rules below) BEFORE recruiting annotators, then never change it mid-round.

## Why a second round

Round 1 (`data/00_manual/`, executed 2026-09) showed annotators only the two
questions. That audits *question-level answer substitutability* — whether the
transformation changes what is being asked — but not *extensional* answer
equivalence: two questions about different entities can coincidentally share an
answer value (two assignments with the same deadline), and neither the
construction rule nor a question-only annotator can detect that. Round 2 grounds
the judgment in the stored answer, which is exactly the cache's decision
problem: would serving this stored answer fully and correctly answer both
questions?

## Design

- Input: `human_annotation_v2/gold_input_v2.jsonl` — the SAME 1,500 stratified
  pairs and the same randomized A/B order as round 1, for comparability, plus
  one new field: `answer`, the reference answer that fully and correctly
  answers one of the two questions (which one is not disclosed).
- **3 annotators, labeling independently**, each all 1,500 pairs, blind to the
  construction labels, axes, judge outputs, each other, the paper's
  hypotheses, and the round-1 labels.
- **Prefer annotators who did not take part in round 1.** If round-1 annotators
  must be reused, allow a washout period of at least two weeks and disclose the
  reuse (memory of round-1 decisions is a threat to independence between
  rounds).
- The one question per pair:

  > **The answer shown correctly and fully answers one of the two questions.
  > Would serving this same answer fully and correctly answer BOTH questions?**

  - **SAME** — the shown answer is a complete, correct answer to both
    questions.
  - **DIFFERENT** — for at least one of the two questions the shown answer
    would be wrong, incomplete, or misleading.
  - **UNSURE** — only when reasonable people would genuinely disagree after
    careful thought. Use sparingly.

- Acceptance gate: **Fleiss' κ ≥ 0.65** across the three annotators (same as
  round 1).

## Analysis rules (fixed in advance; identical to round 1 rules v2)

- Analysis set: pairs with a 2-of-3 definite (SAME/DIFFERENT) majority; pairs
  without one are excluded from all statistics and reported separately, so
  agreement and label-accuracy analyses use the same n.
- Gold label: 2-of-3 majority of definite votes.
- Headline CIs: nonparametric percentile cluster bootstrap resampling seeds
  (pairs cluster by seed), 10,000 replicates; per-stratum proportions also
  carry pair-level Wilson intervals.
- Expected divergence from construction labels: pairs where distinct questions
  coincidentally share an answer value should now surface as construction-MISS
  / human-SAME. Report their rate separately — it estimates the extensional
  looseness of the intensional labels, which round 1 could not measure.

Run: `python3 scripts/gold_agreement.py --prefix human_annotation_v2/annotator_ --out results/human_gold_v2.json`

## Workflow

1. Give each annotator their CSV from `sheets/` and `HUONG_DAN_V2.md`.
   Annotators covering the ~300 Vietnamese pairs must read Vietnamese.
   No discussion until all three submit.
2. Collect finished CSVs, then per file:
   `python3 human_annotation_v2/scripts/sheet_to_jsonl.py human_annotation_v2/sheets/annotator_1.csv`
3. Gate check + statistics: the gold_agreement.py command above.
4. Paper updates: report round 2 alongside round 1 in the human-audit
   subsection; revisit the Threats "audit grounding" item, which round 2 is
   designed to retire.

Effort: answers are short (median ~100 characters); ~20–25 s/pair → 8–10 h per
annotator; recommend 3–4 sittings.
