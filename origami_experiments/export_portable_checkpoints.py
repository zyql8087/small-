"""Export selected taskfit checkpoints without pickled Python objects."""

from __future__ import annotations

import copy
from pathlib import Path

import pandas as pd
import torch

from audit_trained_models import MODEL_CANDIDATES
from train_taskfit import TaskfitPreprocessor


SCRIPT_DIR = Path(__file__).resolve().parent
OUT_DIR = SCRIPT_DIR / "best_models_taskfit"


def scalar_or_list(value):
    if hasattr(value, "tolist"):
        return value.tolist()
    return value


def scaler_state(scaler) -> dict:
    return {
        "mean": scalar_or_list(getattr(scaler, "mean_", None)),
        "scale": scalar_or_list(getattr(scaler, "scale_", None)),
        "var": scalar_or_list(getattr(scaler, "var_", None)),
        "n_features_in": scalar_or_list(getattr(scaler, "n_features_in_", None)),
        "n_samples_seen": scalar_or_list(getattr(scaler, "n_samples_seen_", None)),
    }


def preprocessor_state(prep: TaskfitPreprocessor | None) -> dict | None:
    if prep is None:
        return None
    return {
        "class": "TaskfitPreprocessor",
        "continuous_transform": "log10",
        "curve_transform": "log10",
        "cont_scaler": scaler_state(prep.cont_scaler),
        "curve_scaler": scaler_state(prep.curve_scaler),
    }


def load_legacy_checkpoint(path: Path) -> dict:
    globals()["TaskfitPreprocessor"] = TaskfitPreprocessor
    return torch.load(path, map_location="cpu", weights_only=False)


def export_checkpoint(item: dict) -> dict:
    source = Path(item["checkpoint"])
    ckpt = load_legacy_checkpoint(source)
    portable = copy.deepcopy(ckpt)
    portable["preprocessor_state"] = preprocessor_state(portable.get("preprocessor"))
    portable.pop("preprocessor", None)
    portable["portable_checkpoint"] = True
    portable["source_checkpoint"] = str(source)
    portable["model_name"] = item["name"]
    portable["model_role"] = item["role"]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"{item['name']}_portable.pth"
    torch.save(portable, out_path)
    reloaded = torch.load(out_path, map_location="cpu", weights_only=False)
    model_state = reloaded.get("model_state")
    ok = isinstance(model_state, dict) and bool(model_state) and reloaded.get("portable_checkpoint") is True
    return {
        "name": item["name"],
        "role": item["role"],
        "production_candidate": item["production"],
        "source_checkpoint": str(source),
        "portable_checkpoint": str(out_path),
        "portable_load_ok": ok,
        "size_bytes": out_path.stat().st_size,
    }


def main() -> None:
    export_names = {
        "forward_resmlp",
        "forward_gat_physical_sparse",
        "forward_transformer",
        "inverse_resmlp",
        "inverse_cvae_physical",
        "inverse_diffusion_x0",
        "inverse_classifier",
    }
    rows = [export_checkpoint(item) for item in MODEL_CANDIDATES if item["name"] in export_names]
    manifest = pd.DataFrame(rows)
    manifest.to_csv(OUT_DIR / "portable_checkpoint_manifest.csv", index=False)
    try:
        manifest.to_excel(OUT_DIR / "portable_checkpoint_manifest.xlsx", index=False)
    except Exception as exc:  # pragma: no cover - optional Excel engine.
        print(f"[WARN] Could not write xlsx: {exc}")
    print(manifest[["name", "role", "portable_load_ok", "portable_checkpoint"]].to_string(index=False))
    print(f"[Saved] {OUT_DIR / 'portable_checkpoint_manifest.csv'}")


if __name__ == "__main__":
    main()
