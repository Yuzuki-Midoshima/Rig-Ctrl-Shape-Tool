"""Transform value editing independent of widgets and Maya scene calls."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

from ..core.domain import TransformValues
from ..core.state import ToolState


class ControlsFeature:
    """Update transform-control state independently from Qt widgets."""

    def __init__(self, state: ToolState) -> None:
        self._state = state
        self.changed: Callable[[], None] = lambda: None
        self._preview_edit_active = False
        self._preview_value_recorded = False

    def current_values(self) -> TransformValues:
        return self._state.values

    def update(self, group: str, values: tuple[float, ...]) -> None:
        self._record_preview_value()
        value = values[0] if group in ("uniform", "line_width") else values
        setattr(self._state.values, group, value)
        if group == "line_width":
            self._state.line_width_dirty = True
        self.changed()

    def reset(self, group: str) -> None:
        self._record_preview_value()
        default = getattr(TransformValues(), group)
        setattr(self._state.values, group, default)
        if group == "line_width":
            self._state.line_width_dirty = True
        self.changed()

    def reset_axis(self, group: str, axis: int) -> None:
        """Reset one axis while preserving the other two values."""
        self._record_preview_value()
        current = getattr(self._state.values, group)
        default = getattr(TransformValues(), group)
        if not isinstance(current, tuple) or not isinstance(default, tuple):
            raise ValueError(f"{group} does not contain axis values")
        values = list(current)
        values[axis] = default[axis]
        setattr(self._state.values, group, tuple(values))
        self.changed()

    def reset_all(self) -> None:
        self._record_preview_value()
        self._state.reset_values()
        self.changed()

    def _record_preview_value(self) -> None:
        preview = self._state.preview
        if self._preview_edit_active and self._preview_value_recorded:
            return
        preview.value_undo_stack.append(replace(self._state.values))
        preview.value_redo_stack.clear()
        self._preview_value_recorded = True

    def begin_preview_edit(self) -> None:
        """Group continuous slider updates into one Preview undo step."""
        self._preview_edit_active = True
        self._preview_value_recorded = False

    def end_preview_edit(self) -> None:
        self._preview_edit_active = False
        self._preview_value_recorded = False

    def record_apply(self) -> None:
        """Pair Maya's next transform Undo with the current control values."""
        before = replace(self._state.committed_values)
        after = replace(self._state.values)
        self._state.value_undo_stack.append((before, after))
        self._state.value_redo_stack.clear()
        self._state.committed_values = replace(after)

        self._state.preview.value_undo_stack.clear()
        self._state.preview.value_redo_stack.clear()

    def restore_undo_values(self) -> bool:
        """Restore the inputs associated with a completed Maya Undo."""
        if not self._state.value_undo_stack:
            return False
        before, after = self._state.value_undo_stack.pop()
        self._state.value_redo_stack.append((before, after))
        self._state.values = replace(before)
        self._state.committed_values = replace(before)
        self._clear_dirty_flags()
        return True

    def restore_redo_values(self) -> bool:
        """Restore the inputs associated with a completed Maya Redo."""
        if not self._state.value_redo_stack:
            return False
        before, after = self._state.value_redo_stack.pop()
        self._state.value_undo_stack.append((before, after))
        self._state.values = replace(after)
        self._state.committed_values = replace(after)
        self._clear_dirty_flags()
        return True

    def _clear_dirty_flags(self) -> None:
        self._state.line_width_dirty = False
        if hasattr(self._state, "joint_size_dirty"):
            self._state.joint_size_dirty = False
