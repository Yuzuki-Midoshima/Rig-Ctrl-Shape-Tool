"""Safe controller connection cleanup workflow."""

from __future__ import annotations

from collections.abc import Callable

from ..core.errors import InvalidSelectionError, UnsupportedShapeError
from ..services import ConnectionService, MayaSceneService, SelectionService


class DisconnectFeature:
    """Safely remove connections from the selected controller."""

    def __init__(self, selection: SelectionService, connections: ConnectionService,
                 scene: MayaSceneService) -> None:
        self._selection = selection
        self._connections = connections
        self._scene = scene
        self.cancel_sessions: Callable[[], None] = lambda: None

    def disconnect_selected(self) -> None:
        """Disconnect the selection inside one Maya-restorable Undo chunk."""
        controller = self._selection.first_controller()
        if not controller:
            raise InvalidSelectionError("Select a controller to disconnect")
        if self._scene.is_referenced(controller):
            raise UnsupportedShapeError("Referenced Controller connections cannot be removed")
        self.cancel_sessions()
        with self._scene.undo_chunk("RigCtrlShapeDisconnect"):
            for node in [controller, *self._selection.curve_shapes(controller)]:
                self._connections.unlock(node)
                self._connections.disconnect(node)
                self._connections.hide_user_attributes(node)
            controller = self._connections.unparent(controller)
            self._connections.rename(controller)
