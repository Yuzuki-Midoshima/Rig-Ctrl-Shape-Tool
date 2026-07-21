"""Controller connection inspection, transfer, and cleanup."""

from __future__ import annotations

import maya.cmds as cmds

from .utils import long_name, warn

def connection_pairs(node: str) -> list[tuple[str, str]]:
    raw = cmds.listConnections(
        node, source=True, destination=True, plugs=True,
        connections=True, skipConversionNodes=False,
    ) or []
    return list(zip(raw[0::2], raw[1::2]))


def plug_on_node(pair: tuple[str, str], node: str) -> tuple[str, str] | None:
    prefix = f"{long_name(node)}."
    short_prefix = f"{node.rsplit('|', 1)[-1]}."
    for index, plug in enumerate(pair):
        node_name, attribute = plug.split(".", 1)
        long_plug = (cmds.ls(node_name, long=True) or [node_name])[0]
        normalized = f"{long_plug}.{attribute}"
        if normalized.startswith(prefix) or plug.startswith(short_prefix):
            return normalized, pair[1 - index]
    return None


def matching_plug(source_plug: str, source_node: str, target_node: str) -> str | None:
    source_long = long_name(source_node)
    if not source_plug.startswith(f"{source_long}."):
        return None
    target_plug = f"{target_node}.{source_plug[len(source_long) + 1:]}"
    return target_plug if cmds.objExists(target_plug) else None


def transfer_controller_connections(source_controller: str, target_controller: str) -> None:
    seen = set()
    for pair in connection_pairs(source_controller):
        local_pair = plug_on_node(pair, source_controller)
        if not local_pair or local_pair in seen:
            continue
        seen.add(local_pair)
        source_plug, external_plug = local_pair
        target_plug = matching_plug(source_plug, source_controller, target_controller)
        if not target_plug:
            continue
        try:
            if cmds.isConnected(external_plug, source_plug):
                if not cmds.isConnected(external_plug, target_plug):
                    cmds.connectAttr(external_plug, target_plug, force=True)
            elif cmds.isConnected(source_plug, external_plug):
                cmds.connectAttr(target_plug, external_plug, force=True)
        except RuntimeError as error:
            warn(f"Could not transfer connection ({source_plug})", error)


def unlock_node_attributes(node: str) -> None:
    if cmds.referenceQuery(node, isNodeReferenced=True):
        return
    for attribute in cmds.listAttr(node, locked=True) or []:
        try:
            cmds.setAttr(f"{node}.{attribute}", lock=False)
        except RuntimeError:
            continue


def disconnect_node_connections(node: str) -> None:
    handled = set()
    for pair in connection_pairs(node):
        local_pair = plug_on_node(pair, node)
        if not local_pair:
            continue
        local_plug, external_plug = local_pair
        if cmds.isConnected(external_plug, local_plug):
            connection = (external_plug, local_plug)
        elif cmds.isConnected(local_plug, external_plug):
            connection = (local_plug, external_plug)
        else:
            continue
        if connection in handled:
            continue
        handled.add(connection)
        try:
            cmds.disconnectAttr(*connection)
        except RuntimeError as error:
            warn(f"Could not disconnect {connection[0]} -> {connection[1]}", error)


def unparent_to_world(controller: str) -> str:
    if not cmds.listRelatives(controller, parent=True, fullPath=True):
        return controller
    try:
        return cmds.parent(controller, world=True)[0]
    except RuntimeError as error:
        warn("Could not unparent the controller", error)
        return controller


def rename_as_new_controller(controller: str) -> None:
    try:
        cmds.rename(controller, "controller#")
    except RuntimeError as error:
        warn("Could not rename the controller", error)
