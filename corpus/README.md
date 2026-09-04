# corpus/ — raw source documents (NOT committed)

Raw documents are licensed material. Git ignores everything here except this README,
`.gitkeep` placeholders, and per-domain `index.jsonl` provenance files.

## Provenance — required BEFORE a document is used

Each domain keeps `corpus/dN/index.jsonl`, one line per document:

```json
{"doc_id":"d3_doc0007","title":"...","url":"...","license":"...","retrieved":"2026-08-20","notes":""}
```

A document without an index line does not exist for the pipeline.

## Per-domain licensing checklist (PLAN §10)

| Dir | Domain | Rules before use |
|---|---|---|
| d1 | University admin (course docs, EN) | **Written permission from the course owner** + anonymize names/codes/institution BEFORE the file lands here. |
| d2 | Academic NLP (Qasper) | Record dataset license + version; cite the Qasper paper. |
| d3 | Tech docs (Django/React/PostgreSQL) | Record each project's documentation license per doc. |
| d4 | Medical (MedQuAD, WHO public) | **Public sources only, zero patient data.** MedQuAD subsources vary — record license per subsource. |
| d5 | Vietnamese admin/edu (self-collected) | Public documents only; record provenance (URL, date) per doc. |

Target: ~150 docs/domain → ~900-seed pool/domain → select 400/domain (config/domains.yaml).
