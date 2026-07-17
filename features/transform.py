"""Committed controller-CV transform operations."""

from __future__ import annotations

from collections.abc import Callable, Sequence

from ..domain import TransformValues
from ..errors import InvalidSelectionError
from ..logic import isolated_transform_values
from ..services import MayaSceneService, SelectionService
from ..state import ToolState


class TransformFeature:
    """Commit controller CV transforms and line-width changes."""

    def __init__(self, state: ToolState, selection: SelectionService, scene: MayaSceneService) -> None:
        self._state = state
        self._selection = selection
        self._scene = scene
        self.cancel_preview: Callable[[], None] = lambda: None
        self.cancel_color: Callable[[], None] = lambda: None
        self.has_active_preview: Callable[[], bool] = lambda: False
        self.commit_preview: Callable[[], None] = lambda: None

    def _transform_cvs(self, cvs: Sequence[str], values: TransformValues | None = None) -> None:
        """Transform one controller's CVs around its shape center.

        Maya's implicit component pivot can be the center of the complete CV
        selection.  A controller transform's origin can also be far away from
        its visible shape.  Processing each controller independently with its
        object center keeps the visible shape stationary while scaling.
        """
        if not cvs:
            return
        self._scene.transform_cvs(cvs, values or self._state.values)

    def _transform_selection(self, values: TransformValues | None = None) -> None:
        """Transform each selected controller independently."""
        for controller in self._selection.controllers():
            self._transform_cvs(self._selection.controller_cvs(controller), values)

    def apply_value(self, group: str, axis: int = 0) -> None:
        """Commit only one context-menu value, leaving every other value unapplied."""
        self.cancel_color()
        self.cancel_preview()
        cvs = self._selection.cvs()
        if not cvs:
            raise InvalidSelectionError("Select a controller with a NURBS curve shape")

        isolated = isolated_transform_values(self._state.values, group, axis)

        with self._scene.undo_chunk("RigCtrlShapeApplyValue"):
            if group == "line_width":
                for shape in self._selection.shapes():
                    self._scene.set_line_width(shape, isolated.line_width)
            else:
                self._transform_selection(isolated)

    def _apply_line_width(self, shapes: Sequence[str]) -> None:
        if not self._state.line_width_dirty:
            return
        for shape in shapes:
            try:
                self._scene.set_line_width(shape, self._state.values.line_width)
            except RuntimeError:
                continue

    def apply(self) -> None:
        self.cancel_color()
        if self.has_active_preview():
            self.commit_preview()
            self._state.line_width_dirty = False
            return
        cvs = self._selection.cvs()
        if not cvs:
            raise InvalidSelectionError("Select a controller with a NURBS curve shape")
        with self._scene.undo_chunk("RigCtrlShapeApply"):
            self._transform_selection()
            self._apply_line_width(self._selection.shapes())
        self._state.line_width_dirty = False

    def _rotate_90(self, axis: int) -> None:
        values = list(self._state.values.rotate)
        values[axis] = 90.0
        self._state.values.rotate = tuple(values)

    def rotate_x_90(self) -> None:
        self._rotate_90(0)

    def rotate_y_90(self) -> None:
        self._rotate_90(1)

    def rotate_z_90(self) -> None:
        self._rotate_90(2)
