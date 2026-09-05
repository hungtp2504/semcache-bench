# human_annotation_v2/ — source-grounded label audit (round 2, prepared, NOT yet run)

Round 1 (`data/00_manual/`) showed annotators only the two questions; it audits
question-level answer substitutability. This round grounds the judgment in the
stored answer — the cache's actual decision — so it can also catch pairs whose
distinct questions coincidentally share an answer. See `PROTOCOL_V2.md` for the
full design and pre-fixed analysis rules.

| File | What it is | Who reads it |
|---|---|---|
| `HUONG_DAN_V2.md` | Hướng dẫn tiếng Việt cho người gán (vòng 2) | Annotators (start here) |
| `PROTOCOL_V2.md` | English protocol: motivation, design, analysis rules | Coordinator / paper |
| `gold_input_v2.jsonl` | Canonical input: `{gid, qa, qb, answer}` — same 1,500 pairs and A/B order as round 1, plus the reference answer | Scripts |
| `sheets/annotator_{1,2,3}.csv` | 1,500 rows each; fill the `nhan` column | Annotators |
| `scripts/sheet_to_jsonl.py` | Validate + convert a finished CSV to JSONL | Coordinator |

## Workflow

1. Recruit three annotators — **preferably people who did not do round 1**
   (see PROTOCOL_V2.md on reuse/washout). Annotators covering the ~300
   Vietnamese pairs must read Vietnamese. Hand each their CSV + `HUONG_DAN_V2.md`.
2. Collect finished CSVs into `sheets/`, then per file:
   ```bash
   python3 human_annotation_v2/scripts/sheet_to_jsonl.py human_annotation_v2/sheets/annotator_1.csv  # x3
   ```
3. Analysis (same script and rules as round 1):
   ```bash
   python3 scripts/gold_agreement.py --prefix human_annotation_v2/annotator_ --out results/human_gold_v2.json
   ```
   Gate: Fleiss' κ ≥ 0.65.
4. Paper: report round 2 next to round 1 in the human-audit appendix and
   revisit the Threats "audit grounding" item.
