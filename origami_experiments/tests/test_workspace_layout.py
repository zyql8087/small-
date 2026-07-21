"""Regression checks for the functional workspace layout."""

from __future__ import annotations

from pathlib import Path
import unittest


class WorkspaceLayoutTests(unittest.TestCase):
    def test_functional_modules_are_located_in_their_packages(self) -> None:
        root = Path(__file__).resolve().parents[1]
        expected_files = [
            "models/origami_forward_gnn.py",
            "workflows/data/prepare_data.py",
            "workflows/training/train_taskfit.py",
            "workflows/evaluation/evaluate_taskfit.py",
            "workflows/analysis/audit_trained_models.py",
            "workflows/publishing/export_portable_checkpoints.py",
        ]
        for relative_path in expected_files:
            with self.subTest(relative_path=relative_path):
                self.assertTrue((root / relative_path).is_file())

    def test_snap_probe_is_classified_as_curve_dataset_probe(self) -> None:
        root = Path(__file__).resolve().parents[1]
        self.assertTrue((root / "curve_dataset" / "probes" / "snap_probe").is_dir())


if __name__ == "__main__":
    unittest.main()
