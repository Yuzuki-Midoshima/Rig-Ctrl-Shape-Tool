"""Low-level Maya scene adapter used by feature use cases."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from contextlib import contextmanager

import maya.cmds as cmds

from ..core.domain import TransformValues
from ..maya.utils import is_settable, preserve_selection, warn


class MayaSceneService:
    preserve_selection = staticmethod(preserve_selection)

    def __init__(self) -> None:
        self._direct_edit_manip_modes: dict[str, tuple[int, str]] = {}
        self._direct_edit_hilited_shapes: list[str] = []
        self._direct_edit_panel_hilites: dict[str, bool] = {}
        self._direct_edit_soft_select: int | None = None
        self._direct_edit_symmetry: int | None = None

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
        self._use_safe_component_manipulators()
        self._disable_weighted_selection()
        self._hide_viewport_selection_hilite()
        cmds.selectMode(component=True)
        shapes = list(dict.fromkeys(cv.split(".cv[", 1)[0] for cv in cvs))
        if self._direct_edit_hilited_shapes:
            cmds.hilite(self._direct_edit_hilited_shapes, unHilite=True)
        self._direct_edit_hilited_shapes = shapes
        cmds.hilite(shapes, replace=True)
        cmds.select(list(cvs), replace=True)
        cmds.setToolTo("Move")

    def pointer_is_over_viewport(self) -> bool:
        """Whether Maya currently reports a model panel below the pointer."""
        panel = cmds.getPanel(underPointer=True)
        return bool(panel and cmds.getPanel(typeOf=panel) == "modelPanel")

    def leave_component_edit(self, controllers: Sequence[str]) -> None:
        """Return to object selection while retaining manual CV edits."""
        cmds.selectMode(object=True)
        if self._direct_edit_hilited_shapes:
            cmds.hilite(self._direct_edit_hilited_shapes, unHilite=True)
            self._direct_edit_hilited_shapes.clear()
        existing = [node for node in controllers if cmds.objExists(node)]
        cmds.select(existing, replace=True) if existing else cmds.select(clear=True)
        self._restore_viewport_selection_hilite()
        self._restore_weighted_selection()
        self._restore_manipulator_modes()

    def ensure_object_mode(self) -> None:
        """Leave Maya in object mode without changing the current selection."""
        cmds.selectMode(object=True)

    def cleanup_legacy_direct_edit_proxies(self) -> None:
        """Remove temporary nodes left by the retired proxy-edit workflow."""
        nodes = cmds.ls(
            "__RigCtrlShapeDirectEdit*",
            "__RigCtrlShapeDirectDisplay*",
            type="transform",
            long=True,
        ) or []
        if not nodes:
            return
        undo_enabled = bool(cmds.undoInfo(query=True, state=True))
        try:
            if undo_enabled:
                cmds.undoInfo(stateWithoutFlush=False)
            cmds.delete(nodes)
        finally:
            if undo_enabled:
                cmds.undoInfo(stateWithoutFlush=True)

    def _hide_viewport_selection_hilite(self) -> None:
        """Keep each curve's display color visible during component editing."""
        if self._direct_edit_panel_hilites:
            return
        for panel in cmds.getPanel(type="modelPanel") or []:
            enabled = bool(
                cmds.modelEditor(panel, query=True, selectionHiliteDisplay=True)
            )
            self._direct_edit_panel_hilites[panel] = enabled
            if enabled:
                cmds.modelEditor(
                    panel, edit=True, selectionHiliteDisplay=False, noUndo=True
                )

    def _restore_viewport_selection_hilite(self) -> None:
        for panel, enabled in self._direct_edit_panel_hilites.items():
            if cmds.modelEditor(panel, exists=True):
                cmds.modelEditor(
                    panel,
                    edit=True,
                    selectionHiliteDisplay=enabled,
                    noUndo=True,
                )
        self._direct_edit_panel_hilites.clear()

    def _use_safe_component_manipulators(self) -> None:
        """Use Maya's component modes without inheriting scaled object axes."""
        if self._direct_edit_manip_modes:
            return
        contexts = (
            ("Move", cmds.manipMoveContext, 2),
            ("Rotate", cmds.manipRotateContext, 10),
            ("Scale", cmds.manipScaleContext, 10),
        )
        undo_enabled = bool(cmds.undoInfo(query=True, state=True))
        try:
            if undo_enabled:
                cmds.undoInfo(stateWithoutFlush=False)
            for name, command, world_mode in contexts:
                if command(name, exists=True):
                    self._direct_edit_manip_modes[name] = (
                        int(command(name, query=True, mode=True)),
                        str(command(name, query=True, xformConstraint=True)),
                    )
                    command(
                        name, edit=True, mode=world_mode, xformConstraint="none"
                    )
        finally:
            if undo_enabled:
                cmds.undoInfo(stateWithoutFlush=True)

    def _restore_manipulator_modes(self) -> None:
        if not self._direct_edit_manip_modes:
            return
        commands = {
            "Move": cmds.manipMoveContext,
            "Rotate": cmds.manipRotateContext,
            "Scale": cmds.manipScaleContext,
        }
        undo_enabled = bool(cmds.undoInfo(query=True, state=True))
        try:
            if undo_enabled:
                cmds.undoInfo(stateWithoutFlush=False)
            for name, (mode, constraint) in self._direct_edit_manip_modes.items():
                command = commands[name]
                if command(name, exists=True):
                    command(
                        name,
                        edit=True,
                        mode=mode,
                        xformConstraint=constraint,
                    )
        finally:
            self._direct_edit_manip_modes.clear()
            if undo_enabled:
                cmds.undoInfo(stateWithoutFlush=True)

    def _disable_weighted_selection(self) -> None:
        if self._direct_edit_soft_select is not None:
            return
        self._direct_edit_soft_select = int(
            cmds.softSelect(query=True, softSelectEnabled=True)
        )
        self._direct_edit_symmetry = int(
            cmds.symmetricModelling(query=True, symmetry=True)
        )
        undo_enabled = bool(cmds.undoInfo(query=True, state=True))
        try:
            if undo_enabled:
                cmds.undoInfo(stateWithoutFlush=False)
            if self._direct_edit_soft_select:
                cmds.softSelect(softSelectEnabled=0)
            if self._direct_edit_symmetry:
                cmds.symmetricModelling(symmetry=0)
        finally:
            if undo_enabled:
                cmds.undoInfo(stateWithoutFlush=True)

    def _restore_weighted_selection(self) -> None:
        if self._direct_edit_soft_select is None:
            return
        undo_enabled = bool(cmds.undoInfo(query=True, state=True))
        try:
            if undo_enabled:
                cmds.undoInfo(stateWithoutFlush=False)
            cmds.softSelect(softSelectEnabled=self._direct_edit_soft_select)
            cmds.symmetricModelling(symmetry=self._direct_edit_symmetry or 0)
        finally:
            self._direct_edit_soft_select = None
            self._direct_edit_symmetry = None
            if undo_enabled:
                cmds.undoInfo(stateWithoutFlush=True)

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
