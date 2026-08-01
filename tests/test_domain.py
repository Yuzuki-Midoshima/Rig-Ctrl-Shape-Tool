"""Tests that run with standard Python and no Maya installation."""

import unittest

from rig_ctrl_shape_tool.core.domain import ColorValue, SessionStatus, TransformValues
from rig_ctrl_shape_tool.core.errors import EditSessionError
from rig_ctrl_shape_tool.core.sessions import EditSessionLifecycle
from rig_ctrl_shape_tool.core.state import ToolState
from rig_ctrl_shape_tool.core.transform_math import isolated_transform_values
from rig_ctrl_shape_tool.features.controls import ControlsFeature
from rig_ctrl_shape_tool.features.preview import PreviewFeature


class ColorLogicTests(unittest.TestCase):
    def test_rgb_is_clamped(self) -> None:
        self.assertEqual(ColorValue.rgb_color((-1.0, .5, 2.0)).rgb, (0.0, .5, 1.0))


class SessionTests(unittest.TestCase):
    def test_commit_requires_active_session(self) -> None:
        session = EditSessionLifecycle()
        with self.assertRaises(EditSessionError):
            session.commit()
        session.begin()
        session.commit()
        self.assertFalse(session.is_active)

    def test_second_begin_is_rejected(self) -> None:
        session = EditSessionLifecycle()
        session.begin()
        with self.assertRaises(EditSessionError):
            session.begin()

    def test_session_can_restart_after_rollback(self) -> None:
        session = EditSessionLifecycle()
        session.begin()
        session.rollback()
        self.assertEqual(session.status, SessionStatus.ROLLED_BACK)
        session.begin()
        session.commit()
        self.assertEqual(session.status, SessionStatus.COMMITTED)


class TransformLogicTests(unittest.TestCase):
    def test_context_apply_isolates_one_axis(self) -> None:
        current = TransformValues(scale=(2, 3, 4), rotate=(10, 20, 30), move=(5, 6, 7))
        isolated = isolated_transform_values(current, "scale", 1)
        self.assertEqual(isolated.scale, (1.0, 3, 1.0))
        self.assertEqual(isolated.rotate, (0.0, 0.0, 0.0))
        self.assertEqual(isolated.move, (0.0, 0.0, 0.0))

    def test_applied_values_follow_undo_and_redo(self) -> None:
        state = ToolState()
        controls = ControlsFeature(state)
        controls.update("scale", (2.0, 3.0, 4.0))
        controls.record_apply()

        self.assertTrue(controls.restore_undo_values())
        self.assertEqual(state.values.scale, (1.0, 1.0, 1.0))
        self.assertTrue(controls.restore_redo_values())
        self.assertEqual(state.values.scale, (2.0, 3.0, 4.0))

    def test_pre_apply_preview_undo_restores_initial_inputs(self) -> None:
        class Selection:
            def cvs(self):
                return ["curveShape.cv[0]"]

            def joints(self):
                return []

            def shapes(self):
                return []

            def controllers(self):
                return []

        class Scene:
            def cv_position(self, _cv):
                return (0.0, 0.0, 0.0)

            def open_undo(self, _name):
                return None

            def close_undo(self):
                return None

            def exists(self, _node):
                return True

            def set_cv_position(self, _cv, _position):
                return None

            def warning(self, _message, _error=None):
                return None

        state = ToolState()
        preview = PreviewFeature(state, Selection(), Scene())
        controls = ControlsFeature(state)
        controls.changed = preview.update_preview
        preview.begin()
        controls.update("scale", (2.0, 2.0, 2.0))
        controls.update("scale", (3.0, 3.0, 3.0))
        controls.update("scale", (4.0, 4.0, 4.0))

        self.assertTrue(preview.undo_uncommitted())
        self.assertEqual(state.values.scale, (3.0, 3.0, 3.0))
        self.assertTrue(preview.undo_uncommitted())
        self.assertEqual(state.values.scale, (2.0, 2.0, 2.0))
        self.assertTrue(state.preview.enabled)
        self.assertTrue(preview.is_active)
        self.assertTrue(preview.redo_uncommitted())
        self.assertEqual(state.values.scale, (3.0, 3.0, 3.0))
        self.assertTrue(preview.redo_uncommitted())
        self.assertEqual(state.values.scale, (4.0, 4.0, 4.0))


if __name__ == "__main__":
    unittest.main()
