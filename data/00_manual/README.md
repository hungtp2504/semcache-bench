# 00_manual — hand-curated data

## Human gold-subset validation (PLAN §15)

| File | Content |
|---|---|
| `gold_input.jsonl` | the blind input: 1,500 stratified pairs, `{gid, qa, qb}` only, A/B order randomized |
| `annotator_{1,2,3}.jsonl` | one line per pair: `{"gid", "label": SAME \| DIFFERENT \| UNSURE}` |
| `PROTOCOL.md` | design, gates, sample-size justification (with as-run status note) |
| `HUONG_DAN.md` | the Vietnamese annotator guide, verbatim as distributed |

Three independent annotators — university-educated colleagues of the authors,
unpaid volunteers, all reading Vietnamese — each labeled all 1,500 pairs
(164–168 per axis, ~300 per domain), blind to the construction labels, axes,
judge outputs, and each other. Analyze with:

```bash
python3 scripts/gold_agreement.py   # writes results/human_gold.json
```

Headline (2026-09-05): Fleiss' κ = 0.76 [0.73, 0.78] (pre-registered gate
0.65); majority label vs construction label 1,478/1,500 = 98.5% [97.8, 99.0];
every axis ≥ 96.4%. Three pairs (all N5) were double-UNSURE, resolved by the
remaining definite vote.

## risk_check_pairs.jsonl — ⚠️ DRAFT, researcher review required before running

Input for **risk check 2** (PLAN §9): 20 pairs per group (I invariant/HIT,
II slope/MISS, III cliff/MISS), half English, half Vietnamese. Risk check 1 reuses the
same questions by default.

The plan specifies these pairs are **hand-written by the researcher** ("tự viết tay").
This file ships as a curated draft (2026-08-11) so the scripts are runnable — review
every pair, edit freely, replace any you dislike, then run:

```bash
python3 scripts/validate_jsonl.py --stage risk_pairs data/00_manual/risk_check_pairs.jsonl
```

Deliberate boundary cases carry a `note` (e.g. `rc_II_05`, `rc_II_13`, `rc_II_15`:
antonym verb pairs sitting between slope and cliff). They probe exactly the II/III
boundary the check is about — keep or move them consciously, and record the decision
in the codebook (Month 2, T6).

Schema: `{pair_id, group: I|II|III, axis, lang: en|vi, domain, q1, q2, expected: HIT|MISS, note}`
— `expected` is fixed by the group (I→HIT, II/III→MISS); the validator enforces
group↔axis↔expected consistency.
