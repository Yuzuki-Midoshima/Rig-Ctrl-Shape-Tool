"""Tests that run with standard Python and no Maya installation."""

import unittest

from rig_ctrl_shape_tool.core.domain import ColorValue, SessionStatus, TransformValues
from rig_ctrl_shape_tool.core.errors import EditSessionError
from rig_ctrl_shape_tool.core.sessions import EditSessionLifecycle
from rig_ctrl_shape_tool.core.state import ToolState
from rig_ctrl_shape_tool.core.transform_math import isolated_transform_values
from rig_ctrl_shape_tool.features.controls import ControlsFeature


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


if __name__ == "__main__":
    unittest.main()
