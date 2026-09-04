#!/usr/bin/env python3
"""Shared embedding helpers for the risk checks and (later) the RQ3/RQ4 analysis.

--mock mode uses a deterministic character-trigram hash embedder (numpy only): it lets
every script's LOGIC run end-to-end without downloading models. Mock numbers are a crude
lexical baseline — never report them as results.
"""
import hashlib

import numpy as np

# Query-side prefixes some models require (config/models.yaml is the source of truth).
PREFIXES = {
    "intfloat/e5-large-v2": "query: ",
    "intfloat/multilingual-e5-large": "query: ",
    "nomic-ai/nomic-embed-text-v1.5": "search_query: ",
}
TRUST_REMOTE_CODE = {"nomic-ai/nomic-embed-text-v1.5", "jinaai/jina-embeddings-v3"}
DEFAULT_RISK_MODELS = ["sentence-transformers/all-MiniLM-L6-v2", "BAAI/bge-m3"]
MOCK_MODEL_NAME = "mock-char-trigram"


def mock_embed(texts, dim=256):
    vecs = np.zeros((len(texts), dim), dtype=np.float32)
    for r, t in enumerate(texts):
        t2 = f"  {t.lower().strip()}  "
        for i in range(len(t2) - 2):
            g = t2[i:i + 3]
            h = int.from_bytes(hashlib.md5(g.encode("utf-8")).digest()[:8], "big")
            vecs[r, h % dim] += 1.0 if (h >> 8) % 2 else -1.0
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return vecs / norms


def embed_texts(texts, model_name, mock=False, batch_size=64):
    """Return L2-normalized embeddings (n, d). Lazy-imports torch stack only when real."""
    if mock or model_name == MOCK_MODEL_NAME:
        return mock_embed(list(texts))
    try:
        import torch
        from sentence_transformers import SentenceTransformer
    except ImportError as e:
        raise SystemExit(
            f"missing dependency for real embeddings ({e}).\n"
            "pip install -r requirements.txt — or run with --mock to smoke-test logic."
        )
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    kwargs = {"trust_remote_code": True} if model_name in TRUST_REMOTE_CODE else {}
    model = SentenceTransformer(model_name, device=device, **kwargs)
    prefix = PREFIXES.get(model_name, "")
    payload = [prefix + t for t in texts] if prefix else list(texts)
    emb = model.encode(payload, batch_size=batch_size,
                       normalize_embeddings=True, show_progress_bar=len(payload) > 200)
    return np.asarray(emb, dtype=np.float32)


def cosine_matrix(emb):
    """Pairwise cosine similarity for L2-normalized embeddings."""
    return emb @ emb.T


def ks_2samp(x, y):
    """Two-sample Kolmogorov–Smirnov: statistic + asymptotic p (Stephens correction).
    Hand-rolled so the risk checks need numpy only."""
    x = np.sort(np.asarray(x, dtype=float))
    y = np.sort(np.asarray(y, dtype=float))
    n1, n2 = len(x), len(y)
    allv = np.concatenate([x, y])
    cdf1 = np.searchsorted(x, allv, side="right") / n1
    cdf2 = np.searchsorted(y, allv, side="right") / n2
    d = float(np.max(np.abs(cdf1 - cdf2)))
    ne = n1 * n2 / (n1 + n2)
    lam = (np.sqrt(ne) + 0.12 + 0.11 / np.sqrt(ne)) * d
    p = 2.0 * sum((-1.0) ** (k - 1) * np.exp(-2.0 * (k * lam) ** 2) for k in range(1, 101))
    return d, float(min(max(p, 0.0), 1.0))


def irreducible_overlap(hit_sims, miss_sims):
    """Mini-IO preview (PLAN §5): IO = 1 - max_tau BalancedAccuracy(tau),
    predicting HIT when sim > tau. Returns (io, best_tau)."""
    hit_sims = np.asarray(hit_sims, dtype=float)
    miss_sims = np.asarray(miss_sims, dtype=float)
    cuts = np.unique(np.concatenate([hit_sims, miss_sims]))
    cands = np.unique(np.concatenate([cuts - 1e-9, cuts + 1e-9]))
    best_ba, best_tau = 0.0, None
    for t in cands:
        ba = 0.5 * ((hit_sims > t).mean() + (miss_sims <= t).mean())
        if ba > best_ba:
            best_ba, best_tau = float(ba), float(t)
    return 1.0 - best_ba, best_tau
