"""Exact quarter-point subset selection used to hit an exam's barme-bandi total."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

UNITS_PER_POINT = 4  # Iranian exams score in exact 0.25-point increments


def to_units(points: object) -> int | None:
    """Convert ``points`` to quarter-point units; ``None`` if not an exact positive multiple."""
    if isinstance(points, bool) or not isinstance(points, (int, float)):
        return None
    scaled = float(points) * UNITS_PER_POINT
    units = round(scaled)
    if units <= 0 or abs(scaled - units) > 1e-6:
        return None
    return int(units)


def select_items_for_target_points(
    pool: Sequence[Mapping[str, Any]], target_points: float
) -> tuple[list[Any], float]:
    """0/1 subset-sum over quarter-point units.

    * Returns the earliest-ranked subset summing *exactly* to ``target_points``.
    * Otherwise returns the subset with the highest achievable total that does not
      exceed the target (never overshoots; never pads with arbitrary items).
    * Items whose points are not exact positive multiples of 0.25 are skipped
      rather than silently rounded.
    * Returns ``([], 0.0)`` when nothing fits or the target is not positive.
    """
    target_units = to_units(target_points)
    if target_units is None or not pool:
        return [], 0.0

    reachable: dict[int, tuple[int, ...]] = {0: ()}
    for idx, item in enumerate(pool):
        units = to_units(item.get("points"))
        if units is None or units > target_units:
            continue
        for current, chosen in list(reachable.items()):
            total = current + units
            if total <= target_units and total not in reachable:
                reachable[total] = (*chosen, idx)
        if target_units in reachable:
            break

    best = max(reachable)
    return [pool[i] for i in reachable[best]], round(best / UNITS_PER_POINT, 2)
