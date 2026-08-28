from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RewardBreakdown:
    iou: float = 0.0
    edge_alignment: float = 0.0
    regularity: float = 0.0
    topology: float = 0.0
    baseline_deviation: float = 0.0
    total: float = 0.0


def compose_reward(
    iou_reward: float,
    edge_alignment_reward: float,
    geometry_regularization_penalty: float,
    topology_violation_penalty: float,
    baseline_deviation_penalty: float,
) -> RewardBreakdown:
    total = (
        iou_reward
        + edge_alignment_reward
        - geometry_regularization_penalty
        - topology_violation_penalty
        - baseline_deviation_penalty
    )
    return RewardBreakdown(
        iou=iou_reward,
        edge_alignment=edge_alignment_reward,
        regularity=-geometry_regularization_penalty,
        topology=-topology_violation_penalty,
        baseline_deviation=-baseline_deviation_penalty,
        total=total,
    )
