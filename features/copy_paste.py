"""Copy buffer and Replace/Add curve-shape use case."""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from ..constants import CurveDisplayAttributes
from ..errors import InvalidSelectionError, MissingCopyBufferError, UnsupportedShapeError
from ..services import ConnectionService, CurveService, MayaSceneService, SelectionService
from ..state import ToolState

class CopyPasteFeature:
    """Own the copy buffer and execute Replace/Add shape workflows."""

    def __init__(self, state: ToolState, selection: SelectionService, curves: CurveService,
                 connections: ConnectionService, scene: MayaSceneService) -> None:
        self._state = state
        self._selection = selection
        self._curves = curves
        self._connections = connections
        self._scene = scene
        self.cancel_sessions: Callable[[], None] = lambda: None

    def copy(self) -> None:
        controller = self._selection.first_controller()
        if not controller:
            raise InvalidSelectionError("Select a controller to copy")
        if not self._selection.curve_shapes(controller):
            raise UnsupportedShapeError("Selected controller has no NURBS curve shape")
        self._state.copy_buffer.controller = self._selection.long_name(controller)

    def paste_replace(self) -> None:
        """Replace the copied controller's shapes with the selected shapes."""
        self._paste("replace")

    def paste_add(self) -> None:
        """Create an additional controller using the selected shapes."""
        self._paste("add")

    def _paste(self, mode: Literal["replace", "add"]) -> None:
        rig = self._state.copy_buffer.controller
        if not rig or not self._scene.exists(rig):
            raise MissingCopyBufferError("The copied Rig Controller is not available")
        visual = self._selection.first_controller()
        if not visual or self._selection.long_name(visual) == self._selection.long_name(rig):
            raise InvalidSelectionError("Select the new Controller Shape")
        source_shapes = self._selection.curve_shapes(visual)
        rig_shapes = self._selection.curve_shapes(rig)
        if not source_shapes or not rig_shapes:
            raise UnsupportedShapeError("A valid NURBS curve shape was not found")
        if self._scene.is_referenced(rig):
            raise UnsupportedShapeError("Referenced Controller shapes cannot be replaced")
        self.cancel_sessions()
        settings = self._curves.display_settings(
            rig_shapes[0], CurveDisplayAttributes.ALL
        )
        try:
            with self._scene.undo_chunk("RigCtrlShapePaste"), self._scene.preserve_selection():
                if not self._curves.align_position(visual, rig):
                    raise RuntimeError("Position alignment failed")
                definitions = tuple(self._curves.capture(shape) for shape in source_shapes)
                if mode == "add":
                    target = self._curves.create_add_controller(rig, definitions, settings)
                    self._connections.transfer(rig, target)
                else:
                    self._scene.delete(rig_shapes)
                    for definition in definitions:
                        shape = self._curves.create(rig, definition)
                        self._curves.apply_display_settings(shape, settings)
                self._curves.delete_source_if_safe(visual)
        except (RuntimeError, ValueError):
            self._scene.rollback_named_undo("RigCtrlShapePaste")
            raise
