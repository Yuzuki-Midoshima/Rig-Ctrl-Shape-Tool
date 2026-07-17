"""Transform value editing independent of widgets and Maya scene calls."""

from __future__ import annotations

from collections.abc import Callable

from ..domain import TransformValues
from ..state import ToolState


class ControlsFeature:
    """Update transform-control state independently from Qt widgets."""

    def __init__(self, state: ToolState) -> None:
        self._state = state
        self.changed: Callable[[], None] = lambda: None

    def current_values(self) -> TransformValues:
        return self._state.values

    def update(self, group: str, values: tuple[float, ...]) -> None:
        value = values[0] if group in ("uniform", "line_width") else values
        setattr(self._state.values, group, value)
        if group == "line_width":
            self._state.line_width_dirty = True
        self.changed()

    def reset(self, group: str) -> None:
        default = getattr(TransformValues(), group)
        setattr(self._state.values, group, default)
        if group == "line_width":
            self._state.line_width_dirty = True
        self.changed()

    def reset_axis(self, group: str, axis: int) -> None:
        """Reset one axis while preserving the other two values."""
        current = getattr(self._state.values, group)
        default = getattr(TransformValues(), group)
        if not isinstance(current, tuple) or not isinstance(default, tuple):
            raise ValueError(f"{group} does not contain axis values")
        values = list(current)
        values[axis] = default[axis]
        setattr(self._state.values, group, tuple(values))
        self.changed()

    def reset_all(self) -> None:
        self._state.reset_values()
        self.changed()
