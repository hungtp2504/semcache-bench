# 00_manual — hand-curated data

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
