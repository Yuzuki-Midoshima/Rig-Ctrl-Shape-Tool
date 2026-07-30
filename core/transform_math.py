"""Pure use-case calculations that are testable without Maya."""

from __future__ import annotations

from .domain import TransformValues


def isolated_transform_values(
    current: TransformValues, group: str, axis: int = 0
) -> TransformValues:
    """Return neutral values except for one context-menu field."""
    isolated = TransformValues()
    if group in ("uniform", "line_width", "joint_size"):
        setattr(isolated, group, getattr(current, group))
        return isolated
    if group not in ("scale", "rotate", "move"):
        raise ValueError(f"Unknown transform group: {group}")
    values = list(getattr(isolated, group))
    values[axis] = getattr(current, group)[axis]
    setattr(isolated, group, tuple(values))
    return isolated
