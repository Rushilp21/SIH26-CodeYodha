"""Unit tests for conservative training and checkpoint-selection policy."""

import importlib.util
import sys
import unittest
from pathlib import Path


SEGMENTATION = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SEGMENTATION))
SCRIPT = SEGMENTATION / "training_policy.py"
SPEC = importlib.util.spec_from_file_location("training_policy", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class SamplingPolicyTests(unittest.TestCase):
    def test_feedback_mass_is_bounded_independently_of_patch_count(self):
        groups = (
            [("reference", "positive_boundary")] * 2
            + [("reference", "ordinary")] * 8
            + [("feedback", "positive_boundary")] * 30
            + [("feedback", "hard_negative")] * 70
        )
        weights = MODULE.sampling_weights(groups, feedback_fraction=0.30)
        feedback_mass = sum(weight for weight, group in zip(weights, groups) if group[0] == "feedback")
        self.assertAlmostEqual(feedback_mass / sum(weights), 0.30)

    def test_roles_are_balanced_within_each_source(self):
        groups = (
            [("reference", "positive_boundary")] * 4
            + [("reference", "hard_negative")] * 20
            + [("reference", "ordinary")] * 40
        )
        weights = MODULE.sampling_weights(groups)
        mass = {
            role: sum(weight for weight, group in zip(weights, groups) if group[1] == role)
            for role in MODULE.ROLE_MASS
        }
        total = sum(mass.values())
        for role, expected in MODULE.ROLE_MASS.items():
            self.assertAlmostEqual(mass[role] / total, expected)

    def test_single_available_source_and_role_are_supported(self):
        weights = MODULE.sampling_weights([("feedback", "hard_negative")] * 3)
        self.assertEqual(len(weights), 3)
        self.assertTrue(all(abs(weight - 1.0) < 1e-9 for weight in weights))


class SelectionPolicyTests(unittest.TestCase):
    BASELINE = {
        "boundary_iou": 0.10,
        "boundary_f1": 0.18,
        "precision": 0.30,
        "false_positive_rate": 0.02,
    }

    def test_validation_gate_requires_iou_f1_precision_and_fpr(self):
        candidate = dict(self.BASELINE, boundary_iou=0.11, boundary_f1=0.19, precision=0.31, false_positive_rate=0.019)
        self.assertTrue(MODULE.validation_gate(candidate, self.BASELINE))
        candidate["false_positive_rate"] = 0.021
        self.assertFalse(MODULE.validation_gate(candidate, self.BASELINE))
        candidate.update(false_positive_rate=0.019, precision=0.29)
        self.assertFalse(MODULE.validation_gate(candidate, self.BASELINE))

    def test_chain_gate_never_uses_target_only_success(self):
        report = {"baseline_comparison": {"selection_eligible_without_target": False, "final_promotion_eligible": True}}
        self.assertFalse(MODULE.chain_selection_gate(report))
        report["baseline_comparison"]["selection_eligible_without_target"] = True
        self.assertTrue(MODULE.chain_selection_gate(report))

    def test_score_rewards_overlap_and_precision_and_penalizes_fpr(self):
        better = dict(self.BASELINE, boundary_iou=0.12, precision=0.34, false_positive_rate=0.015)
        self.assertGreater(MODULE.validation_score(better), MODULE.validation_score(self.BASELINE))


if __name__ == "__main__":
    unittest.main()
