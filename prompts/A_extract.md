---
prompt: A_extract
version: "1.0"
stage: A
model: claude-sonnet-5
batch: 3 documents per turn
output: data/01_facts.jsonl + data/02_seeds.jsonl
---

<!-- CACHED BLOCK START -->
You extract facts and seed question–answer pairs from source documents, to build a
semantic-cache benchmark.

TASK
For each document below: (1) extract atomic facts, (2) write seed questions whose answers
are fully contained in the document.

RULES FOR FACTS
1. One atomic fact per line — a single checkable statement with its specifics
   (dates, numbers, names, conditions) intact.
2. Copy the supporting span reference: quote the shortest snippet that proves the fact.
3. Skip boilerplate, navigation text, and opinions.

RULES FOR SEEDS
1. Each seed is a natural, self-contained question a real user would type. It must be
   answerable WITHOUT seeing the document.
2. The answer must be short (1–3 sentences), complete, and grounded ONLY in the
   document. No outside knowledge.
3. One unambiguous answer per question — if two readings give two answers, rewrite or drop.
4. Prefer questions rich in entities, numbers, dates, conditions (they support the
   9-axis variation stage later). Avoid pure yes/no questions (aim ≤ 1 in 6).
5. Write in the SAME LANGUAGE as the document (d5 documents → Vietnamese).
6. Target ~6 seeds per document; fewer is fine for thin documents — never pad.

OUTPUT FORMAT — JSONL only, no commentary, no code fences.
Fact lines:  {"type":"fact","doc_id":"<given>","statement":"...","source_span":"..."}
Seed lines:  {"type":"seed","doc_id":"<given>","fact_refs":[<0-based indexes of this doc's facts>],"question":"...","answer":"..."}
(seed_id is assigned by the parser, not by you.)
<!-- CACHED BLOCK END -->

[BATCH INPUT]
batch_id: {{batch_id}}
documents (each as: doc_id, domain, then full text):

{{documents}}
