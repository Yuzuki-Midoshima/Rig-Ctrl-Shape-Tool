"""Capture and recreate NURBS controller shapes."""

from __future__ import annotations

from collections.abc import Sequence

import maya.cmds as cmds
from maya.api import OpenMaya as om

from .domain import CurveForm, CurveShapeData, DisplaySettings
from .maya_utils import is_settable, long_name, nurbs_curve_shapes, safe_get_attr, warn


def _curve_function(shape: str) -> om.MFnNurbsCurve:
    selection = om.MSelectionList()
    selection.add(shape)
    return om.MFnNurbsCurve(selection.getDagPath(0))


def capture_curve_definition(shape: str) -> CurveShapeData:
    curve = _curve_function(shape)
    points = curve.cvPositions(om.MSpace.kWorld)
    point_values = tuple((point.x, point.y, point.z, point.w) for point in points)
    form = {
        om.MFnNurbsCurve.kOpen: CurveForm.OPEN,
        om.MFnNurbsCurve.kClosed: CurveForm.CLOSED,
        om.MFnNurbsCurve.kPeriodic: CurveForm.PERIODIC,
    }[curve.form]
    return CurveShapeData(
        points=point_values, knots=tuple(curve.knots()), degree=curve.degree,
        form=form, rational=any(abs(point[3] - 1.0) > 1.0e-8 for point in point_values),
        dimension=3, spans=curve.numSpans,
    )


def create_curve_shape(target: str, curve_data: CurveShapeData) -> str:
    selection = om.MSelectionList()
    selection.add(target)
    inverse_matrix = selection.getDagPath(0).inclusiveMatrixInverse()
    local_points = []
    for x_pos, y_pos, z_pos, weight in curve_data.points:
        local = om.MPoint(x_pos, y_pos, z_pos, weight) * inverse_matrix
        local_points.append((local.x, local.y, local.z, local.w))
    shape = cmds.createNode("nurbsCurve", parent=target)
    cv_values = tuple(point if curve_data.rational else point[:3] for point in local_points)
    cmds.setAttr(
        f"{shape}.create",
        curve_data.degree, curve_data.spans, curve_data.form.value,
        curve_data.rational, curve_data.dimension, curve_data.knots,
        0, len(cv_values), *cv_values, type="nurbsCurve",
    )
    return long_name(shape)


def shape_display_settings(shape: str, attributes: Sequence[str]) -> DisplaySettings:
    settings = {}
    for attribute in attributes:
        plug = f"{shape}.{attribute}"
        if not cmds.objExists(plug):
            continue
        value = safe_get_attr(plug)
        if value is not None:
            settings[attribute] = value[0] if isinstance(value, list) else value
    return DisplaySettings(tuple(settings.items()))


def apply_shape_display_settings(shape: str, settings: DisplaySettings) -> None:
    for attribute, value in settings.values:
        plug = f"{shape}.{attribute}"
        if not is_settable(plug):
            continue
        try:
            cmds.setAttr(plug, *value) if isinstance(value, tuple) else cmds.setAttr(plug, value)
        except RuntimeError:
            continue


def align_curve_position(target: str, source: str) -> bool:
    """Align visible curve CVs without moving the target transform or pivot."""
    try:
        source_position = cmds.xform(
            source, query=True, worldSpace=True, translation=True
        )
        target_position = cmds.xform(
            target, query=True, worldSpace=True, translation=True
        )
        delta = tuple(
            source_value - target_value
            for source_value, target_value in zip(source_position, target_position)
        )
        cvs = [
            cv
            for shape in nurbs_curve_shapes(target)
            for cv in cmds.ls(f"{shape}.cv[*]", flatten=True) or []
        ]
        if not cvs:
            warn("Could not align position because the target has no curve CVs")
            return False
        cmds.move(*delta, cvs, relative=True, worldSpace=True)
        return True
    except RuntimeError as error:
        warn("Could not match position. Check locked or connected attributes", error)
        return False


def delete_visual_source_if_safe(transform: str) -> None:
    children = cmds.listRelatives(transform, children=True, type="transform", fullPath=True) or []
    non_curves = [
        shape
        for shape in cmds.listRelatives(transform, shapes=True, fullPath=True) or []
        if cmds.nodeType(shape) != "nurbsCurve"
    ]
    if children or non_curves or cmds.referenceQuery(transform, isNodeReferenced=True):
        warn("Source transform was kept because it contains another node or is referenced")
        return
    cmds.delete(transform)


def create_add_controller(
    rig_controller: str,
    curve_definitions: Sequence[CurveShapeData],
    display_settings: DisplaySettings,
) -> str:
    source_name = rig_controller.rsplit("|", 1)[-1]
    duplicates = cmds.duplicate(
        rig_controller, returnRootsOnly=True, parentOnly=True, renameChildren=True
    ) or []
    if not duplicates:
        raise RuntimeError("Could not duplicate the rig controller")
    new_controller = long_name(cmds.rename(duplicates[0], f"{source_name}_1"))
    old_shapes = nurbs_curve_shapes(new_controller)
    if old_shapes:
        cmds.delete(old_shapes)
    for curve_data in curve_definitions:
        shape = create_curve_shape(new_controller, curve_data)
        apply_shape_display_settings(shape, display_settings)
    return new_controller
