import unittest

import torch

from gc_graphformer.diffusion_interface import MethodConditionedDiffusionInterface


class DiffusionInterfaceTests(unittest.TestCase):
    def test_condition_contains_curve_descriptors_method_token_and_mask(self):
        interface = MethodConditionedDiffusionInterface(response_descriptor_dim=4)
        condition = interface.build_condition(
            "M2",
            target_curve=torch.ones(20),
            response_descriptors=torch.tensor([1.0, 2.0, 3.0, 4.0]),
        )
        self.assertEqual(condition["target_curve"].shape, (1, 20))
        self.assertEqual(condition["response_descriptors"].shape, (1, 4))
        self.assertEqual(condition["method_token"].tolist(), [[0.0, 1.0, 0.0]])
        self.assertEqual(condition["variable_validity_mask"].tolist(), [[True, False, False, True]])

    def test_training_and_decode_projection_share_padded_output_contract(self):
        interface = MethodConditionedDiffusionInterface()
        raw = torch.tensor(
            [[0.1, 0.12, 0.14, 7.0], [0.1, 0.12, 0.14, 7.0], [0.1, 0.12, 0.14, 7.0]],
            requires_grad=True,
        )
        methods = ["M1", "M2", "M3"]
        training = interface.project_training_output(raw, methods)
        decoded = interface.decode_output(raw.detach(), methods)
        self.assertEqual(training.shape, (3, 4))
        torch.testing.assert_close(training.detach(), decoded)
        self.assertEqual(training[0, 3].item(), 0.0)
        torch.testing.assert_close(training[1, :3], torch.full((3,), 0.12))
        torch.testing.assert_close(training[2], raw.detach()[2])
        training.sum().backward()
        self.assertTrue(torch.isfinite(raw.grad).all())

    def test_decoder_bounds_width_to_open_interval(self):
        interface = MethodConditionedDiffusionInterface()
        raw = torch.tensor([[0.01, 0.21, 0.1, 2.0], [0.1, 0.1, 0.1, 8.0]])
        projected = interface.decode_output(raw, ["M2", "M3"])
        self.assertTrue(interface.validate_padded_parameters(projected, ["M2", "M3"]).all())
        self.assertGreater(projected[:, 3].min().item(), 2.0)
        self.assertLess(projected[:, 3].max().item(), 8.0)
        self.assertTrue((projected[:, :3] >= 0.03).all())
        self.assertTrue((projected[:, :3] <= 0.20).all())


if __name__ == "__main__":
    unittest.main()

