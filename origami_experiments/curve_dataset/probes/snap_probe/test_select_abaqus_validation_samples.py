import unittest

import pandas as pd

from select_abaqus_validation_samples import pick


class AbaqusValidationSelectionTests(unittest.TestCase):
    def test_pick_uses_only_samples_with_probe_labels_and_fills_requested_count(self):
        params = pd.DataFrame(
            {
                "sample_id": [f"miura_{i:05d}" for i in range(1, 13)],
                "pattern": [1] * 12,
                "m": [6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 99, 100],
                "n": [4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 99, 100],
                "tcrease": [0.001 + i * 1e-5 for i in range(12)],
                "tpanel": [0.002 + i * 1e-5 for i in range(12)],
                "W": [0.003 + i * 1e-5 for i in range(12)],
                "creaseE": [1e9 + i for i in range(12)],
                "panelE": [2e9 + i for i in range(12)],
            }
        )
        per_curve = pd.DataFrame(
            {
                "sample_id": [f"miura_{i:05d}" for i in range(1, 11)],
                "curve_id": [0] * 10,
                "label": ["snap_back"] + ["monotone_hardening"] * 9,
            }
        )

        selected = pick(params, per_curve, n_samples=10)

        self.assertEqual(len(selected), 10)
        self.assertEqual(set(selected["sample_id"]), set(per_curve["sample_id"]))
        self.assertNotIn("miura_00011", set(selected["sample_id"]))
        self.assertNotIn("miura_00012", set(selected["sample_id"]))


if __name__ == "__main__":
    unittest.main()
