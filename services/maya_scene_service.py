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
        cmds.move(*values.move, components, relative=True, objectSpace=True)

    def cv_position(self, cv: str) -> tuple[float, float, float]:
        return tuple(cmds.xform(cv, query=True, objectSpace=True, translation=True))

    def set_cv_position(self, cv: str, position: Sequence[float]) -> None:
        cmds.xform(cv, objectSpace=True, translation=position)

    def line_width(self, shape: str) -> float | None:
        plug = f"{shape}.lineWidth"
        return float(cmds.getAttr(plug)) if cmds.objExists(plug) else None

    def set_line_width(self, shape: str, value: float) -> None:
        plug = f"{shape}.lineWidth"
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
