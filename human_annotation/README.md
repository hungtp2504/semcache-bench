# human_annotation/ — everything for the human gold-subset validation

One self-contained folder: the pairs to annotate, the annotator guide, the
sheets to fill in, and the analysis scripts.

| File | What it is | Who reads it |
|---|---|---|
| `HUONG_DAN.md` | **Hướng dẫn tiếng Việt cho người gán** — nhãn là gì, đánh thế nào, ví dụ mẫu, quy tắc | Annotators (start here) |
| `PROTOCOL.md` | English protocol: design, sample-size justification, gates | Coordinator / paper |
| `sheets/annotator_{1,2,3}.csv` | 1,500 pairs each, open in Excel/Google Sheets, fill the `nhan` column | Annotators |
| `gold_input.jsonl` | The canonical blind input (gid + two questions; stratified 9 axes × 5 domains, 164–168/axis) | Scripts |
| `scripts/sheet_to_jsonl.py` | Validate + convert a finished CSV to JSONL | Coordinator |
| `scripts/gold_agreement.py` | Fleiss' κ, pairwise agreement, majority-vs-construction accuracy, adjudication list | Coordinator |

## Workflow

1. Give each annotator their CSV from `sheets/` and `HUONG_DAN.md`.
   Three independent annotators (minimum 2 + a referee); annotators covering the
   ~300 Vietnamese pairs must read Vietnamese. No discussion until all submit.
2. Collect the finished CSVs back into `sheets/`, then:
   ```bash
   python3 human_annotation/scripts/sheet_to_jsonl.py human_annotation/sheets/annotator_1.csv  # x3
   python3 human_annotation/scripts/gold_agreement.py human_annotation/annotator_*.jsonl
   ```
3. Gate: Fleiss' κ ≥ 0.65. Pairs without unanimity land in
   `adjudication_needed.jsonl` → discussion → referee → gold labels.
4. Paper updates once done: reword the LLM-only-validation threat, add κ +
   human-agreement numbers to RQ1–RQ2, strengthen the abstract's validation
   sentence.

Effort: ~15–20 s/pair → 6–8 h per annotator; recommend 3–4 sittings.
