"""Composition root: construct dependencies and show the tool window."""

from __future__ import annotations

from PySide6 import QtCore, QtWidgets

from .core.state import ToolState
from .features import (
    ColorFeature,
    ControlsFeature,
    CopyPasteFeature,
    DisconnectFeature,
    PreviewFeature,
    TransformFeature,
)
from .maya.utils import maya_main_window
from .services import (
    ColorService,
    ConnectionService,
    CurveService,
    MayaSceneService,
    SelectionService,
    WindowService,
)
from .ui import RigCtrlShapeWindow


def _find_existing_window(parent: QtWidgets.QWidget | None) -> QtCore.QObject | None:
    existing = parent.findChild(QtCore.QObject, "RigCtrlShapeTool") if parent else None
    if existing is not None:
        return existing
    return next(
        (widget for widget in QtWidgets.QApplication.topLevelWidgets()
         if widget.objectName() == "RigCtrlShapeTool"),
        None,
    )


def show() -> RigCtrlShapeWindow:
    """Create a fresh application graph and show its single Maya-owned window."""
    parent = maya_main_window()
    existing = _find_existing_window(parent)
    if existing is not None:
        existing.close()
        existing.deleteLater()

    state = ToolState()
    selection = SelectionService()
    curves = CurveService()
    colors = ColorService()
    connection_service = ConnectionService()
    window_service = WindowService()
    scene = MayaSceneService()
    transform = TransformFeature(state, selection, scene)
    preview = PreviewFeature(state, selection, scene)
    color = ColorFeature(state, selection, colors, scene)
    controls = ControlsFeature(state)
    copy_paste = CopyPasteFeature(state, selection, curves, connection_service, scene)
    disconnect = DisconnectFeature(selection, connection_service, scene)

    transform.cancel_preview = preview.rollback
    transform.cancel_color = color.rollback
    transform.has_active_preview = lambda: preview.is_active
    transform.commit_preview = preview.commit
    preview.cancel_color = color.rollback
    controls.changed = preview.update_preview
    def cancel_sessions() -> None:
        """Rollback edits while preserving the Preview checkbox preference."""
        color.rollback()
        preview.rollback(keep_enabled=state.preview.enabled)

    copy_paste.cancel_sessions = cancel_sessions
    disconnect.cancel_sessions = cancel_sessions

    window = RigCtrlShapeWindow(
        transform,
        preview,
        color,
        copy_paste,
        disconnect,
        controls,
        parent=parent,
    )
    color.colors_changed = window.handle_color_state_changed
    state.window.event_jobs = window_service.watch_scene(window.refresh_colors)

    def close() -> None:
        if state.window.closing:
            return
        state.window.closing = True
        window_service.stop_watching(state.window.event_jobs)
        state.window.event_jobs.clear()
        color.rollback()
        preview.rollback()

    window.closing.connect(close)
    window.refresh_colors()
    window.show()
    return window


__all__ = ["show"]
