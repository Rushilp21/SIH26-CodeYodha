"""Pure contract tests for reviewed-feedback preparation; no raster downloads or training."""

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "build_reviewed_dataset.py"
SPEC = importlib.util.spec_from_file_location("build_reviewed_dataset", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class ReviewedDatasetContracts(unittest.TestCase):
    def test_accepts_explicit_positive_and_negative_labels(self):
        document = {
            "schema_version": "bhumisetu.review-labels.v1",
            "type": "FeatureCollection",
            "summary": {"training_ready": False},
            "features": [
                {"properties": {"parcel_id": "a", "training_role": "positive_boundary"}},
                {"properties": {"parcel_id": "b", "training_role": "hard_negative", "false_positive_class": "canal"}},
            ],
        }
        self.assertEqual(MODULE.validate_review_export(document), {"training_ready": False})

    def test_rejects_duplicate_or_untyped_feedback(self):
        duplicate = {
            "schema_version": "bhumisetu.review-labels.v1",
            "type": "FeatureCollection",
            "features": [
                {"properties": {"parcel_id": "a", "training_role": "positive_boundary"}},
                {"properties": {"parcel_id": "a", "training_role": "hard_negative", "false_positive_class": "road"}},
            ],
        }
        with self.assertRaises(ValueError):
            MODULE.validate_review_export(duplicate)

    def test_base_validation_and_test_must_exclude_target_aoi(self):
        records = [
            {"name": "train", "split": "train"},
            {"name": "validation", "split": "validation"},
            {"name": "test", "split": "test"},
        ]
        safe = {"records": records, "target_aoi_used_for_training_or_selection": False}
        self.assertEqual(MODULE.validate_base_manifest(safe), {"train": 1, "validation": 1, "test": 1})
        unsafe = {"records": records, "target_aoi_used_for_parameter_selection": True, "target_aoi_used_for_test": False}
        with self.assertRaises(ValueError):
            MODULE.validate_base_manifest(unsafe)

    def test_require_ready_fails_closed_with_report_location(self):
        report_path = Path("/tmp/reviewed/pretraining_report.json")
        with self.assertRaisesRegex(RuntimeError, "pretraining_report.json"):
            MODULE.require_dataset_ready(
                {"dataset_ready": False, "blocking_issue": "Matched labels are insufficient."},
                report_path,
            )
        MODULE.require_dataset_ready({"dataset_ready": True}, report_path)


if __name__ == "__main__":
    unittest.main()
