# corpus/ — raw source documents (not committed)

Raw documents are licensed material, so git ignores everything here except this
README and the per-domain provenance indexes (`index*.jsonl`: document id, title,
URL, license, retrieval date; no document text).

| Dir | Domain | Source | Provenance index |
|---|---|---|---|
| d1 | University administration (EN) | MIT OpenCourseWare course pages (CC BY-NC-SA 4.0) | `d1/index.jsonl` |
| d2 | Academic NLP (EN) | Qasper v0.3, AllenAI (CC BY 4.0) | `d2/index.jsonl` |
| d3 | Technical documentation (EN) | Django docs (BSD-3-Clause), react.dev (CC BY 4.0) | `d3/index_django.jsonl`, `d3/index_react.jsonl` |
| d4 | Medical (EN) | MedQuAD, NIH sources (CC BY 4.0; verify per subsource); no patient data | `d4/index_MedQuAD.jsonl` |
| d5 | Vietnamese administrative/education regulations (VI) | Legal documents via luatvietnam.vn (copyright-exempt, Art. 15 of the Law on Intellectual Property) | `d5/index.jsonl` |

The indexes list the collected documents; the 567 documents from which seeds were
extracted are the `doc_id`s in `data/01_facts.jsonl` / `data/02_seeds.jsonl`
(d3/d4 seed `doc_id`s are derived from the file names in the indexes' `local_path`).
Licensing of the derived benchmark pairs: see `DATASHEET.md`.
