import unittest

import numpy as np
import torch
from torch_geometric.data import Batch

from gc_graphformer.graph_builder import build_graph
from gc_graphformer.model import FullyConnectedPyGGraphTransformer, GCGraphFormer


def make_batch(count=2):
    graphs = []
    for index in range(count):
        graphs.append(
            build_graph(
                method="M3" if index % 2 == 0 else "M1",
                parameters=[0.08 + 0.01 * index, 0.12, 0.16, 5.0],
                descriptors=np.linspace(0.1, 0.5, 5),
                sensitivities=np.full((4, 5), 0.1 + index, dtype=np.float32),
                descriptor_profile="physical_m04",
            )
        )
    return Batch.from_data_list(graphs)


class GCGraphFormerTests(unittest.TestCase):
    def test_output_shape_and_amplitude_shape_reconstruction(self):
        torch.manual_seed(5)
        model = GCGraphFormer(hidden_dim=32, heads=4, num_layers=2, dropout=0.0)
        model.eval()
        output = model(make_batch(), return_aux=True)
        self.assertEqual(output["curve"].shape, (2, 20))
        self.assertEqual(output["amplitude"].shape, (2,))
        self.assertEqual(output["shape"].shape, (2, 20))
        self.assertTrue(torch.isfinite(output["curve"]).all())
        self.assertTrue((output["shape"] >= 0.0).all())
        torch.testing.assert_close(output["curve"], output["amplitude"][:, None] * output["shape"])

    def test_node_and_edge_inputs_receive_gradients(self):
        torch.manual_seed(9)
        batch = make_batch()
        batch.x.requires_grad_()
        batch.edge_attr.requires_grad_()
        model = GCGraphFormer(hidden_dim=32, heads=4, num_layers=1, dropout=0.0)
        model(batch).sum().backward()
        self.assertIsNotNone(batch.x.grad)
        self.assertIsNotNone(batch.edge_attr.grad)
        self.assertTrue(torch.isfinite(batch.x.grad).all())
        self.assertTrue(torch.isfinite(batch.edge_attr.grad).all())

    def test_eval_is_deterministic_for_identical_initialization(self):
        torch.manual_seed(12)
        first = GCGraphFormer(hidden_dim=32, heads=4, num_layers=1, dropout=0.0)
        torch.manual_seed(12)
        second = GCGraphFormer(hidden_dim=32, heads=4, num_layers=1, dropout=0.0)
        first.eval()
        second.eval()
        batch = make_batch()
        torch.testing.assert_close(first(batch), second(batch))

    def test_one_step_smoke_overfits_a_repeated_curve(self):
        torch.manual_seed(19)
        model = GCGraphFormer(hidden_dim=16, heads=4, num_layers=1, dropout=0.0)
        optimizer = torch.optim.Adam(model.parameters(), lr=0.02)
        batch = make_batch(1)
        target = torch.full((1, 20), 2.0)
        before = torch.nn.functional.mse_loss(model(batch), target)
        for _ in range(30):
            optimizer.zero_grad()
            loss = torch.nn.functional.mse_loss(model(batch), target)
            loss.backward()
            optimizer.step()
        after = torch.nn.functional.mse_loss(model(batch), target)
        self.assertLess(after.item(), before.item())

    def test_fully_connected_pyg_graph_transformer_is_an_explicit_ablation(self):
        torch.manual_seed(23)
        model = FullyConnectedPyGGraphTransformer(hidden_dim=32, heads=4, num_layers=1, dropout=0.0)
        output = model(make_batch())
        self.assertEqual(output.shape, (2, 20))
        self.assertEqual(model.edge_policy, "fully_connected_all_ones")


if __name__ == "__main__":
    unittest.main()

