"""Maya 2026 integration tests. Run with mayapy, not standard Python."""

from __future__ import annotations

import unittest
import os
import tempfile

import maya.cmds as cmds
from maya.api import OpenMaya as om

from rig_ctrl_shape_tool.domain import ColorValue
from rig_ctrl_shape_tool.errors import UnsupportedShapeError
from rig_ctrl_shape_tool.features import ColorFeature, CopyPasteFeature, PreviewFeature, TransformFeature
from rig_ctrl_shape_tool.maya_utils import nurbs_curve_shapes
from rig_ctrl_shape_tool.services import (
    ColorService, ConnectionService, CurveService, MayaSceneService, SelectionService,
)
from rig_ctrl_shape_tool.state import ToolState


class MayaCurveIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import maya.standalone
        try:
            maya.standalone.initialize(name="python")
        except RuntimeError:
            pass

    def setUp(self):
        cmds.file(new=True, force=True)
        self.state = ToolState()
        self.selection = SelectionService()
        self.curves = CurveService()
        self.connections = ConnectionService()
        self.scene = MayaSceneService()
        self.feature = CopyPasteFeature(
            self.state, self.selection, self.curves, self.connections, self.scene
        )

    @staticmethod
    def _open_curve(name: str, offset: float = 0.0) -> str:
        return cmds.curve(
            name=name, degree=1,
            point=[(offset, 0, 0), (offset + 1, 2, 0), (offset + 2, 0, 0)],
        )

    @staticmethod
    def _periodic_curve(name: str) -> str:
        points = [(0, 0, 0), (1, 0, 1), (0, 0, 2), (-1, 0, 1)]
        return cmds.curve(
            name=name, degree=1, periodic=True,
            point=[*points, points[0]], knot=list(range(5)),
        )

    @staticmethod
    def _feature_for(state: ToolState) -> CopyPasteFeature:
        return CopyPasteFeature(
            state, SelectionService(), CurveService(), ConnectionService(), MayaSceneService()
        )

    def _copy_rig(self, rig: str) -> None:
        cmds.select(rig, replace=True)
        self.feature.copy()

    def test_replace_preserves_multiple_typed_shapes_and_supports_undo_redo(self):
        rig = self._open_curve("rig_ctrl")
        visual = self._open_curve("visual_ctrl", 5)
        periodic = self._periodic_curve("periodic_visual")
        periodic_shape = nurbs_curve_shapes(periodic)[0]
        cmds.parent(periodic_shape, visual, shape=True, relative=True)
        cmds.delete(periodic)
        self.assertEqual(len(nurbs_curve_shapes(visual)), 2)

        self._copy_rig(rig)
        cmds.select(visual, replace=True)
        self.feature.paste_replace()
        shapes = nurbs_curve_shapes(rig)
        self.assertEqual(len(shapes), 2)
        self.assertIn(2, {self.curves.capture(shape).form.value for shape in shapes})
        self.assertFalse(cmds.objExists(visual))

        cmds.undo()
        self.assertTrue(cmds.objExists(visual))
        self.assertEqual(len(nurbs_curve_shapes(rig)), 1)
        cmds.redo()
        self.assertEqual(len(nurbs_curve_shapes(rig)), 2)

    def test_rational_curve_weights_survive_typed_round_trip(self):
        source = cmds.createNode("transform", name="rational_source")
        selection = om.MSelectionList(); selection.add(source)
        parent = selection.getDependNode(0)
        points = om.MPointArray([
            om.MPoint(0, 0, 0, 1.0), om.MPoint(1, 2, 0, 0.5),
            om.MPoint(2, 2, 0, 0.5), om.MPoint(3, 0, 0, 1.0),
        ])
        curve = om.MFnNurbsCurve()
        curve_object = curve.create(
            points, [0, 0, 1, 2, 2], 2, om.MFnNurbsCurve.kOpen,
            False, True, parent,
        )
        source_shape = om.MFnDagNode(curve_object).fullPathName()
        data = self.curves.capture(source_shape)
        self.assertTrue(data.rational)
        target = cmds.createNode("transform", name="rational_target")
        created = self.curves.create(target, data)
        recreated = self.curves.capture(created)
        self.assertTrue(recreated.rational)
        self.assertEqual(
            tuple(round(point[3], 6) for point in recreated.points),
            (1.0, 0.5, 0.5, 1.0),
        )

    def test_add_moves_outgoing_connection_to_new_controller(self):
        rig = self._open_curve("connected_ctrl")
        visual = self._open_curve("add_visual", 5)
        receiver = cmds.createNode("transform", name="receiver")
        cmds.addAttr(rig, longName="driver", attributeType="double", keyable=True)
        cmds.addAttr(receiver, longName="driven", attributeType="double", keyable=True)
        cmds.connectAttr(f"{rig}.driver", f"{receiver}.driven")

        self._copy_rig(rig)
        cmds.select(visual, replace=True)
        self.feature.paste_add()
        source = cmds.connectionInfo(f"{receiver}.driven", sourceFromDestination=True)
        self.assertTrue(source)
        self.assertNotEqual(source.split(".", 1)[0], rig)
        self.assertTrue(cmds.objExists(source))

    def test_locked_target_rolls_back_failed_replace(self):
        rig = self._open_curve("locked_ctrl")
        visual = self._open_curve("locked_visual", 5)
        original_shapes = tuple(nurbs_curve_shapes(rig))
        cmds.setAttr(f"{visual}.translateX", 5)
        cmds.lockNode(visual, lock=True)
        self._copy_rig(rig)
        cmds.select(visual, replace=True)

        with self.assertRaises(RuntimeError):
            self.feature.paste_replace()
        self.assertTrue(cmds.objExists(visual))
        self.assertEqual(tuple(nurbs_curve_shapes(rig)), original_shapes)

    def test_selection_is_restored_when_original_node_survives(self):
        rig = self._open_curve("selection_rig")
        visual = self._open_curve("selection_visual", 5)
        keeper = cmds.createNode("transform", name="selection_keeper")
        self._copy_rig(rig)
        cmds.select([visual, keeper], replace=True)
        self.feature.paste_replace()
        selected = cmds.ls(selection=True, long=True) or []
        self.assertEqual(selected, [cmds.ls(keeper, long=True)[0]])

    def test_referenced_controller_is_rejected_without_scene_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            reference_file = os.path.join(directory, "referenced_controller.ma")
            referenced_source = self._open_curve("ref_ctrl")
            cmds.file(rename=reference_file)
            cmds.file(save=True, type="mayaAscii", force=True)
            cmds.file(new=True, force=True)
            cmds.file(reference_file, reference=True, namespace="asset")
            referenced = "asset:ref_ctrl"
            visual = self._open_curve("reference_visual", 5)
            cmds.select(referenced, replace=True)
            self.feature.copy()
            cmds.select(visual, replace=True)
            with self.assertRaises(UnsupportedShapeError):
                self.feature.paste_replace()
            self.assertTrue(cmds.objExists(visual))
            self.assertTrue(cmds.objExists(referenced))

    def test_color_session_rolls_back_and_committed_color_is_undoable(self):
        controller = self._open_curve("color_ctrl")
        shape = nurbs_curve_shapes(controller)[0]
        cmds.select(controller, replace=True)
        feature = ColorFeature(
            self.state, self.selection, ColorService(), self.scene
        )
        original = ColorService().capture(shape)
        feature.begin_edit()
        feature.update_preview(ColorValue.rgb_color((1.0, 0.0, 0.0)))
        feature.rollback()
        self.assertEqual(ColorService().capture(shape), original)

        feature.begin_edit()
        feature.update_preview(ColorValue.rgb_color((0.0, 1.0, 0.0)))
        feature.commit()
        self.assertAlmostEqual(ColorService().capture(shape).rgb[1], 1.0)
        cmds.undo()
        self.assertEqual(ColorService().capture(shape), original)
        cmds.redo()
        self.assertAlmostEqual(ColorService().capture(shape).rgb[1], 1.0)

    def test_transform_preview_rolls_back_and_commit_is_undoable(self):
        controller = self._open_curve("preview_ctrl")
        cmds.select(controller, replace=True)
        transform = TransformFeature(self.state, self.selection, self.scene)
        preview = PreviewFeature(self.state, self.selection, self.scene)
        transform.has_active_preview = lambda: preview.is_active
        transform.commit_preview = preview.commit
        before = cmds.exactWorldBoundingBox(controller)
        self.state.values.scale = (1.0, 2.0, 1.0)
        preview.begin()
        changed = cmds.exactWorldBoundingBox(controller)
        self.assertNotEqual(before, changed)
        preview.rollback()
        self.assertEqual(cmds.exactWorldBoundingBox(controller), before)

        preview.begin()
        transform.apply()
        committed = cmds.exactWorldBoundingBox(controller)
        self.assertNotEqual(committed, before)
        cmds.undo()
        self.assertEqual(cmds.exactWorldBoundingBox(controller), before)


if __name__ == "__main__":
    unittest.main()
