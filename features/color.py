"""Transactional color-edit use case with a Qt-independent public API."""

from __future__ import annotations

from collections.abc import Callable

from ..domain import ColorSwatchData, ColorValue, ColorViewData
from ..errors import EditSessionError, InvalidSelectionError
from ..services import ColorService, MayaSceneService, SelectionService
from ..state import ColorSession, ToolState


class ColorFeature:
    """Manage transactional controller-color editing without UI dependencies."""

    def __init__(self, state: ToolState, selection: SelectionService,
                 colors: ColorService, scene: MayaSceneService) -> None:
        self._state = state
        self._selection = selection
        self._colors = colors
        self._scene = scene
        self.colors_changed: Callable[[], None] = lambda: None

    @property
    def is_active(self) -> bool:
        session = self._state.color_session
        return bool(session and session.lifecycle.is_active)

    def begin_edit(self) -> ColorViewData:
        if self.is_active:
            return self.get_current_view_data()
        grouped = self._selection.grouped_shapes()
        if not grouped:
            raise InvalidSelectionError("Select a controller with a NURBS curve shape")
        original = {
            shape: self._colors.capture(shape)
            for shapes in grouped.values()
            for shape in shapes
        }
        session = ColorSession(original)
        session.lifecycle.begin()
        self._state.color_session = session
        try:
            self._scene.open_undo("RigCtrlShapeColor")
            session.undo_open = True
        except Exception:
            if session.lifecycle.is_active:
                session.lifecycle.rollback()
            self._state.color_session = None
            raise
        return self.get_current_view_data()

    def get_current_view_data(self) -> ColorViewData:
        grouped = self._selection.grouped_shapes()
        session = self._state.color_session
        saved = session.original if session else {}
        swatches = []
        for controller, shapes in grouped.items():
            state = saved.get(shapes[0]) or self._colors.capture(shapes[0])
            swatches.append(ColorSwatchData(controller, self._colors.display_color(state)))
        if not swatches:
            raise InvalidSelectionError("Select a controller with a NURBS curve shape")
        return ColorViewData(swatches[0].color, tuple(swatches))

    def update_preview(self, color: ColorValue) -> None:
        session = self._state.color_session
        if not session or not session.lifecycle.is_active:
            raise EditSessionError("Color edit session is not active")
        if color.rgb is None:
            raise EditSessionError("Preview color does not contain an RGB value")
        for shape in session.original:
            self._colors.apply(shape, color.rgb)
        self.colors_changed()

    def commit(self) -> None:
        self._finish(True)

    def rollback(self) -> None:
        self._finish(False)

    def _finish(self, accepted: bool) -> None:
        session = self._state.color_session
        if not session or not session.lifecycle.is_active:
            return
        try:
            if accepted:
                self._state.color_reset_states.update(session.original)
                session.lifecycle.commit()
            else:
                for shape, original in session.original.items():
                    self._colors.restore(shape, original)
                session.lifecycle.rollback()
        finally:
            if session.lifecycle.is_active:
                session.lifecycle.rollback()
            if session.undo_open:
                self._scene.close_undo()
                session.undo_open = False
            self._state.color_session = None
            self.colors_changed()

    def reset(self) -> ColorValue | None:
        session = self._state.color_session
        if session:
            for shape, original in session.original.items():
                self._colors.restore(shape, original)
            self.colors_changed()
            return self._colors.display_color(next(iter(session.original.values())))
        restore = {
            shape: self._state.color_reset_states[shape]
            for shape in self._selection.shapes()
            if shape in self._state.color_reset_states
        }
        if not restore:
            return None
        with self._scene.undo_chunk("RigCtrlShapeResetColor"):
            for shape, original in restore.items():
                self._colors.restore(shape, original)
                self._state.color_reset_states.pop(shape, None)
        self.colors_changed()
        return None
