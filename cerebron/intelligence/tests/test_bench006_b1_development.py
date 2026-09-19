import unittest

import bench006_b1_development as b1


class Bench006B1Tests(unittest.TestCase):
    def test_private_and_unknown_fields_rejected(self):
        for field in sorted(b1.PRIVATE_FIELDS | {"unexpected"}):
            with self.subTest(field=field), self.assertRaises(ValueError):
                b1.public_request({field: "canary"})

    def test_splits_are_disjoint(self):
        fit, validation, query, _ = b1.dataset(6101, "affine_gf2")
        sets = [{(s, a) for s, a, _ in part} for part in (fit, validation, query)]
        self.assertFalse(sets[0] & sets[1])
        self.assertFalse(sets[0] & sets[2])
        self.assertFalse(sets[1] & sets[2])

    def test_active_recovers_development_systems(self):
        result = b1.run_development()
        self.assertLess(result["summary"]["active"]["mean_bit_error"], 0.01)
        self.assertLess(result["summary"]["active"]["mean_bit_error"], result["summary"]["baseline"]["mean_bit_error"])
        self.assertLess(result["summary"]["active"]["mean_bit_error"], result["summary"]["sham"]["mean_bit_error"])

    def test_ablation_recomputation_is_charged(self):
        result = b1.run_development()
        self.assertGreater(result["summary"]["ablation"]["mean_operations"], result["summary"]["baseline"]["mean_operations"])

    def test_private_changes_cannot_change_public_prediction(self):
        fit, validation, query, _ = b1.dataset(6102, "local_xor_ring")
        first, _ = b1.evaluate_condition("active", fit, validation, query, 6102)
        second, _ = b1.evaluate_condition("active", fit, validation, query, 6102)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
