"""Contract tests for the read-only preflight gate."""

import importlib.util
import sys
import unittest
from pathlib import Path


SEGMENTATION = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SEGMENTATION))
SCRIPT = SEGMENTATION / "check_training_readiness.py"
SPEC = importlib.util.spec_from_file_location("check_training_readiness", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def records():
    return [
        {"name": f"train_{index}", "split": "train"} for index in range(9)
    ] + [
        {"name": f"validation_{index}", "split": "validation"} for index in range(3)
    ] + [
        {"name": f"test_{index}", "split": "test"} for index in range(3)
    ]


class TrainingReadinessContracts(unittest.TestCase):
    def test_accepts_disjoint_independent_split_contract(self):
        blockers, warnings = MODULE.manifest_contract({
            "records": records(),
            "target_aoi_used_for_training_or_selection": False,
        })
        self.assertEqual(blockers, [])
        self.assertTrue(any("No human-reviewed" in warning for warning in warnings))

    def test_rejects_target_aoi_selection_and_short_splits(self):
        blockers, _ = MODULE.manifest_contract({
            "records": [{"name": "train", "split": "train"}],
            "target_aoi_used_for_parameter_selection": True,
            "target_aoi_used_for_test": False,
        })
        self.assertTrue(any("validation needs" in item for item in blockers))
        self.assertTrue(any("parameter selection" in item for item in blockers))

    def test_rejects_feedback_outside_training(self):
        manifest_records = records()
        manifest_records[9]["source"] = "human_review_feedback"
        blockers, _ = MODULE.manifest_contract({
            "records": manifest_records,
            "target_aoi_used_for_training_or_selection": False,
        })
        self.assertTrue(any("outside the training split" in item for item in blockers))

    def test_human_feedback_is_not_ready_from_presence_alone(self):
        manifest_records = records()
        manifest_records[0]["source"] = "human_review_feedback"
        manifest = {
            "records": manifest_records,
            "review_summary": {"training_ready": False},
            "target_aoi_used_for_training_or_selection": False,
        }
        blockers, _ = MODULE.manifest_contract(manifest)
        self.assertEqual(blockers, [])
        self.assertFalse(MODULE.reviewed_feedback_ready(manifest))
        manifest["review_summary"]["training_ready"] = True
        self.assertTrue(MODULE.reviewed_feedback_ready(manifest))
        manifest["matched_review_summary"] = {"training_ready": False}
        self.assertFalse(MODULE.reviewed_feedback_ready(manifest))

    def test_allows_explicit_negative_only_feedback_windows(self):
        negative = {
            "source": "human_review_feedback",
            "hard_negative_count": 3,
        }
        self.assertTrue(MODULE.valid_boundary_coverage(negative, 0, 1200))
        self.assertFalse(MODULE.valid_boundary_coverage(negative, 0, 0))
        self.assertFalse(MODULE.valid_boundary_coverage({"split": "train"}, 0, 1200))


if __name__ == "__main__":
    unittest.main()
