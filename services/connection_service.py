"""Typed repository facade for controller connections."""

from __future__ import annotations

from ..maya import connections


class ConnectionService:
    """Expose only connection operations used by current Feature workflows."""

    transfer = staticmethod(connections.transfer_controller_connections)
    unlock = staticmethod(connections.unlock_node_attributes)
    disconnect = staticmethod(connections.disconnect_node_connections)
    hide_user_attributes = staticmethod(connections.hide_user_defined_attributes)
    show_default_attributes = staticmethod(connections.show_default_transform_attributes)
    unparent = staticmethod(connections.unparent_to_world)
    rename = staticmethod(connections.rename_as_new_controller)
