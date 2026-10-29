"""Low-level Maya scene adapter used by feature use cases."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from contextlib import contextmanager

import maya.cmds as cmds

from ..core.domain import TransformValues
from ..maya.utils import is_settable, preserve_selection, warn


class MayaSceneService:
    preserve_selection = staticmethod(preserve_selection)

    def exists(self, node: str) -> bool:
        return bool(cmds.objExists(node))

    def is_referenced(self, node: str) -> bool:
        return bool(cmds.referenceQuery(node, isNodeReferenced=True))

    def delete(self, nodes: Sequence[str]) -> None:
        cmds.delete(list(nodes))

    def transform_cvs(self, cvs: Sequence[str], values: TransformValues) -> None:
        components = list(cvs)
        bounds = cmds.exactWorldBoundingBox(components)
        pivot = tuple((bounds[index] + bounds[index + 3]) * .5 for index in range(3))
        scale = tuple(values.uniform * axis for axis in values.scale)
        cmds.scale(*scale, components, relative=True, worldSpace=True, pivot=pivot)
        cmds.rotate(*values.rotate, components, relative=True, worldSpace=True, pivot=pivot)
        # Scale and rotate are evaluated in world space, so Move must use the
        # same coordinate frame.  Object-space translation follows the
        # controller transform axes, which can make a requested single-axis
        # move travel diagonally when the controller (or one of its parents)
        # is rotated.  Preview sessions recapture the committed CV positions,
        # making the adjusted shape the baseline for the next edit.
        cmds.move(*values.move, components, relative=True, worldSpace=True)

    def cv_position(self, cv: str) -> tuple[float, float, float]:
        return tuple(cmds.xform(cv, query=True, objectSpace=True, translation=True))

    def set_cv_position(self, cv: str, position: Sequence[float]) -> None:
        cmds.xform(cv, objectSpace=True, translation=position)

    def enter_component_edit(self, cvs: Sequence[str]) -> None:
        """Select curve CVs and expose Maya's native component manipulators."""
        cmds.select(list(cvs), replace=True)
        cmds.selectMode(component=True)
        cmds.setToolTo("Move")

    def pointer_is_over_viewport(self) -> bool:
        """Whether Maya currently reports a model panel below the pointer."""
        panel = cmds.getPanel(underPointer=True)
        return bool(panel and cmds.getPanel(typeOf=panel) == "modelPanel")

    def leave_component_edit(self, controllers: Sequence[str]) -> None:
        """Return to object selection while retaining manual CV edits."""
        cmds.selectMode(object=True)
        existing = [node for node in controllers if cmds.objExists(node)]
        cmds.select(existing, replace=True) if existing else cmds.select(clear=True)

    def line_width(self, shape: str) -> float | None:
        plug = f"{shape}.lineWidth"
        return float(cmds.getAttr(plug)) if cmds.objExists(plug) else None

    def set_line_width(self, shape: str, value: float) -> None:
        plug = f"{shape}.lineWidth"
        if is_settable(plug):
            cmds.setAttr(plug, value)

    def joint_size(self, joint: str) -> float | None:
        plug = f"{joint}.radius"
        return float(cmds.getAttr(plug)) if cmds.objExists(plug) else None

    def set_joint_size(self, joint: str, value: float) -> None:
        plug = f"{joint}.radius"
        if is_settable(plug):
            cmds.setAttr(plug, value)

    def open_undo(self, name: str) -> None:
        cmds.undoInfo(openChunk=True, chunkName=name)

    def close_undo(self) -> None:
        cmds.undoInfo(closeChunk=True)

    @contextmanager
    def undo_chunk(self, name: str) -> Iterator[None]:
        self.open_undo(name)
        try:
            yield
        finally:
            self.close_undo()

    def rollback_named_undo(self, name: str) -> None:
        if cmds.undoInfo(query=True, undoName=True) == name:
            cmds.undo()

    def undo_name(self) -> str:
        return str(cmds.undoInfo(query=True, undoName=True) or "")

    def redo_name(self) -> str:
        return str(cmds.undoInfo(query=True, redoName=True) or "")

    def warning(self, message: str, error: Exception | None = None) -> None:
        warn(message, error)

    def show_status(self, message: str) -> None:
        """Show a short success message in Maya's active viewport."""
        cmds.inViewMessage(
            amg=f"<hl>{message}</hl>",
            pos="midCenter",
            fade=True,
        )
