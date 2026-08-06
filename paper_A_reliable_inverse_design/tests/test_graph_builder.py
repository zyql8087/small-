import unittest

import numpy as np
import torch
from torch_geometric.data import Batch

from gc_graphformer.contracts import (
    DESCRIPTOR_COUNT,
    PARAMETER_COUNT,
    profile_id,
)
from gc_graphformer.graph_builder import (
    EDGE_TYPE_AXIAL,
    EDGE_TYPE_COMPILER,
    EDGE_TYPE_METHOD,
    EDGE_TYPE_READOUT,
    NODE_INDEX,
    build_graph,
)


def make_graph(method="M3", profile="physical_m04"):
    parameters = {
        "M1": [0.08, 0.12, 0.16, 7.0],
        "M2": [0.08, 0.12, 0.16, 7.0],
        "M3": [0.08, 0.12, 0.16, 7.0],
    }[method]
    descriptors = np.linspace(0.1, 0.5, DESCRIPTOR_COUNT)
    sensitivities = np.arange(PARAMETER_COUNT * DESCRIPTOR_COUNT, dtype=np.float32).reshape(
        PARAMETER_COUNT, DESCRIPTOR_COUNT
    )
    return build_graph(
        method=method,
        parameters=parameters,
        descriptors=descriptors,
        sensitivities=sensitivities,
        descriptor_profile=profile,
        y_curve=np.linspace(1.0, 20.0, 20),
        base_structure_id=11,
    )


class GraphBuilderTests(unittest.TestCase):
    def test_graph_has_fixed_nodes_and_typed_semantics(self):
        graph = make_graph()
        self.assertEqual(graph.num_nodes, 11)
        self.assertEqual(graph.node_type.tolist(), list(range(11)))
        self.assertEqual(graph.x.shape, (11, 7))
        self.assertEqual(graph.method_id.item(), 2)
        self.assertEqual(graph.descriptor_profile_id.item(), profile_id("physical_m04"))

    def test_edge_families_have_approved_counts_and_directions(self):
        expected_counts = {"M1": 33, "M2": 28, "M3": 38}
        for method, expected in expected_counts.items():
            graph = make_graph(method)
            self.assertEqual(graph.edge_index.shape, (2, expected))
            edge_pairs = set(map(tuple, graph.edge_index.t().tolist()))
            axial_pairs = {(1, 2), (2, 1), (2, 3), (3, 2)}
            self.assertTrue(axial_pairs.issubset(edge_pairs))
            for source, target in graph.edge_index[:, graph.edge_type == EDGE_TYPE_COMPILER].t().tolist():
                self.assertIn(source, {1, 2, 3, 4})
                self.assertIn(target, {5, 6, 7, 8, 9})
            active = {1, 2, 3} if method == "M1" else ({1, 4} if method == "M2" else {1, 2, 3, 4})
            compiler_sources = set(
                graph.edge_index[0, graph.edge_type == EDGE_TYPE_COMPILER].tolist()
            )
            self.assertEqual(compiler_sources, active)
            for source, target in graph.edge_index[:, graph.edge_type == EDGE_TYPE_METHOD].t().tolist():
                self.assertEqual(source, NODE_INDEX["method"])
                self.assertIn(target, {1, 2, 3, 4})
            for source, target in graph.edge_index[:, graph.edge_type == EDGE_TYPE_READOUT].t().tolist():
                self.assertIn(source, range(10))
                self.assertEqual(target, NODE_INDEX["readout"])

    def test_compiler_edge_attributes_encode_continuous_sensitivity(self):
        graph = make_graph()
        compiler_mask = graph.edge_type == EDGE_TYPE_COMPILER
        pairs = graph.edge_index[:, compiler_mask].t().tolist()
        index = pairs.index([1, 5])
        actual = graph.edge_attr[compiler_mask][index]
        expected = torch.tensor([0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 0.0, 0.0])
        torch.testing.assert_close(actual, expected)
        self.assertTrue(torch.isfinite(graph.edge_attr).all())

    def test_method_constraints_and_profile_separation_are_explicit(self):
        m1 = make_graph("M1", "legacy_small")
        m2 = make_graph("M2", "physical_m04")
        np.testing.assert_allclose(m1.parameters.numpy(), [0.08, 0.12, 0.16, 0.0])
        np.testing.assert_allclose(m2.parameters.numpy(), [0.12, 0.12, 0.12, 7.0])
        self.assertEqual(m1.parameter_active_mask.tolist(), [True, True, True, False])
        self.assertEqual(m2.parameter_active_mask.tolist(), [True, False, False, True])
        self.assertNotEqual(m1.descriptor_profile_id.item(), m2.descriptor_profile_id.item())

    def test_batch_has_no_cross_graph_edges_and_build_is_deterministic(self):
        left = make_graph("M3")
        right = make_graph("M1")
        repeated = make_graph("M3")
        self.assertTrue(torch.equal(left.edge_index, repeated.edge_index))
        self.assertTrue(torch.equal(left.edge_attr, repeated.edge_attr))
        batch = Batch.from_data_list([left, right])
        self.assertEqual(batch.num_graphs, 2)
        for source, target in batch.edge_index.t().tolist():
            self.assertEqual(batch.batch[source].item(), batch.batch[target].item())
        self.assertTrue(torch.equal(batch.edge_index[:, batch.edge_index[0] < 11], left.edge_index))


if __name__ == "__main__":
    unittest.main()
