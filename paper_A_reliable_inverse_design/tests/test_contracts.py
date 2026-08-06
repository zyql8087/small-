import numpy as np
import unittest

from gc_graphformer.contracts import (
    CURVE_POINTS,
    decompose_curve,
    project_parameters,
    reconstruct_curve,
    validate_parameters,
)


class ContractTests(unittest.TestCase):
    def test_method_projection_enforces_m1_m2_m3(self):
        self.assertEqual(project_parameters("M1", [0.1, 0.12, 0.14, 7.0]).tolist(), [0.1, 0.12, 0.14, 0.0])
        self.assertEqual(project_parameters("M2", [0.1, 0.12, 0.14, 7.0]).tolist(), [0.12, 0.12, 0.12, 7.0])
        self.assertEqual(project_parameters("M3", [0.1, 0.12, 0.14, 7.0]).tolist(), [0.1, 0.12, 0.14, 7.0])

    def test_curve_decomposition_reconstructs_twenty_points(self):
        curve = np.linspace(1.0, 20.0, CURVE_POINTS)
        amplitude, shape = decompose_curve(curve)
        self.assertEqual(shape.shape, (CURVE_POINTS,))
        np.testing.assert_allclose(reconstruct_curve(amplitude, shape), curve)

    def test_parameter_validation_respects_method_constraints(self):
        validate_parameters("M1", [0.1, 0.12, 0.14, 0.0])
        validate_parameters("M2", [0.12, 0.12, 0.12, 7.0])
        validate_parameters("M3", [0.1, 0.12, 0.14, 7.0])
