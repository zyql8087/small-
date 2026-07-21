import unittest

import numpy as np

from detect_curve_diversity import classify_curve


class CurveDiversityClassificationTests(unittest.TestCase):
    def test_monotone_negative_signed_displacement_is_not_snap_back(self):
        signed_disp = np.linspace(0.0, -1.0, 80)
        disp = np.abs(signed_disp)
        force = np.linspace(0.0, 10.0, 80)

        label, _ = classify_curve(disp, force, signed_disp)

        self.assertNotEqual(label, "snap_back")
        self.assertEqual(label, "monotone_hardening")

    def test_material_signed_displacement_reversal_is_snap_back(self):
        signed_disp = np.r_[np.linspace(0.0, 1.0, 40), np.linspace(1.0, 0.35, 40)]
        disp = np.abs(signed_disp)
        force = np.linspace(0.0, 10.0, 80)

        label, features = classify_curve(disp, force, signed_disp)

        self.assertEqual(label, "snap_back")
        self.assertTrue(features["snap_back"])


if __name__ == "__main__":
    unittest.main()
