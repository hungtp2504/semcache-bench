#!/usr/bin/env python3
"""RISK CHECK 1 (PLAN §9) — are transitivity violations frequent enough to carry RQ3b?

Per embedding model and threshold τ, measures:
  1. transitivity-violation rate — over "connected triples" (A,B,C) with
     sim(A,B) > τ and sim(B,C) > τ, the fraction where sim(A,C) <= τ;
  2. order dependence — simulate a semantic cache over M random arrival orders;
     a query is UNSTABLE if the entry that serves it differs across orders
     (proxy for answer instability: full RQ3b uses real answers; a serve by a
     different stored key can mean a different answer, a miss means a fresh one);
  3. hit-rate mean/std across orders.

Pre-registered decision rule (PLAN §9):
  violations < 1% AND instability < 2%  → RQ3b is NOT headline material: demote it to a
                                          secondary finding, promote RQ3a/RQ5.
  instability >= 5%                     → reorganize the whole narrative around RQ3b.

Cost: local only, no tokens.

Usage:
  python3 scripts/risk_check_1_transitivity.py                    # real models (downloads)
  python3 scripts/risk_check_1_transitivity.py --mock             # logic smoke-test only
  python3 scripts/risk_check_1_transitivity.py --questions my_questions.txt --n 500
Input may be .txt (one question/line) or .jsonl (uses question/q1/q2/text/variation fields).
"""
import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from embed_utils import DEFAULT_RISK_MODELS, MOCK_MODEL_NAME, cosine_matrix, embed_texts

REPO = Path(__file__).resolve().parents[1]


def load_questions(path: Path):
    qs = []
    for ln in path.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        if ln.startswith("{"):
            try:
                o = json.loads(ln)
            except json.JSONDecodeError:
                continue
            for f in ("question", "q1", "text", "variation"):
                if o.get(f):
                    qs.append(str(o[f]).strip())
                    break
            if o.get("q2"):
                qs.append(str(o["q2"]).strip())
        else:
            qs.append(ln)
    seen, out = set(), []
    for q in qs:
        if q and q not in seen:
            seen.add(q)
            out.append(q)
    return out


def transitivity_stats(S, tau):
    """Count connected triples and violations among them (anchor-B formulation)."""
    n = S.shape[0]
    A = S > tau
    np.fill_diagonal(A, False)
    below = S <= tau
    connected = violated = 0
    for j in range(n):
        idx = np.flatnonzero(A[:, j])
        k = idx.size
        if k < 2:
            continue
        connected += k * (k - 1) // 2
        sub = below[np.ix_(idx, idx)]
        violated += int(np.triu(sub, 1).sum())
    return connected, violated


def simulate_orders(S, tau, m_orders, rng):
    """FIFO semantic-cache simulation over random arrival orders.
    Policy (matches PLAN §5 example): on miss, store the query; on hit, serve the best
    stored entry with sim > τ and do NOT store the query."""
    n = S.shape[0]
    serving_keys = [set() for _ in range(n)]
    hit_rates = []
    for _ in range(m_orders):
        order = rng.permutation(n)
        stored = []
        hits = 0
        for i in order:
            if stored:
                sims = S[i, stored]
                b = int(np.argmax(sims))
                if sims[b] > tau:
                    serving_keys[i].add(stored[b])
                    hits += 1
                    continue
            stored.append(int(i))
            serving_keys[i].add(int(i))  # fresh LLM answer = its own key
        hit_rates.append(hits / n)
    unstable = sum(1 for s in serving_keys if len(s) > 1) / n
    return unstable, float(np.mean(hit_rates)), float(np.std(hit_rates))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--questions", default=str(REPO / "data" / "00_manual" / "risk_check_pairs.jsonl"),
                    help="txt or jsonl; default reuses the hand-written pair file (both q1 and q2)")
    ap.add_argument("--models", nargs="+", default=None)
    ap.add_argument("--taus", nargs="+", type=float, default=[0.85, 0.90, 0.95])
    ap.add_argument("--n", type=int, default=500, help="sample size cap (PLAN §9: 500)")
    ap.add_argument("--orders", type=int, default=200, help="arrival-order permutations")
    ap.add_argument("--mock", action="store_true", help="deterministic mock embedder — logic test only")
    ap.add_argument("--out", default=str(REPO / "results" / "risk_check_1.json"))
    a = ap.parse_args()

    rng = np.random.default_rng(42)
    questions = load_questions(Path(a.questions))
    if len(questions) < 10:
        print(f"only {len(questions)} questions — need more to say anything", file=sys.stderr)
        return 2
    if len(questions) > a.n:
        questions = [questions[i] for i in rng.choice(len(questions), a.n, replace=False)]
    models = [MOCK_MODEL_NAME] if a.mock else (a.models or DEFAULT_RISK_MODELS)

    print(f"risk check 1 — {len(questions)} questions, taus={a.taus}, orders={a.orders}"
          + ("  [MOCK — logic test only, numbers meaningless]" if a.mock else ""))

    results = {"generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
               "mock": a.mock, "n_questions": len(questions), "orders": a.orders, "models": {}}
    worst_instab, worst_viol = 0.0, 0.0

    for m in models:
        print(f"\n== {m} ==")
        S = cosine_matrix(embed_texts(questions, m, mock=a.mock))
        per_tau = {}
        print(f"{'tau':>6} {'conn.triples':>13} {'violations':>11} {'viol.rate':>10} "
              f"{'unstable':>9} {'hit.mean':>9} {'hit.std':>8}")
        for tau in a.taus:
            connected, violated = transitivity_stats(S, tau)
            vr = violated / connected if connected else 0.0
            unstable, hit_mean, hit_std = simulate_orders(S, tau, a.orders, rng)
            per_tau[str(tau)] = {"connected_triples": int(connected), "violations": int(violated),
                                 "violation_rate": vr, "unstable_share": unstable,
                                 "hit_rate_mean": hit_mean, "hit_rate_std": hit_std}
            worst_instab = max(worst_instab, unstable)
            worst_viol = max(worst_viol, vr)
            print(f"{tau:>6.2f} {connected:>13,} {violated:>11,} {vr:>9.2%} "
                  f"{unstable:>8.2%} {hit_mean:>9.2%} {hit_std:>8.3f}")
        results["models"][m] = per_tau

    print("\n--- pre-registered verdict (PLAN §9) ---")
    if a.mock:
        verdict = "MOCK RUN — logic verified only; rerun with real models before deciding anything."
    elif worst_viol < 0.01 and worst_instab < 0.02:
        verdict = ("WEAK: violations < 1% and instability < 2% at every tau/model → RQ3b is not "
                   "headline material. Demote to secondary finding; promote RQ3a/RQ5 in the narrative.")
    elif worst_instab >= 0.05:
        verdict = (f"STRONG: instability reaches {worst_instab:.1%} → reorganize the narrative "
                   "around order dependence (RQ3b). This is the abstract's X.")
    else:
        verdict = (f"MIDDLE: instability {worst_instab:.1%}, violations {worst_viol:.1%} → real but "
                   "not headline-grade on this sample; retest on domain questions before deciding.")
    print(verdict)
    results["verdict"] = verdict

    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
