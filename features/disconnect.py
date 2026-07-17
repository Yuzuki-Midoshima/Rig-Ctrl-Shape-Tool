"""Safe controller connection cleanup workflow."""

from __future__ import annotations

from collections.abc import Callable

from ..errors import InvalidSelectionError, UnsupportedShapeError
from ..domain import PlugConnection
from ..services import ConnectionService, MayaSceneService, SelectionService


class DisconnectFeature:
    """Capture and safely remove connections from the selected controller."""

    def __init__(self, selection: SelectionService, connections: ConnectionService,
                 scene: MayaSceneService) -> None:
        self._selection = selection
        self._connections = connections
        self._scene = scene
        self.cancel_sessions: Callable[[], None] = lambda: None
        self._last_connections: list[PlugConnection] = []

    def _connections_for(self, node: str) -> tuple[PlugConnection, ...]:
        return self._connections.capture(node)

    def restore_connections(self) -> None:
        """Restore the last captured connections; normal UI restoration uses Maya Undo."""
        self._connections.reconnect(self._last_connections)

    def disconnect_selected(self) -> None:
        """Disconnect the selected controller and preserve a restorable snapshot."""
        controller = self._selection.first_controller()
        if not controller:
            raise InvalidSelectionError("Select a controller to disconnect")
        if self._scene.is_referenced(controller):
            raise UnsupportedShapeError("Referenced Controller connections cannot be removed")
        self.cancel_sessions()
        with self._scene.undo_chunk("RigCtrlShapeDisconnect"):
            self._last_connections = []
            for node in [controller, *self._selection.curve_shapes(controller)]:
                self._last_connections.extend(self._connections_for(node))
                self._connections.unlock(node)
                self._connections.disconnect(node)
            controller = self._connections.unparent(controller)
            self._connections.rename(controller)
