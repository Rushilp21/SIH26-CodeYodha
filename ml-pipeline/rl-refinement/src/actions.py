"""Discrete vertex micro-movements (initial action space).

Encoding
--------
action = vertex_index * 4 + direction

direction:
  0 = +Y (north in projected metres)
  1 = +X (east)
  2 = -Y (south)
  3 = -X (west)

Nudge length: `step_m` metres in PROCESSING_CRS (default 0.5 m).

Future actions (not in this Discrete space yet):
  insert vertex, delete vertex, snap to detected edge.
"""

from __future__ import annotations

DIRECTIONS = {
    0: (0.0, 1.0),
    1: (1.0, 0.0),
    2: (0.0, -1.0),
    3: (-1.0, 0.0),
}


def decode_action(action: int, n_vertices: int) -> tuple[int, int]:
    vertex = int(action) // 4
    direction = int(action) % 4
    if vertex < 0 or vertex >= n_vertices:
        raise ValueError(f"vertex {vertex} out of range for {n_vertices} vertices")
    return vertex, direction


def action_space_n(n_vertices: int) -> int:
    return n_vertices * 4
