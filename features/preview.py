"""Non-destructive real-time preview lifecycle."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

from ..core.state import ToolState
from ..services import MayaSceneService, SelectionService


class PreviewFeature:
    """Manage the non-destructive transform-preview edit session."""

    def __init__(self, state: ToolState, selection: SelectionService,
                 scene: MayaSceneService) -> None:
        self._state = state
        self._selection = selection
        self._scene = scene
        self.cancel_color: Callable[[], None] = lambda: None

    @property
    def is_enabled(self) -> bool:
        return self._state.preview.enabled

    @property
    def is_active(self) -> bool:
        return self._state.preview.lifecycle.is_active

    def begin(self) -> None:
        self.set_enabled(True)

    def update_preview(self) -> None:
        self._refresh()

    def commit(self) -> None:
        preview = self._state.preview
        if not self.is_active:
            return
        if preview.undo_open:
            self._scene.close_undo()
        preview.lifecycle.commit()
        preview.enabled = False
        preview.clear()

    def rollback(self, keep_enabled: bool = False) -> None:
        """Restore the preview baseline, optionally preserving checkbox state."""
        self._cancel(keep_enabled=keep_enabled)

    def undo_uncommitted(self) -> bool:
        """Undo one input edit while keeping the preview session active."""
        preview = self._state.preview
        if not self.is_active:
            return False
        if preview.value_undo_stack:
            preview.value_redo_stack.append(replace(self._state.values))
            self._state.values = preview.value_undo_stack.pop()
        self._mark_display_values_dirty()
        self._refresh()
        return True

    def redo_uncommitted(self) -> bool:
        """Redo one input edit while keeping the preview session active."""
        preview = self._state.preview
        if not self.is_active or not preview.value_redo_stack:
            return False
        preview.value_undo_stack.append(replace(self._state.values))
        self._state.values = preview.value_redo_stack.pop()
        self._mark_display_values_dirty()
        self._refresh()
        return True

    def _mark_display_values_dirty(self) -> None:
        self._state.line_width_dirty = True
        if hasattr(self._state, "joint_size_dirty"):
            self._state.joint_size_dirty = True

    def set_enabled(self, enabled: bool) -> None:
        self._state.preview.enabled = enabled
        if enabled:
            self.cancel_color()
            self._refresh()
        else:
            self._cancel()

    def _start(self, cvs: list[str]) -> bool:
        if not cvs:
            return False
        try:
            self._state.preview.input_values = replace(self._state.values)
            self._state.preview.positions = {
                cv: self._scene.cv_position(cv) for cv in cvs
            }
            self._state.preview.line_widths = {
                shape: width for shape in self._selection.shapes()
                if (width := self._scene.line_width(shape)) is not None
            }
            self._state.preview.lifecycle.begin()
            self._scene.open_undo("RigCtrlShapePreview")
            self._state.preview.undo_open = True
            return True
        except (RuntimeError, ValueError) as error:
            preview = self._state.preview
            if preview.undo_open:
                self._scene.close_undo()
            if preview.lifecycle.is_active:
                preview.lifecycle.rollback()
            self._state.preview.clear()
            self._scene.warning("Could not start Preview", error)
            return False

    def _restore(self) -> None:
        for cv, position in self._state.preview.positions.items():
            if self._scene.exists(cv):
                self._scene.set_cv_position(cv, position)
        for shape, width in self._state.preview.line_widths.items():
            self._scene.set_line_width(shape, width)

    def _refresh(self) -> None:
        if not self._state.preview.enabled:
            return
        cvs = self._selection.cvs()
        if set(cvs) != set(self._state.preview.positions):
            value_undo_stack = list(self._state.preview.value_undo_stack)
            value_redo_stack = list(self._state.preview.value_redo_stack)
            self._cancel(keep_enabled=True)
            self._state.preview.value_undo_stack = value_undo_stack
            self._state.preview.value_redo_stack = value_redo_stack
            if not self._start(cvs):
                return
        try:
            self._restore()
            self._apply_current_values()
        except RuntimeError as error:
            self._cancel()
            self._scene.warning("Could not update Preview", error)

    def _apply_current_values(self) -> None:
        for controller in self._selection.controllers():
            cvs = self._selection.controller_cvs(controller)
            self._scene.transform_cvs(cvs, self._state.values)
        if self._state.line_width_dirty:
            for shape in self._selection.shapes():
                self._scene.set_line_width(shape, self._state.values.line_width)

    def _cancel(self, keep_enabled: bool = False) -> None:
        try:
            if self._state.preview.positions:
                self._restore()
        except RuntimeError as error:
            self._scene.warning(
                "Some shapes could not be restored during Preview cancellation", error
            )
        finally:
            preview = self._state.preview
            if preview.undo_open:
                self._scene.close_undo()
            if preview.lifecycle.is_active:
                preview.lifecycle.rollback()
            preview.clear()
            if not keep_enabled:
                preview.enabled = False
