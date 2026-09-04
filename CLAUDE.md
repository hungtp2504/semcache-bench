# CLAUDE.md — semcache-bench standing instructions

Benchmark + analysis code for the paper **"Cliffs and Slopes: Why Semantic Caches Fail
Structurally, Not Just Through Miscalibration"** (target: Information & Software Technology).
Master plan: `../PLAN.md` · Abstract contract: `../ABSTRACT.md` (both deliberately outside this repo).

Core thesis: semantic caching needs an **equivalence relation** but is implemented as a
**threshold on smooth, non-transitive similarity** — so its failures are structural
(irreducible overlap concentrated on "cliff" axes; order-dependent behavior), not mere
miscalibration. Four pre-registered claims C1–C4 (PLAN §3); C4 is the key advance prediction.

---

## SESSION PROTOCOL — every session, in this order

1. **Read `logs/manifest.json` first** (or run `python3 scripts/manifest.py status`).
2. Confirm this session's model matches the stage table below. If it does not match,
   STOP and tell the user to switch with `/model`. Record the **exact model string** in
   every generated record and log.
3. Resume from the first `pending` batch of the current stage. **One turn = one batch.**
4. After EVERY batch, in this exact order:
   1. Write the raw model output verbatim to `logs/generation/<batch_id>.raw.md`
      (before any parsing or cleanup).
   2. Write `logs/generation/<batch_id>.meta.json`:
      `{batch_id, stage, model, prompt_file, prompt_version, cached_block_sha256,
        input_ids, ts_start, ts_end, session_id}`.
      (`cached_block_sha256` comes from `scripts/render_prompt.py --hash`.)
   3. Parse the raw output with the stage's assemble script (e.g.
      `scripts/assemble_variations.py` for A4), which validates and **appends** to the
      stage's data file. Then run `scripts/validate_jsonl.py --stage <stage> <file>`.
   4. `python3 scripts/manifest.py mark <batch_id> --status done --n <records>`
      (or `--status failed --note "<what broke>"`).
5. Malformed or partial model output → salvage the valid lines, mark the batch `failed`
   with a note, **move on to the next batch**. Never stop the whole run for one bad batch.
   Never silently hand-edit records.
6. End of session: manifest updated → `git add` new data/logs → commit
   (`stage(batch range): short summary`).

## APPEND-ONLY RULE

`data/*.jsonl` and `logs/**` are append-only. Never rewrite or reorder existing lines.
Corrections happen by filtering at `05_final` build time, never by editing history.

---

## STAGE TABLE (models, batch sizes — PLAN §13)

| Stage | Task | Prompt file | Model | Batch/turn | Output file |
|---|---|---|---|---|---|
| A  | docs → facts + seed Q/A     | prompts/A_extract.md    | claude-sonnet-5  | 3 docs        | data/01_facts.jsonl + data/02_seeds.jsonl |
| A4 | seed → 28 generated variants (9 axes; N4/N5 ×4 overgenerate, top-2 judge-passed kept at freeze — v1.2) | prompts/A4_variation.md | claude-opus-5 | 10 seeds → 280 variants | data/03_variations.jsonl |
| B1 | judge axis compliance #1    | prompts/B_judge.md      | claude-sonnet-5  | 60 variants   | data/04a_judgments_b1.jsonl |
| B2 | judge axis compliance #2    | prompts/B_judge.md      | claude-opus-5    | 60 variants   | data/04b_judgments_b2.jsonl |
| C  | RQ6: regenerate 40% subset  | prompts/A4_variation.md | claude-sonnet-5 / claude-haiku-4-5-20251001 | 20 seeds | data/03_variations_rq6_{sonnet,haiku}.jsonl |
| E  | RQ5 verification tier       | prompts/E_verify.md     | claude-haiku-4-5-20251001 | 50 pairs | data/06_verify_decisions.jsonl |

