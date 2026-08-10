"""Selection and controller-shape queries."""

from __future__ import annotations

import maya.cmds as cmds

from ..maya import utils as maya_utils


class SelectionService:
    """Provide controller-oriented views of Maya's active selection."""

    def controllers(self) -> list[str]:
        return maya_utils.selected_controller_transforms()

    def first_controller(self) -> str | None:
        return maya_utils.selected_controller_transform()

    def grouped_shapes(self, controllers: list[str] | None = None) -> dict[str, list[str]]:
        return maya_utils.controller_curve_shapes(controllers or self.controllers())

    def shapes(self) -> list[str]:
        return maya_utils.selected_curve_shapes()

    def cvs(self) -> list[str]:
        return maya_utils.selected_shape_cvs()

    def controller_cvs(self, controller: str) -> list[str]:
        return maya_utils.shape_cvs(controller)

    def joints(self) -> list[str]:
        """Return individually selected joint nodes."""
        return cmds.ls(selection=True, long=True, type="joint") or []

    def curve_shapes(self, controller: str) -> list[str]:
        """Return editable NURBS curve shapes below one controller."""
        return maya_utils.nurbs_curve_shapes(controller)

    def long_name(self, node: str) -> str:
        """Return Maya's stable long DAG path for a node."""
        return maya_utils.long_name(node)
