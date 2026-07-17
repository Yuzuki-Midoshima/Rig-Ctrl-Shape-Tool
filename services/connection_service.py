"""Typed repository facade for controller connections."""

from __future__ import annotations

from collections.abc import Sequence

from .. import connections
from ..domain import PlugConnection


class ConnectionService:
    def capture(self, node: str) -> tuple[PlugConnection, ...]:
        pairs = [*connections.incoming_connections(node), *connections.outgoing_connections(node)]
        return tuple(PlugConnection(source, destination) for source, destination in pairs)

    def reconnect(self, snapshot: Sequence[PlugConnection]) -> None:
        connections.reconnect_connections([
            (connection.source_plug, connection.destination_plug) for connection in snapshot
        ])

    transfer = staticmethod(connections.transfer_controller_connections)
    unlock = staticmethod(connections.unlock_node_attributes)
    disconnect = staticmethod(connections.disconnect_node_connections)
    unparent = staticmethod(connections.unparent_to_world)
    rename = staticmethod(connections.rename_as_new_controller)
