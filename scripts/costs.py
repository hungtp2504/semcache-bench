#!/usr/bin/env python3
"""Latency inputs of the cost model and Table 1 (results/costs.json).

  bi_encoder_ms, cross_encoder_ms  amortized per-item model time from the
                                   micro-benchmark in scripts/stats_and_f7.py
                                   (results/stats_final.json; M4 Pro, MPS, batch 64;
                                   nearest-neighbour search not included)
  llm_verifier_ms_per_pair         median over all logged stage-E batches of
                                   (batch wall-clock / pairs in the batch), from
                                   logs/generation/E_*.meta.json
"""
import datetime as dt
import json
import statistics
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def ts(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def main() -> int:
    lat = json.loads((REPO / "results" / "stats_final.json").read_text())["latency"]
    per_pair = []
    for f in sorted((REPO / "logs" / "generation").glob("E_*.meta.json")):
        m = json.loads(f.read_text())
        if m.get("n_input"):
            per_pair.append((ts(m["ts_end"]) - ts(m["ts_start"])).total_seconds() * 1000
                            / m["n_input"])
    out = {"bi_encoder_ms": lat["bi_encoder_ms_per_query"],
           "cross_encoder_ms": lat["cross_encoder_ms_per_pair"],
           "llm_verifier_ms_per_pair": round(statistics.median(per_pair)),
           "llm_verifier_batches": len(per_pair),
           "note": "bi/cross-encoder: scripts/stats_and_f7.py micro-benchmark (M4 Pro, MPS, "
                   "batch 64, amortized per item, no nearest-neighbour search); LLM verifier: "
                   "median per-pair wall-clock over the logged stage-E batches"}
    (REPO / "results" / "costs.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
