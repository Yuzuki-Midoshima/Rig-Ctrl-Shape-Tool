"""Common Maya queries and safe operation helpers."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator, Sequence

import maya.cmds as cmds
from maya import OpenMayaUI as omui
from PySide6 import QtWidgets
from shiboken6 import wrapInstance


def maya_main_window() -> QtWidgets.QWidget | None:
    if cmds.about(batch=True):
        return None
    pointer = omui.MQtUtil.mainWindow()
    return wrapInstance(int(pointer), QtWidgets.QWidget) if pointer else None


def long_name(node: str) -> str:
    names = cmds.ls(node, long=True) or []
    return names[0] if names else node


def nurbs_curve_shapes(transform: str) -> list[str]:
    return [
        shape
        for shape in cmds.listRelatives(transform, shapes=True, fullPath=True) or []
        if cmds.nodeType(shape) == "nurbsCurve"
        and not bool(cmds.getAttr(f"{shape}.intermediateObject"))
    ]


def selected_controller_transforms() -> list[str]:
    selected = cmds.ls(selection=True, objectsOnly=True, long=True) or []
    if not selected:
        selected = cmds.ls(selection=True, long=True) or []
    controllers = []
    for node in selected:
        if not cmds.objExists(node):
            continue
        node_type = cmds.nodeType(node)
        if node_type == "nurbsCurve" or node_type not in ("transform", "joint"):
            parents = cmds.listRelatives(node, parent=True, fullPath=True) or []
            node = parents[0] if parents else ""
        if node and node not in controllers:
            controllers.append(node)
    return controllers


def selected_controller_transform() -> str | None:
    controllers = selected_controller_transforms()
    return controllers[0] if controllers else None


def controller_curve_shapes(controllers: Sequence[str]) -> dict[str, list[str]]:
    return {
        controller: shapes
        for controller in controllers
        if cmds.objExists(controller)
        if (shapes := nurbs_curve_shapes(controller))
    }


def selected_curve_shapes() -> list[str]:
    grouped = controller_curve_shapes(selected_controller_transforms())
    return [shape for shapes in grouped.values() for shape in shapes]


def shape_cvs(controller: str) -> list[str]:
    if cmds.objExists(controller) and cmds.nodeType(controller) == "nurbsCurve":
        parents = cmds.listRelatives(controller, parent=True, fullPath=True) or []
        controller = parents[0] if parents else controller
    return [
        cv
        for shape in nurbs_curve_shapes(controller)
        for cv in cmds.ls(f"{shape}.cv[*]", flatten=True) or []
    ]


def selected_shape_cvs() -> list[str]:
    return [cv for controller in selected_controller_transforms() for cv in shape_cvs(controller)]


def safe_get_attr(plug: str) -> Any:
    try:
        return cmds.getAttr(plug)
    except (RuntimeError, ValueError):
        return None


def is_settable(plug: str) -> bool:
    try:
        return bool(cmds.objExists(plug) and cmds.getAttr(plug, settable=True))
    except (RuntimeError, ValueError):
        return False


def warn(message: str, error: Exception | None = None) -> None:
    cmds.warning(f"{message}: {error}" if error else message)


@contextmanager
def preserve_selection() -> Iterator[None]:
    """Restore surviving members of Maya's original selection."""
    original = cmds.ls(selection=True, long=True) or []
    try:
        yield
    finally:
        existing = [node for node in original if cmds.objExists(node)]
        cmds.select(existing, replace=True) if existing else cmds.select(clear=True)
