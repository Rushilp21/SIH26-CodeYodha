"""Pure policy helpers for conservative boundary-model fine-tuning."""

from __future__ import annotations

from collections import Counter


ROLE_MASS = {
    "positive_boundary": 0.55,
    "hard_negative": 0.30,
    "ordinary": 0.15,
}


def sampling_weights(
    groups: list[tuple[str, str]], feedback_fraction: float = 0.30,
) -> list[float]:
    """Return per-patch weights with bounded feedback and role proportions.

    ``groups`` entries are ``(source_group, patch_role)`` where source group is
    either ``reference`` or ``feedback``. Missing roles are renormalized within
    each source instead of fabricating samples.
    """
    if not groups:
        raise ValueError("At least one training patch is required")
    if not 0 <= feedback_fraction <= 1:
        raise ValueError("feedback_fraction must be between zero and one")
    invalid = [group for group in groups if group[0] not in {"reference", "feedback"} or group[1] not in ROLE_MASS]
    if invalid:
        raise ValueError(f"Unsupported sampling groups: {invalid[:3]}")

    counts = Counter(groups)
    present_sources = {source for source, _ in groups}
    requested_source_mass = {"reference": 1 - feedback_fraction, "feedback": feedback_fraction}
    source_total = sum(requested_source_mass[source] for source in present_sources)
    source_mass = {
        source: requested_source_mass[source] / source_total
        for source in present_sources
    }
    role_mass: dict[str, dict[str, float]] = {}
    for source in present_sources:
        present_roles = {role for item_source, role in groups if item_source == source}
        total = sum(ROLE_MASS[role] for role in present_roles)
        role_mass[source] = {role: ROLE_MASS[role] / total for role in present_roles}

    raw = [source_mass[source] * role_mass[source][role] / counts[(source, role)] for source, role in groups]
    scale = len(raw) / sum(raw)
    return [weight * scale for weight in raw]


def validation_gate(candidate: dict, baseline: dict) -> bool:
    """Use validation-only safeguards before an expensive checkpoint can win."""
    return bool(
        candidate["boundary_iou"] > baseline["boundary_iou"]
        and candidate["boundary_f1"] > baseline["boundary_f1"]
        and candidate["precision"] >= 0.98 * baseline["precision"]
        and candidate["false_positive_rate"] <= baseline["false_positive_rate"]
    )


def validation_score(metrics: dict) -> float:
    """Rank already-gated checkpoints without consulting the test or target AOI."""
    return (
        metrics["boundary_iou"]
        + 0.25 * metrics["boundary_f1"]
        + 0.10 * metrics["precision"]
        - 0.05 * metrics["false_positive_rate"]
    )


def chain_selection_gate(report: dict) -> bool:
    """Require the non-target pixel/polygon/topology chain gate."""
    return bool(report.get("baseline_comparison", {}).get("selection_eligible_without_target", False))
