import unittest

import torch

from gc_graphformer.baselines import (
    DenseAllOnesGATBaseline,
    ParameterTokenTransformerBaseline,
    ResMLPBaseline,
)


class BaselineTests(unittest.TestCase):
    def test_retained_mlp_baseline_outputs_twenty_curve_points(self):
        model = ResMLPBaseline(input_dim=9, hidden_dim=32)
        self.assertEqual(model(torch.rand(2, 9)).shape, (2, 20))

    def test_retained_parameter_token_transformer_outputs_twenty_curve_points(self):
        model = ParameterTokenTransformerBaseline(hidden_dim=32, heads=4, num_layers=1)
        self.assertEqual(model(torch.rand(2, 9)).shape, (2, 20))

    def test_dense_all_ones_gat_is_marked_as_baseline(self):
        model = DenseAllOnesGATBaseline(hidden_dim=32, heads=4)
        self.assertEqual(model(torch.rand(2, 9)).shape, (2, 20))
        self.assertEqual(model.graph_semantics, "dense_all_ones_baseline")


if __name__ == "__main__":
    unittest.main()

