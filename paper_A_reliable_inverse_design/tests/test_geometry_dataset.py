import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from gc_graphformer.compiler import SyntheticM04Compiler
from gc_graphformer.geometry_dataset import (
    GeometryOnlyGenerator,
    load_dataset,
    write_dataset,
)


class GeometryDatasetTests(unittest.TestCase):
    def test_smoke_compiler_is_explicitly_nonmechanical_and_profile_bound(self):
        compiler = SyntheticM04Compiler(profile="physical_m04")
        result = compiler.compile("M3", [0.08, 0.12, 0.16, 5.0], sample_index=0)
        self.assertEqual(result.descriptor_profile, "physical_m04")
        self.assertEqual(result.compiler_mode, "synthetic_smoke")
        self.assertFalse(result.abaqus_executed)
        self.assertFalse(result.solver_ready)
        self.assertTrue(np.isfinite(result.descriptors).all())

    def test_same_seed_produces_byte_identical_manifest_and_records(self):
        compiler = SyntheticM04Compiler(profile="physical_m04")
        first = GeometryOnlyGenerator(compiler, seed=17, profile="physical_m04").generate(6)
        second = GeometryOnlyGenerator(compiler, seed=17, profile="physical_m04").generate(6)
        self.assertEqual(first, second)
        with tempfile.TemporaryDirectory() as temp:
            left = Path(temp) / "left"
            right = Path(temp) / "right"
            write_dataset(left, first, seed=17, profile="physical_m04", shard_size=3)
            write_dataset(right, second, seed=17, profile="physical_m04", shard_size=3)
            self.assertEqual(
                (left / "manifest.json").read_bytes(),
                (right / "manifest.json").read_bytes(),
            )
            self.assertEqual(load_dataset(left), load_dataset(right))

    def test_shards_are_recoverable_and_profile_mixing_is_rejected(self):
        compiler = SyntheticM04Compiler(profile="physical_m04")
        records = GeometryOnlyGenerator(compiler, seed=3, profile="physical_m04").generate(5)
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "dataset"
            manifest = write_dataset(output, records, seed=3, profile="physical_m04", shard_size=2)
            self.assertEqual(manifest["record_count"], 5)
            self.assertEqual(len(manifest["shards"]), 3)
            loaded = load_dataset(output)
            self.assertEqual(len(loaded), 5)
            self.assertTrue(all(record["descriptor_profile"] == "physical_m04" for record in loaded))
            self.assertTrue(all(len(record["record_sha256"]) == 64 for record in loaded))

        mixed = list(records)
        mixed[0] = dict(mixed[0], descriptor_profile="legacy_small")
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):
                write_dataset(Path(temp) / "mixed", mixed, seed=3, profile="physical_m04", shard_size=2)

    def test_manifest_provenance_has_no_mechanics_or_abaqus_claim(self):
        compiler = SyntheticM04Compiler(profile="physical_m04")
        records = GeometryOnlyGenerator(compiler, seed=5, profile="physical_m04").generate(2)
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "dataset"
            write_dataset(output, records, seed=5, profile="physical_m04", shard_size=2)
            manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["dataset_role"], "original_auxiliary_geometry_dataset")
            self.assertFalse(manifest["mechanical_labels"])
            self.assertFalse(manifest["abaqus_executed"])
            self.assertEqual(manifest["compiler_mode"], "synthetic_smoke")


if __name__ == "__main__":
    unittest.main()

