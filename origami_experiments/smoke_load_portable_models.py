"""Instantiate final portable taskfit models and load their state dicts."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import torch

from modules.origami_taskfit_models import (
    OrigamiForwardGATTaskfit,
    OrigamiForwardResMLP,
    OrigamiForwardTransformerTaskfit,
    OrigamiInverseCVAEHeaded,
    OrigamiInverseDiffusionTaskfit,
    OrigamiInverseDiscreteClassifier,
    OrigamiInverseResMLP,
)


SCRIPT_DIR = Path(__file__).resolve().parent
MANIFEST = SCRIPT_DIR / "best_models_taskfit" / "portable_checkpoint_manifest.csv"


def instantiate(name: str, config: dict, diffusion_config: dict | None):
    if name == "forward_resmlp":
        return OrigamiForwardResMLP(
            hidden_dim=config.get("forward_hidden", 256),
            dropout=config.get("forward_dropout", 0.1),
        )
    if name == "forward_gat_physical_sparse":
        return OrigamiForwardGATTaskfit(
            hidden_dim=config.get("gat_hidden", 256),
            heads=config.get("gat_heads", 8),
            mlp_dim=config.get("gat_mlp_dim", config.get("gat_hidden", 256)),
            dropout=config.get("gat_dropout", config.get("forward_dropout", 0.1)),
        )
    if name == "forward_transformer":
        return OrigamiForwardTransformerTaskfit(
            hidden_dim=config.get("transformer_hidden", 192),
            num_heads=config.get("transformer_heads", 4),
            num_layers=config.get("transformer_layers", 3),
            dropout=config.get("transformer_dropout", 0.12),
        )
    if name == "inverse_resmlp":
        return OrigamiInverseResMLP(
            hidden_dim=config.get("inverse_hidden", 256),
            dropout=config.get("inverse_dropout", 0.2),
        )
    if name == "inverse_cvae_physical":
        return OrigamiInverseCVAEHeaded(
            latent_dim=config.get("cvae_latent_dim", 8),
            hidden_dim=config.get("cvae_hidden", 512),
        )
    if name == "inverse_diffusion_x0":
        return OrigamiInverseDiffusionTaskfit(
            target_dim=(diffusion_config or {}).get("target_dim", 8),
            time_dim=config.get("diffusion_time_dim", 64),
            cond_dim=config.get("diffusion_cond_dim", 128),
            hidden_dim=config.get("diffusion_hidden", 512),
            dropout=config.get("diffusion_dropout", 0.1),
        )
    if name == "inverse_classifier":
        return OrigamiInverseDiscreteClassifier(
            hidden_dim=config.get("inverse_classifier_hidden", 256),
            dropout=config.get("inverse_classifier_dropout", 0.1),
        )
    raise ValueError(f"Unknown model: {name}")


def main() -> None:
    rows = []
    manifest = pd.read_csv(MANIFEST)
    for _, item in manifest.iterrows():
        ckpt = torch.load(item["portable_checkpoint"], map_location="cpu", weights_only=False)
        model = instantiate(item["name"], ckpt.get("config", {}), ckpt.get("diffusion_config"))
        missing, unexpected = model.load_state_dict(ckpt["model_state"], strict=False)
        ok = not missing and not unexpected
        rows.append(
            {
                "name": item["name"],
                "portable_checkpoint": item["portable_checkpoint"],
                "load_state_ok": ok,
                "missing_keys": ";".join(missing),
                "unexpected_keys": ";".join(unexpected),
            }
        )
    out = pd.DataFrame(rows)
    out_path = SCRIPT_DIR / "best_models_taskfit" / "portable_load_smoke.csv"
    out.to_csv(out_path, index=False)
    print(out[["name", "load_state_ok"]].to_string(index=False))
    print(f"[Saved] {out_path}")


if __name__ == "__main__":
    main()
