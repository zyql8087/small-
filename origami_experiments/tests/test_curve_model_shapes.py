from __future__ import annotations

import unittest
import importlib.util
import tempfile
from unittest.mock import patch
from pathlib import Path

import numpy as np
import torch

from origami_experiments.modules.origami_curve_models import (
    OrigamiCurveConditionalDiffusion,
    OrigamiCurveGNNTransformerForward,
    build_parameter_adjacency,
)


SCRIPT_DIR = (
    Path(__file__).resolve().parents[1]
    / "curve_dataset"
    / "miura_nonlinear_v2"
    / "scripts"
)


def load_script(name: str):
    path = SCRIPT_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class CurveModelShapeTests(unittest.TestCase):
    def test_forward_gnn_transformer_predicts_six_condition_curves(self) -> None:
        model = OrigamiCurveGNNTransformerForward(
            hidden_dim=48,
            gnn_heads=2,
            encoder_layers=1,
            decoder_layers=1,
            num_curve_points=80,
            curve_channels=2,
            dropout=0.0,
        )
        cat_ids = torch.tensor([[0, 1, 2], [0, 2, 1]], dtype=torch.long)
        cont_scaled = torch.randn(2, 5)
        adj = build_parameter_adjacency()

        pred = model(cat_ids, cont_scaled, adj)

        self.assertEqual(pred.shape, (2, 6, 80, 2))
        self.assertTrue(torch.isfinite(pred).all())

    def test_forward_gnn_transformer_parameterizes_curves_as_positive_increments(self) -> None:
        model = OrigamiCurveGNNTransformerForward(
            hidden_dim=32,
            gnn_heads=2,
            num_heads=4,
            encoder_layers=1,
            decoder_layers=1,
            temporal_refiner_layers=1,
            num_curve_points=16,
            curve_channels=2,
            dropout=0.0,
        )
        cat_ids = torch.tensor([[0, 1, 2], [1, 2, 0]], dtype=torch.long)
        cont_scaled = torch.randn(2, 5)

        pred = model(cat_ids, cont_scaled)
        step_deltas = pred[:, :, 1:, :] - pred[:, :, :-1, :]

        self.assertEqual(pred.shape, (2, 6, 16, 2))
        self.assertTrue(torch.isfinite(pred).all())
        self.assertTrue(torch.all(step_deltas >= -1e-6))

    def test_forward_gnn_transformer_can_leave_displacement_nonmonotonic_while_force_is_positive(self) -> None:
        model = OrigamiCurveGNNTransformerForward(
            hidden_dim=32,
            gnn_heads=2,
            num_heads=4,
            encoder_layers=1,
            decoder_layers=1,
            num_curve_points=4,
            curve_channels=2,
            monotonic_displacement=False,
            dropout=0.0,
        )
        raw_curve = torch.zeros(1, 1, 4, 2)
        raw_curve[..., 0] = torch.tensor([0.0, 2.0, -1.0, 1.0])
        raw_curve[..., 1] = torch.tensor([0.0, -5.0, -5.0, -5.0])

        curve = model._parameterize_curve_response(raw_curve)

        torch.testing.assert_close(curve[..., 0], raw_curve[..., 0])
        self.assertTrue(torch.all(curve[:, :, 1:, 1] - curve[:, :, :-1, 1] >= 0.0))

    def test_forward_gnn_transformer_conditions_decoder_on_force_schedule(self) -> None:
        model = OrigamiCurveGNNTransformerForward(
            hidden_dim=32,
            gnn_heads=2,
            num_heads=4,
            encoder_layers=1,
            decoder_layers=1,
            temporal_refiner_layers=1,
            num_curve_points=12,
            curve_channels=1,
            dropout=0.0,
        )
        cat_ids = torch.tensor([[0, 1, 2], [0, 1, 2]], dtype=torch.long)
        cont_scaled = torch.randn(2, 5)
        force_low = torch.linspace(0.0, 1.0, 12).view(1, 1, 12, 1).expand(2, 6, 12, 1)
        force_high = torch.linspace(0.0, 2.0, 12).view(1, 1, 12, 1).expand(2, 6, 12, 1)

        pred_low = model(cat_ids, cont_scaled, force_condition=force_low)
        pred_high = model(cat_ids, cont_scaled, force_condition=force_high)

        self.assertEqual(pred_low.shape, (2, 6, 12, 1))
        self.assertTrue(torch.isfinite(pred_low).all())
        self.assertFalse(torch.allclose(pred_low, pred_high))

    def test_parameter_adjacency_expands_for_derived_continuous_nodes(self) -> None:
        adj = build_parameter_adjacency(num_nodes=21)

        self.assertEqual(adj.shape, (21, 21))
        self.assertTrue(torch.allclose(adj, adj.T))
        self.assertTrue(torch.all(torch.diag(adj) == 1.0))
        self.assertGreater(float(adj[8:, 3:8].sum()), 0.0)

    def test_forward_gnn_transformer_adds_ordinal_numeric_encoding_to_categorical_nodes(self) -> None:
        model = OrigamiCurveGNNTransformerForward(
            hidden_dim=32,
            gnn_heads=2,
            num_heads=4,
            encoder_layers=1,
            decoder_layers=1,
            num_curve_points=8,
            dropout=0.0,
        )
        cat_ids = torch.tensor([[0, 0, 0], [0, 2, 2]], dtype=torch.long)
        cont_scaled = torch.zeros(2, 5)

        nodes = model._nodes_from_hard(cat_ids, cont_scaled)

        self.assertEqual(len(model.cat_value_encoders), 3)
        self.assertEqual(nodes.shape, (2, 8, 32))
        self.assertFalse(torch.allclose(nodes[0, 1], nodes[1, 1]))
        self.assertFalse(torch.allclose(nodes[0, 2], nodes[1, 2]))

    def test_forward_gnn_transformer_supports_soft_categorical_inputs(self) -> None:
        model = OrigamiCurveGNNTransformerForward(
            hidden_dim=32,
            gnn_heads=2,
            encoder_layers=1,
            decoder_layers=1,
            num_curve_points=16,
            curve_channels=2,
            dropout=0.0,
        )
        cat_probs = [
            torch.tensor([[1.0, 0.0]], dtype=torch.float32),
            torch.tensor([[0.0, 1.0, 0.0]], dtype=torch.float32),
            torch.tensor([[0.0, 0.0, 1.0]], dtype=torch.float32),
        ]
        cont_scaled = torch.randn(1, 5)

        pred = model.forward_from_probs(cat_probs, cont_scaled)

        self.assertEqual(pred.shape, (1, 6, 16, 2))

    def test_forward_gnn_transformer_uses_temporal_refinement_decoder(self) -> None:
        model = OrigamiCurveGNNTransformerForward(
            hidden_dim=32,
            gnn_heads=2,
            num_heads=4,
            encoder_layers=1,
            decoder_layers=1,
            temporal_refiner_layers=2,
            temporal_kernel_size=5,
            num_curve_points=20,
            curve_channels=2,
            dropout=0.0,
        )
        cat_ids = torch.tensor([[0, 1, 2]], dtype=torch.long)
        cont_scaled = torch.randn(1, 5)

        pred = model(cat_ids, cont_scaled)

        self.assertEqual(pred.shape, (1, 6, 20, 2))
        self.assertEqual(len(model.temporal_refiner), 2)

    def test_forward_gnn_transformer_can_return_physics_auxiliary_history(self) -> None:
        model = OrigamiCurveGNNTransformerForward(
            hidden_dim=40,
            gnn_heads=2,
            num_heads=4,
            encoder_layers=1,
            decoder_layers=1,
            num_curve_points=12,
            curve_channels=2,
            physics_channels=7,
            dropout=0.0,
        )
        cat_ids = torch.tensor([[0, 1, 2]], dtype=torch.long)
        cont_scaled = torch.randn(1, 5)

        outputs = model.forward_with_aux(cat_ids, cont_scaled)

        self.assertEqual(outputs["curve"].shape, (1, 6, 12, 2))
        self.assertEqual(outputs["physics"].shape, (1, 6, 12, 7))
        self.assertTrue(torch.isfinite(outputs["curve"]).all())
        self.assertTrue(torch.isfinite(outputs["physics"]).all())

    def test_inverse_diffusion_conditions_on_curve_tensor(self) -> None:
        model = OrigamiCurveConditionalDiffusion(
            target_dim=8,
            curve_channels=2,
            physics_channels=0,
            hidden_dim=96,
            cond_dim=64,
            time_dim=32,
            num_curve_points=80,
            encoder_layers=1,
            num_heads=4,
            dropout=0.0,
        )
        x_t = torch.randn(3, 8)
        timesteps = torch.tensor([1, 17, 63], dtype=torch.long)
        curve = torch.randn(3, 6, 80, 2)

        eps = model(x_t, timesteps, curve)

        self.assertEqual(eps.shape, (3, 8))
        self.assertTrue(torch.isfinite(eps).all())

    def test_signed_log_robust_physics_scaler_handles_extreme_outliers(self) -> None:
        train_script = load_script("train_curve_forward_gnn_transformer")
        scaler = train_script.RobustLogPhysicsScaler(clip=6.0)
        physics = np.array(
            [
                [[[[0.0, 1.0], [10.0, -10.0], [1.0e12, -1.0e12]]]],
                [[[[0.5, 2.0], [20.0, -20.0], [2.0e12, -2.0e12]]]],
            ],
            dtype=np.float32,
        ).reshape(2, 1, 3, 2)

        transformed = scaler.fit_transform(physics)

        self.assertEqual(transformed.shape, physics.shape)
        self.assertTrue(np.isfinite(transformed).all())
        self.assertLessEqual(float(np.max(np.abs(transformed))), 6.0)

    def test_train_script_json_ready_serializes_paths_and_numpy_scalars(self) -> None:
        train_script = load_script("train_curve_forward_gnn_transformer")

        ready = train_script.json_ready({"path": Path("data"), "value": np.float32(1.5)})

        self.assertEqual(ready, {"path": "data", "value": 1.5})

    def test_train_script_can_initialize_aux_model_from_main_checkpoint(self) -> None:
        train_script = load_script("train_curve_forward_gnn_transformer")
        main_model = OrigamiCurveGNNTransformerForward(
            hidden_dim=32,
            num_heads=4,
            gnn_heads=2,
            encoder_layers=1,
            decoder_layers=1,
            num_curve_points=8,
            physics_channels=0,
            dropout=0.0,
        )
        aux_model = OrigamiCurveGNNTransformerForward(
            hidden_dim=32,
            num_heads=4,
            gnn_heads=2,
            encoder_layers=1,
            decoder_layers=1,
            num_curve_points=8,
            physics_channels=7,
            dropout=0.0,
        )

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "main.pth"
            torch.save({"model_state": main_model.state_dict()}, path)
            info = train_script.load_initial_checkpoint(aux_model, path, torch.device("cpu"))

        self.assertTrue(info["loaded"])
        self.assertGreater(len(info["missing_keys"]), 0)
        self.assertEqual(info["unexpected_keys"], [])

    def test_curve_scaler_inverse_transform_restores_physical_units(self) -> None:
        train_script = load_script("train_curve_forward_gnn_transformer")
        scaler = train_script.CurveChannelScaler()
        curves = np.array(
            [
                [[[[0.1, 1.0], [0.2, 2.0]]]],
                [[[[0.3, 3.0], [0.4, 4.0]]]],
            ],
            dtype=np.float32,
        ).reshape(2, 1, 2, 2)

        restored = scaler.fit(curves).inverse_transform(scaler.transform(curves))

        np.testing.assert_allclose(restored, curves, rtol=1e-6, atol=1e-6)

    def test_denormalized_curve_metrics_are_channel_specific(self) -> None:
        train_script = load_script("train_curve_forward_gnn_transformer")
        pred = np.array([[[[2.0, 10.0], [4.0, 14.0]]]], dtype=np.float32)
        target = np.array([[[[1.0, 8.0], [7.0, 10.0]]]], dtype=np.float32)

        metrics = train_script.denormalized_curve_metrics(pred, target)

        self.assertAlmostEqual(metrics["displacement_mae"], 2.0)
        self.assertAlmostEqual(metrics["force_mae"], 3.0)
        self.assertAlmostEqual(metrics["displacement_rmse"], np.sqrt(5.0))
        self.assertAlmostEqual(metrics["force_rmse"], np.sqrt(10.0))
        self.assertAlmostEqual(metrics["displacement_nrmse_range_percent"], np.sqrt(5.0) / 6.0 * 100.0, places=5)
        self.assertAlmostEqual(metrics["force_nrmse_range_percent"], np.sqrt(10.0) / 2.0 * 100.0, places=5)
        self.assertAlmostEqual(metrics["displacement_nrmse_std_percent"], np.sqrt(5.0) / 3.0 * 100.0, places=5)
        self.assertAlmostEqual(metrics["force_nrmse_std_percent"], np.sqrt(10.0) / 1.0 * 100.0, places=5)

    def test_plot_typical_curves_writes_png_files(self) -> None:
        train_script = load_script("train_curve_forward_gnn_transformer")
        pred = np.zeros((2, 6, 4, 2), dtype=np.float32)
        target = np.zeros((2, 6, 4, 2), dtype=np.float32)
        for sample_idx in range(2):
            for curve_id in range(6):
                target[sample_idx, curve_id, :, 0] = np.linspace(0.0, 0.1 + sample_idx * 0.01, 4)
                target[sample_idx, curve_id, :, 1] = np.linspace(0.0, 10.0 + curve_id, 4)
                pred[sample_idx, curve_id, :, 0] = target[sample_idx, curve_id, :, 0] * 0.9
                pred[sample_idx, curve_id, :, 1] = target[sample_idx, curve_id, :, 1] * 1.1

        with tempfile.TemporaryDirectory() as tmp:
            paths = train_script.plot_typical_curves(
                pred,
                target,
                sample_ids=np.array(["miura_a", "miura_b"]),
                output_dir=Path(tmp),
                max_samples=2,
            )

            self.assertEqual(len(paths), 2)
            self.assertTrue(all(path.exists() and path.suffix == ".png" for path in paths))

    def test_plot_training_history_writes_loss_curve_png(self) -> None:
        train_script = load_script("train_curve_forward_gnn_transformer")
        history = [
            {
                "epoch": 1,
                "train_total": 0.8,
                "train_curve": 0.7,
                "train_physics": 0.05,
                "train_smoothness": 0.03,
                "train_force_monotonic": 0.02,
                "train_displacement_monotonic": 0.01,
                "val_total": 0.9,
                "val_curve": 0.8,
                "val_physics": 0.06,
                "val_smoothness": 0.04,
                "val_force_monotonic": 0.03,
                "val_displacement_monotonic": 0.02,
            },
            {
                "epoch": 2,
                "train_total": 0.5,
                "train_curve": 0.45,
                "train_physics": 0.03,
                "train_smoothness": 0.015,
                "train_force_monotonic": 0.01,
                "train_displacement_monotonic": 0.005,
                "val_total": 0.6,
                "val_curve": 0.55,
                "val_physics": 0.04,
                "val_smoothness": 0.02,
                "val_force_monotonic": 0.015,
                "val_displacement_monotonic": 0.008,
            },
        ]

        with tempfile.TemporaryDirectory() as tmp:
            path = train_script.plot_training_history(history, Path(tmp) / "training_loss_curves.png")

            self.assertTrue(path.exists())
            self.assertEqual(path.suffix, ".png")
            self.assertGreater(path.stat().st_size, 0)

    def test_train_script_defaults_use_stronger_curve_regularization(self) -> None:
        train_script = load_script("train_curve_forward_gnn_transformer")

        with patch("sys.argv", ["train_curve_forward_gnn_transformer.py"]):
            args = train_script.parse_args()

        self.assertAlmostEqual(args.smoothness_weight, 1e-2)
        self.assertAlmostEqual(args.force_monotonic_weight, 1e-2)

    def test_curve_regularization_losses_reward_smooth_monotonic_curves(self) -> None:
        train_script = load_script("train_curve_forward_gnn_transformer")
        steps = torch.linspace(0.0, 1.0, 8)
        smooth = torch.stack([steps, steps * 2.0], dim=-1).view(1, 1, 8, 2)
        jittery = smooth.clone()
        jittery[:, :, 3, 1] = -1.0
        jittery[:, :, 4, 1] = 3.0

        smooth_losses = train_script.curve_regularization_losses(smooth)
        jittery_losses = train_script.curve_regularization_losses(jittery)

        self.assertAlmostEqual(float(smooth_losses["smoothness"]), 0.0, places=6)
        self.assertAlmostEqual(float(smooth_losses["force_monotonic"]), 0.0, places=6)
        self.assertGreater(float(jittery_losses["smoothness"]), 0.0)
        self.assertGreater(float(jittery_losses["force_monotonic"]), 0.0)

    def test_weighted_curve_mse_prioritizes_requested_channel(self) -> None:
        train_script = load_script("train_curve_forward_gnn_transformer")
        pred = torch.tensor([[[[2.0, 2.0]]]], dtype=torch.float32)
        target = torch.zeros_like(pred)

        unweighted = train_script.weighted_curve_mse(pred, target, displacement_weight=1.0, force_weight=1.0)
        displacement_weighted = train_script.weighted_curve_mse(
            pred,
            target,
            displacement_weight=4.0,
            force_weight=1.0,
        )

        self.assertAlmostEqual(float(unweighted), 4.0)
        self.assertAlmostEqual(float(displacement_weighted), 4.0)

        pred = torch.tensor([[[[2.0, 0.0]]]], dtype=torch.float32)
        displacement_only = train_script.weighted_curve_mse(
            pred,
            target,
            displacement_weight=4.0,
            force_weight=1.0,
        )

        self.assertGreater(float(displacement_only), 4.0 / 2.0)

    def test_weighted_curve_mse_can_prioritize_high_displacement_targets(self) -> None:
        train_script = load_script("train_curve_forward_gnn_transformer")
        pred = torch.zeros(1, 1, 2, 2, dtype=torch.float32)
        target = torch.tensor([[[[1.0, 0.0], [10.0, 0.0]]]], dtype=torch.float32)

        unweighted = train_script.weighted_curve_mse(pred, target)
        amplitude_weighted = train_script.weighted_curve_mse(
            pred,
            target,
            displacement_amplitude_weight=2.0,
        )

        self.assertGreater(float(amplitude_weighted), float(unweighted))

    def test_train_script_can_append_physics_inspired_continuous_features(self) -> None:
        train_script = load_script("train_curve_forward_gnn_transformer")
        x_raw = np.array(
            [
                [1.0, 24.0, 6.0, 1.0e-3, 2.0e-3, 3.0e-3, 2.0e9, 3.0e9],
                [1.0, 36.0, 12.0, 2.0e-3, 4.0e-3, 5.0e-3, 4.0e9, 5.0e9],
            ],
            dtype=np.float32,
        )
        base_cont = np.zeros((2, 5), dtype=np.float32)

        features, stats = train_script.build_continuous_features(
            x_raw,
            base_cont,
            augment=True,
        )
        transformed = train_script.apply_continuous_feature_stats(
            x_raw,
            base_cont,
            stats,
            augment=True,
        )

        self.assertGreater(features.shape[1], base_cont.shape[1])
        self.assertEqual(features.shape, transformed.shape)
        self.assertTrue(np.isfinite(features).all())
        self.assertTrue(np.isfinite(transformed).all())


if __name__ == "__main__":
    unittest.main()
