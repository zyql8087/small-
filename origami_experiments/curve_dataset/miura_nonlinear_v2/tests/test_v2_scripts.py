from __future__ import annotations

import importlib.util
import math
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = EXPERIMENT_DIR / "scripts"
MATLAB_GENERATOR = EXPERIMENT_DIR / "matlab" / "GenerateOrigamiForceDisplacementCurves.m"


def load_script(name: str):
    path = SCRIPTS_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def read_matlab_generator() -> str:
    return MATLAB_GENERATOR.read_text(encoding="utf-8")


class V2ScriptTests(unittest.TestCase):
    def test_build_defaults_to_80_curve_points_when_spec_is_absent(self) -> None:
        build = load_script("build_curve_dataset_npz")

        self.assertEqual(build.DEFAULT_CURVE_POINTS, 80)
        self.assertEqual(build.resolve_curve_points({}, None), 80)

    def test_build_rejects_missing_physics_columns_by_default(self) -> None:
        build = load_script("build_curve_dataset_npz")
        conditions = pd.DataFrame(
            {
                "curve_id": [0],
                "load_case": ["bending"],
                "deployment": [0.3],
                "response_axis": ["z"],
            }
        )
        curve_df = pd.DataFrame(
            {
                "curve_id": [0, 0],
                "step": [1, 2],
                "force": [1.0, 2.0],
                "displacement": [0.01, 0.02],
                "converged": [True, True],
            }
        )

        with self.assertRaisesRegex(ValueError, "physical summary columns"):
            build.stack_one_sample(curve_df, conditions, curve_points=2, require_physics=True)

    def test_build_can_pack_legacy_curves_when_physics_is_explicitly_optional(self) -> None:
        build = load_script("build_curve_dataset_npz")
        conditions = pd.DataFrame(
            {
                "curve_id": [0],
                "load_case": ["bending"],
                "deployment": [0.3],
                "response_axis": ["z"],
            }
        )
        curve_df = pd.DataFrame(
            {
                "curve_id": [0, 0],
                "step": [1, 2],
                "force": [1.0, 2.0],
                "displacement": [0.01, 0.02],
                "converged": [True, True],
            }
        )

        _, _, _, physics = build.stack_one_sample(
            curve_df,
            conditions,
            curve_points=2,
            require_physics=False,
        )

        self.assertEqual(physics.shape, (1, 2, len(build.PHYSICS_COLS)))
        self.assertTrue(np.isnan(physics).all())

    def test_build_filters_quality_outliers_before_split(self) -> None:
        build = load_script("build_curve_dataset_npz")
        parameters = pd.DataFrame({"sample_id": ["ok", "bad"], "pattern": [1, 1]})
        force = np.ones((2, 1, 2), dtype=np.float32)
        displacement = np.array([[[0.01, 0.02]], [[0.01, 0.03]]], dtype=np.float32)
        converged = np.ones((2, 1, 2), dtype=bool)
        physics = np.zeros((2, 1, 2, len(build.PHYSICS_COLS)), dtype=np.float32)
        strain_index = build.PHYSICS_COLS.index("max_bar_strain")
        physics[1, 0, 1, strain_index] = 1.0e6

        filtered = build.filter_quality_outliers(
            parameters,
            force,
            displacement,
            converged,
            physics,
            max_physics_abs=1.0e5,
            max_displacement=None,
        )

        filtered_parameters, filtered_force, filtered_displacement, filtered_converged, filtered_physics, summary = filtered
        self.assertEqual(filtered_parameters["sample_id"].tolist(), ["ok"])
        self.assertEqual(filtered_force.shape[0], 1)
        self.assertEqual(filtered_displacement.shape[0], 1)
        self.assertEqual(filtered_converged.shape[0], 1)
        self.assertEqual(filtered_physics.shape[0], 1)
        self.assertEqual(summary["removed_samples"], 1)
        self.assertEqual(summary["removed_sample_ids"], ["bad"])

    def test_inverse_diffusion_snaps_and_clips_generated_parameters(self) -> None:
        inverse = load_script("train_inverse_curve_diffusion")
        raw = np.array(
            [
                [0.8, 25.0, 11.0, -1.0, 5.0, 0.5, 1.0e12, -2.0],
                [1.2, 35.0, 7.0, 0.5, 0.2, 0.3, 2.0, 3.0],
            ],
            dtype=np.float32,
        )
        category_values = [
            np.array([1.0], dtype=np.float32),
            np.array([24.0, 30.0, 36.0], dtype=np.float32),
            np.array([6.0, 9.0, 12.0], dtype=np.float32),
        ]
        continuous_min = np.zeros(5, dtype=np.float32)
        continuous_max = np.ones(5, dtype=np.float32)

        snapped = inverse.snap_and_clip_raw_parameters(raw, category_values, continuous_min, continuous_max)

        np.testing.assert_allclose(snapped[:, 0], [1.0, 1.0])
        np.testing.assert_allclose(snapped[:, 1], [24.0, 36.0])
        np.testing.assert_allclose(snapped[:, 2], [12.0, 6.0])
        self.assertTrue(np.all(snapped[:, 3:] >= 0.0))
        self.assertTrue(np.all(snapped[:, 3:] <= 1.0))

    def test_inverse_diffusion_reports_channelwise_closed_loop_metrics(self) -> None:
        inverse = load_script("train_inverse_curve_diffusion")
        target = np.zeros((2, 6, 4, 2), dtype=np.float32)
        pred = target.copy()
        target[..., 0] = np.linspace(0.0, 1.0, 4)
        target[..., 1] = np.linspace(0.0, 10.0, 4)
        pred[..., 0] = target[..., 0] + 0.1
        pred[..., 1] = target[..., 1] + 1.0
        pred[0, 0, 0, 0] = -0.2
        pred[0, 0, 0, 1] = -5.0

        metrics = inverse.curve_channel_metrics(pred, target)

        self.assertIn("displacement_nrmse_std_percent", metrics)
        self.assertIn("force_nrmse_std_percent", metrics)
        self.assertIn("negative_displacement_fraction", metrics)
        self.assertIn("negative_force_fraction", metrics)
        self.assertGreater(metrics["displacement_rmse"], 0.0)
        self.assertGreater(metrics["force_rmse"], 0.0)
        self.assertGreater(metrics["negative_displacement_fraction"], 0.0)
        self.assertGreater(metrics["negative_force_fraction"], 0.0)

    def test_inverse_diffusion_candidate_score_penalizes_negative_curves(self) -> None:
        inverse = load_script("train_inverse_curve_diffusion")
        curve_mse = np.array([[0.010, 0.012]], dtype=np.float32)
        pred_curve = np.ones((1, 2, 6, 4, 2), dtype=np.float32)
        pred_curve[0, 0, :, :, 1] = -1.0

        score = inverse.candidate_selection_scores(curve_mse, pred_curve, negative_curve_weight=0.25)

        self.assertGreater(score[0, 0], score[0, 1])

    def test_extrapolate_high_w_split_uses_exact_top_fraction(self) -> None:
        build = load_script("build_curve_dataset_npz")
        parameters = pd.DataFrame(
            {
                "pattern": [1] * 10,
                "m": [24] * 10,
                "n": [9] * 10,
                "W": [1.0, 2.0, 3.0, 4.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0],
            }
        )

        train_idx, test_idx = build.split_indices(parameters, "extrapolate_high_W", test_size=0.2, seed=42)

        self.assertEqual(len(test_idx), math.ceil(len(parameters) * 0.2))
        self.assertTrue(set(train_idx).isdisjoint(set(test_idx)))
        self.assertEqual(set(train_idx).union(set(test_idx)), set(range(len(parameters))))

    def test_smoke_train_can_use_displacement_plus_physics_targets(self) -> None:
        smoke = load_script("smoke_train_curve_dataset")
        train = {
            "y": np.array([[0.0, 1.0]], dtype=np.float32),
            "physics_raw": np.arange(14, dtype=np.float32).reshape(1, 1, 2, 7),
        }
        test = {
            "y": np.array([[2.0, 3.0]], dtype=np.float32),
            "physics_raw": (np.arange(14, dtype=np.float32) + 1).reshape(1, 1, 2, 7),
        }

        y_train, y_test, info = smoke.prepare_targets(train, test, target_mode="displacement_physics")

        self.assertEqual(y_train.shape, (1, 16))
        self.assertEqual(y_test.shape, (1, 16))
        self.assertEqual(info["target_mode"], "displacement_physics")
        self.assertEqual(info["physics_target_dim"], 14)

    def test_matlab_history_dimension_checks_use_raw_history(self) -> None:
        source = read_matlab_generator()

        self.assertIn("if size(rawHistory, 1) < curvePoints", source)
        self.assertIn("if size(rawHistory, 2) < minColumns", source)
        self.assertNotIn("if size(history, 1) < curvePoints", source)
        self.assertNotIn("if size(history, 2) < minColumns", source)

    def test_matlab_rejects_overlapping_support_and_force_nodes(self) -> None:
        source = read_matlab_generator()

        self.assertIn("intersect(supNode, forceNode)", source)
        self.assertIn("Support and force nodes overlap", source)

    def test_matlab_uses_targeted_generate_origami_dataset_paths(self) -> None:
        source = read_matlab_generator()

        self.assertIn("addGenerateOrigamiDataSetPaths(projectRoot)", source)
        self.assertIn("Data_Origami_Sheet_MaterialProperty", source)
        self.assertNotIn("addpath(genpath(fullfile(projectRoot, 'external', 'GenerateOrigamiDataSet')))", source)

    def test_matlab_max_abs_history_avoids_redundant_column_guard(self) -> None:
        source = read_matlab_generator()

        self.assertNotIn("if size(rawHistory, 2) < 1", source)

    def test_nonlinear_audit_labels_nonmonotonic_displacement_without_issue(self) -> None:
        audit = load_script("audit_curve_batch")
        param_row = self.make_param_row("miura_99999")
        curve_df = self.make_curve_df_with_one_nonmonotonic_curve("miura_99999")

        with tempfile.TemporaryDirectory() as tmp:
            curves_dir = Path(tmp)
            curve_df.to_csv(curves_dir / "miura_99999.csv", index=False)
            rows, issues = audit.audit_one_sample(
                param_row,
                curves_dir,
                curve_points=4,
                final_load=4.0,
                max_rel_stiff_error=10.0,
                audit_mode="nonlinear",
                min_secant_change_ratio=0.0,
                require_physics=False,
            )

        self.assertFalse(any("displacement is not monotonic" in issue for issue in issues))
        curve3 = next(row for row in rows if row["curve_id"] == 3)
        self.assertEqual(curve3["nonmonotonic_segments"], 1)
        self.assertTrue(curve3["snap_like_response"])
        self.assertAlmostEqual(curve3["max_displacement_drop"], 0.1)

    def test_linear_audit_still_rejects_nonmonotonic_displacement(self) -> None:
        audit = load_script("audit_curve_batch")
        param_row = self.make_param_row("miura_99998")
        curve_df = self.make_curve_df_with_one_nonmonotonic_curve("miura_99998")

        with tempfile.TemporaryDirectory() as tmp:
            curves_dir = Path(tmp)
            curve_df.to_csv(curves_dir / "miura_99998.csv", index=False)
            _, issues = audit.audit_one_sample(
                param_row,
                curves_dir,
                curve_points=4,
                final_load=4.0,
                max_rel_stiff_error=10.0,
                audit_mode="linear",
                min_secant_change_ratio=0.0,
                require_physics=False,
            )

        self.assertTrue(any("displacement is not monotonic" in issue for issue in issues))

    def test_audit_accepts_inverse_validation_source_and_prefix_when_configured(self) -> None:
        audit = load_script("audit_curve_batch")
        param_row = self.make_param_row("invval_0001_miura_00001")
        param_row["source_name"] = "inverse_diffusion"
        curve_df = self.make_curve_df_with_one_nonmonotonic_curve("invval_0001_miura_00001")

        with tempfile.TemporaryDirectory() as tmp:
            curves_dir = Path(tmp)
            curve_df.to_csv(curves_dir / "invval_0001_miura_00001.csv", index=False)
            _, issues = audit.audit_one_sample(
                param_row,
                curves_dir,
                curve_points=4,
                final_load=4.0,
                max_rel_stiff_error=10.0,
                audit_mode="nonlinear",
                min_secant_change_ratio=0.0,
                require_physics=False,
                expected_source_name="inverse_diffusion",
                sample_id_prefix="invval_",
            )

        self.assertFalse(any("source_name is not" in issue for issue in issues))
        self.assertFalse(any("sample_id does not start" in issue for issue in issues))

    def test_prepare_inverse_validation_uses_lowest_closed_loop_generated_parameters(self) -> None:
        prepare = load_script("prepare_inverse_swomps_validation")
        generated = pd.DataFrame(
            {
                "sample_id": ["miura_00003", "miura_00001", "miura_00002"],
                "closed_loop_scaled_mse": [0.30, 0.10, 0.20],
                "generated_pattern": [1, 1, 1],
                "generated_m": [24, 36, 24],
                "generated_n": [6, 9, 12],
                "generated_tcrease": [0.0005, 0.0006, 0.0007],
                "generated_tpanel": [0.002, 0.003, 0.004],
                "generated_W": [0.001, 0.002, 0.003],
                "generated_creaseE": [1.0e9, 2.0e9, 3.0e9],
                "generated_panelE": [4.0e9, 5.0e9, 6.0e9],
            }
        )
        conditions = pd.DataFrame(
            {
                "curve_id": [0, 1],
                "load_case": ["bending", "axial"],
                "deployment": [0.3, 0.6],
                "response_axis": ["z", "x"],
            }
        )

        selected = prepare.select_generated_candidates(generated, top_k=2)
        params = prepare.make_parameter_table(selected)
        jobs = prepare.make_simulation_jobs(params, conditions)

        self.assertEqual(selected["target_sample_id"].tolist(), ["miura_00001", "miura_00002"])
        self.assertEqual(params["sample_id"].tolist(), ["invval_0001_miura_00001", "invval_0002_miura_00002"])
        self.assertEqual(params["m"].tolist(), [36.0, 24.0])
        self.assertEqual(params["tpanel"].tolist(), [0.003, 0.004])
        self.assertEqual(jobs.shape[0], 4)
        self.assertEqual(jobs.loc[0, "sample_id"], "invval_0001_miura_00001")

    def test_reference_stiffness_jobs_use_final_force_over_displacement(self) -> None:
        build = load_script("build_inverse_validation_jobs_from_reference")
        params = pd.DataFrame(
            {
                "sample_id": ["invval_0001_miura_00001"],
                "pattern": [1],
                "m": [24],
                "n": [9],
                "tcrease": [0.0005],
                "tpanel": [0.002],
                "W": [0.001],
                "creaseE": [2.0e9],
                "panelE": [3.0e9],
            }
        )

        with tempfile.TemporaryDirectory() as tmp:
            curves_dir = Path(tmp)
            rows = []
            for curve_id in range(6):
                for step in [1, 2, 3]:
                    rows.append(
                        {
                            "sample_id": "invval_0001_miura_00001",
                            "curve_id": curve_id,
                            "step": step,
                            "force": float(step),
                            "displacement": float(step) / float(curve_id + 2),
                            "converged": True,
                        }
                    )
            pd.DataFrame(rows).to_csv(curves_dir / "invval_0001_miura_00001.csv", index=False)

            enriched = build.attach_reference_stiffness(params, curves_dir, curve_points=3)

        self.assertAlmostEqual(enriched.loc[0, "bendstiff30"], 2.0)
        self.assertAlmostEqual(enriched.loc[0, "bendstiff60"], 3.0)
        self.assertAlmostEqual(enriched.loc[0, "axialstiff90"], 7.0)

    def test_evaluate_inverse_swomps_validation_reports_curve_errors(self) -> None:
        evaluate = load_script("evaluate_inverse_swomps_validation")
        target = self.make_curve_df_with_one_nonmonotonic_curve("miura_00001")
        generated = target.copy()
        generated["sample_id"] = "invval_0001_miura_00001"
        generated["displacement"] = generated["displacement"] + 0.01
        selected = pd.DataFrame(
            {
                "sample_id": ["miura_00001"],
                "validation_sample_id": ["invval_0001_miura_00001"],
                "rank": [1],
                "closed_loop_scaled_mse": [0.001],
            }
        )

        metrics = evaluate.evaluate_one_candidate(
            selected.iloc[0],
            target,
            generated,
            curve_points=4,
        )

        self.assertEqual(metrics["target_sample_id"], "miura_00001")
        self.assertEqual(metrics["validation_sample_id"], "invval_0001_miura_00001")
        self.assertGreater(metrics["displacement_rmse"], 0.0)
        self.assertAlmostEqual(metrics["force_rmse"], 0.0)

    @staticmethod
    def make_param_row(sample_id: str) -> pd.Series:
        values = {
            "sample_id": sample_id,
            "source_name": "miura",
            "pattern": 1,
            "m": 24,
            "n": 9,
            "tcrease": 0.0005,
            "tpanel": 0.002,
            "W": 0.001,
            "creaseE": 2.0e9,
            "panelE": 3.0e9,
            "bendstiff30": 10.0,
            "bendstiff60": 10.0,
            "bendstiff90": 10.0,
            "axialstiff30": 10.0,
            "axialstiff60": 10.0,
            "axialstiff90": 10.0,
        }
        return pd.Series(values)

    @staticmethod
    def make_curve_df_with_one_nonmonotonic_curve(sample_id: str) -> pd.DataFrame:
        rows = []
        for curve_id in range(6):
            load_case = "axial" if curve_id >= 3 else "bending"
            deployment = [0.3, 0.6, 0.9, 0.3, 0.6, 0.9][curve_id]
            response_axis = "x" if curve_id >= 3 else "z"
            displacements = [0.1, 0.2, 0.3, 0.4]
            if curve_id == 3:
                displacements = [0.1, 0.3, 0.2, 0.4]
            for step, displacement in enumerate(displacements, start=1):
                rows.append(
                    {
                        "sample_id": sample_id,
                        "curve_id": curve_id,
                        "load_case": load_case,
                        "deployment": deployment,
                        "response_axis": response_axis,
                        "step": step,
                        "force": float(step),
                        "displacement": displacement,
                        "converged": True,
                        "final_load": 4.0,
                    }
                )
        return pd.DataFrame(rows)


if __name__ == "__main__":
    unittest.main()