**Judge rule (PLAN §12.2, T4):** the **primary** judge of a record must be a *different
model* than that record's `generator_model`; the second judge provides the independent
agreement measurement (Krippendorff's α ≥ 0.70 gate). Never rely on a single same-model
judgment. ⚠️ Note: PLAN §13 labels B1=Opus/B2=Sonnet while §12.2 requires primary ≠
generator; this repo follows §12.2 (A4 generator is Opus ⇒ **B1/primary = Sonnet**,
B2 = Opus, with the same-family limitation reported under Threats T4). Flagged
2026-08-11 — confirm with the author before Stage B starts.

---

## HARD RULES (non-negotiable)

- **`expected_label` is derived from the axis by code** (P1–P3 → HIT; N1–N6 → MISS) in
  `scripts/assemble_variations.py`. No model ever decides HIT/MISS. Judges only assess
  *axis compliance* (`axis_ok`, `conf`) — never the label.
- **Prompt caching / comparability:** the block between `<!-- CACHED BLOCK START -->` and
  `<!-- CACHED BLOCK END -->` in each prompt file must stay **byte-identical** for the
  whole stage, and must sit at the **top** of the assembled prompt. Any change ⇒ bump the
  `version:` header, log it in the manifest `notes`, and record which batches used which
  version. Use `scripts/render_prompt.py` to assemble prompts and to hash the cached block.
- **Taxonomy source of truth = `config/taxonomy.yaml`.** Prompts embed a rendered copy
  stamped with `taxonomy_version`; regenerate only on version bumps, never ad hoc.
- **Language:** variants and judgments are written in the **seed's language**
  (d5 = Vietnamese, d1–d4 = English).
- **IDs:** seeds `d{1..5}_s{0001..}` (sequential per domain, assigned at parse time from
  the current line count of `data/02_seeds.jsonl`); variants `<seed_id>_<axis>_v<k>`;
  batches `<STAGE>_<0001..>`. Timestamps: UTC ISO-8601.
- **Logging is the T1 mitigation** (no temperature/seed control on subscription): raw
  output + meta for every batch, released with the replication package. No log → the
  batch does not exist; regenerate it.

## QUALITY GATES (PLAN §15 — check before scaling, record results in manifest notes)

- Pilot before scaling A4: **≥ 80% axis compliance** on 200 self-audited samples
  (expect N2/N6 weakest — add few-shots there first, don't scale).
- After A: **≥ 4,500 valid seeds** pooled → select 2,000 (400/domain) for A4.
- After A4: every axis ≥ 8% of variants; exactly 12 HIT : 12 MISS per seed.
- After B1+B2: **Krippendorff's α ≥ 0.70** between judges.
- Final: ~35,000 pairs after filtering + **mandatory MinHash dedupe** (LLMs repeat
  themselves; skipping dedupe inflates the dataset).

## BUDGET DISCIPLINE (PLAN §13)

Batch maximally — never 1 item/turn. Cached block at prompt top, byte-identical.
Haiku for simple classification. Avoid 19:00–01:00 VN time (US peak). Real quota numbers:
user runs `/usage` + `/status` and records them in `logs/quota_notes.md` (pending).

---

## LAYOUT

```
config/     taxonomy.yaml (source of truth) · domains.yaml · models.yaml · record.schema.json
corpus/     d1..d5 raw docs — NOT committed (licensing); provenance in corpus/*/index.jsonl
prompts/    A_extract · A4_variation · B_judge · E_verify (versioned, cached-block markers)
data/       00_manual (hand-written risk-check pairs) · 01_facts · 02_seeds ·
            03_variations · 04a/04b judgments · 05_final (built later by join+filter+dedupe)
logs/       manifest.json (RESUME MECHANISM) · generation/<batch>.raw.md + .meta.json
scripts/    manifest.py · render_prompt.py · assemble_variations.py · validate_jsonl.py ·
            embed_utils.py · risk_check_1_transitivity.py · risk_check_2_cliff_separation.py
results/    analysis outputs (RQ3a IO heatmap, RQ3b instability, RQ4 τ* curves, ...)
```

## DATA SCHEMAS (JSONL, one object per line)

- `01_facts`: `{fact_id, domain, doc_id, statement, source_span}`
- `02_seeds`: `{seed_id, domain, doc_id, fact_ids, question, answer, batch_id, generator_model, ts}`
- `03_variations` (canonical record, PLAN §14): `{id, domain, seed_id, seed_question,
  answer, variation, axis, axis_group, expected_label, delta, generator_model, batch_id, ts}`
  — `judge1/judge2` are joined in at 05_final build time.
- `04a/04b_judgments`: `{id, judge_model, axis_ok, conf, issue, batch_id, ts}`
- `05_final`: canonical record + `judge1, judge2` (built by a join script —
  to be written in Month 3, T12).
- `00_manual/risk_check_pairs.jsonl`: `{pair_id, group(I|II|III), axis, lang, domain, q1, q2,
  expected, note}` — hand-curated, gate for C4 plausibility (PLAN §9).

## ANALYSIS PHASE (Months 5–6, all local on MPS)

Embedding models in `config/models.yaml` (10 bi-encoders + 2 cross-encoders = 12).
RQ3a: IO per axis × model × domain (heatmap = flagship figure). RQ3b: 1,000 arrival-order
permutations. RQ4: utility U(τ), sweep ρ ∈ [1, 1000]. RQ5: 4 configurations, results split
by axis group (C4 test). Stats: Friedman + Nemenyi, bootstrap CI, Holm–Bonferroni, Cliff's δ.

## CURRENT STATUS

Scaffolded 2026-08-11. Next milestones: corpus collection (Month 1 = Aug 2026, licensing
notes in `corpus/README.md`), then the two **risk checks** (PLAN §9, early Sep 2026 —
already registered as pending batches RISK_0001/0002 in the manifest) BEFORE any data
generation.
