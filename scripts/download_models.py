#!/usr/bin/env python3
"""Pre-download all evaluation models from config/models.yaml to the local HF cache.

Risk-check defaults download first. Skips weight formats we don't use
(onnx/openvino/tf). Safe to re-run — snapshot_download resumes/no-ops.
"""
import sys
from pathlib import Path

import yaml
from huggingface_hub import snapshot_download

REPO = Path(__file__).resolve().parents[1]
IGNORE = ["*.onnx", "onnx/*", "openvino/*", "*.h5", "*.msgpack", "*.ot", "*.tflite",
          "flax_model*", "tf_model*", "rust_model*"]


def main() -> int:
    cfg = yaml.safe_load((REPO / "config" / "models.yaml").read_text(encoding="utf-8"))
    first = list(cfg.get("risk_check_defaults", []))
    ids = [m["id"] for m in cfg["embedding_models"]] + [m["id"] for m in cfg["cross_encoders"]]
    ordered = first + [i for i in ids if i not in first]
    failed = []
    for i, mid in enumerate(ordered, 1):
        print(f"[{i}/{len(ordered)}] {mid} ...", flush=True)
        try:
            p = snapshot_download(mid, ignore_patterns=IGNORE)
            print(f"    ok -> {p}", flush=True)
        except Exception as e:  # keep going; report at the end
            print(f"    FAILED: {e}", flush=True)
            failed.append((mid, str(e)))
    print("\n== summary ==")
    print(f"ok: {len(ordered) - len(failed)}/{len(ordered)}")
    for mid, e in failed:
        print(f"FAILED {mid}: {e[:200]}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
