"""Tests that run with standard Python and no Maya installation."""

import unittest

from rig_ctrl_shape_tool.core.domain import ColorValue, SessionStatus, TransformValues
from rig_ctrl_shape_tool.core.errors import EditSessionError
from rig_ctrl_shape_tool.core.sessions import EditSessionLifecycle
from rig_ctrl_shape_tool.core.state import ToolState
from rig_ctrl_shape_tool.core.transform_math import isolated_transform_values
from rig_ctrl_shape_tool.features.controls import ControlsFeature
from rig_ctrl_shape_tool.features.direct_edit import DirectEditFeature
from rig_ctrl_shape_tool.features.preview import PreviewFeature
from rig_ctrl_shape_tool.features.transform import TransformFeature


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
    def test_line_width_reset_uses_normal_visible_width(self) -> None:
        state = ToolState()
        controls = ControlsFeature(state)
        controls.update("line_width", (3.0,))

        controls.reset("line_width")

        self.assertEqual(state.values.line_width, 1.0)
        self.assertTrue(state.line_width_dirty)

    def test_direct_edit_reselects_controller_and_rebases_values(self) -> None:
        class Selection:
            def controllers(self):
                return ["ctrl"]

            def controller_cvs(self, _controller):
                return ["ctrlShape.cv[0]", "ctrlShape.cv[1]"]

        class Scene:
            def __init__(self):
                self.entered = []
                self.left = []

            def enter_component_edit(self, cvs):
                self.entered = list(cvs)

            def leave_component_edit(self, controllers):
                self.left = list(controllers)

            def exists(self, _node):
                return True

        scene = Scene()
        feature = DirectEditFeature(Selection(), scene)
        events = []
        feature.cancel_preview = lambda: events.append("preview")
        feature.cancel_color = lambda: events.append("color")
        feature.rebase_values = lambda: events.append("rebase")

        feature.set_enabled(True)
        self.assertTrue(feature.is_active)
        self.assertEqual(scene.entered, ["ctrlShape.cv[0]", "ctrlShape.cv[1]"])
        feature.set_enabled(False)

        self.assertFalse(feature.is_active)
        self.assertEqual(scene.left, ["ctrl"])
        self.assertEqual(events, ["color", "preview", "rebase"])

    def test_direct_edit_stays_active_and_follows_controller_selection(self) -> None:
        class Selection:
            current = ["first"]

            def controllers(self):
                return list(self.current)

            def controller_cvs(self, controller):
                return [f"{controller}Shape.cv[0]"]

        class Scene:
            def __init__(self):
                self.selections = []

            def enter_component_edit(self, cvs):
                self.selections.append(list(cvs))

            def leave_component_edit(self, _controllers):
                return None

            def exists(self, _node):
                return True

        selection = Selection()
        scene = Scene()
        feature = DirectEditFeature(selection, scene)
        feature.begin()
        selection.current = ["second"]

        self.assertTrue(feature.retarget_selection())
        self.assertTrue(feature.is_active)
        self.assertEqual(
            scene.selections,
            [["firstShape.cv[0]"], ["secondShape.cv[0]"]],
        )

        selection.current = []
        self.assertFalse(feature.retarget_selection())
        self.assertTrue(feature.is_active)

    def test_direct_edit_double_click_cycles_to_next_shape(self) -> None:
        class Selection:
            def controllers(self):
                return ["ctrl"]

            def controller_cvs(self, _controller):
                return ["first.cv[0]", "second.cv[0]"]

            def curve_shapes(self, _controller):
                return ["first", "second"]

            def selected_component_shapes(self):
                return ["first"]

            def shape_cvs(self, shape):
                return [f"{shape}.cv[0]", f"{shape}.cv[1]"]

        class Scene:
            def __init__(self):
                self.selections = []

            def enter_component_edit(self, cvs):
                self.selections.append(list(cvs))

            def pointer_is_over_viewport(self):
                return True

        scene = Scene()
        feature = DirectEditFeature(Selection(), scene)
        feature.begin()

        self.assertTrue(feature.select_next_shape())
        self.assertEqual(scene.selections[-1], ["second.cv[0]", "second.cv[1]"])

    def test_direct_edit_double_click_reselects_single_shape_after_deselect(self) -> None:
        class Selection:
            def controllers(self):
                return ["ctrl"]

            def controller_cvs(self, _controller):
                return ["shape.cv[0]", "shape.cv[1]"]

            def curve_shapes(self, _controller):
                return ["shape"]

            def selected_component_shapes(self):
                return []

            def shape_cvs(self, shape):
                return [f"{shape}.cv[0]", f"{shape}.cv[1]"]

        class Scene:
            def __init__(self):
                self.selections = []

            def enter_component_edit(self, cvs):
                self.selections.append(list(cvs))

            def pointer_is_over_viewport(self):
                return True

        scene = Scene()
        feature = DirectEditFeature(Selection(), scene)
        feature.begin()
        scene.selections.clear()

        self.assertTrue(feature.select_next_shape())
        self.assertEqual(scene.selections, [["shape.cv[0]", "shape.cv[1]"]])

    def test_preview_stays_enabled_after_commit(self) -> None:
        state = ToolState()
        preview = PreviewFeature(state, object(), object())
        state.preview.lifecycle.begin()

        preview.commit()

        self.assertTrue(preview.is_enabled)
        self.assertFalse(preview.is_active)

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
        for intermediate, final in ((1.5, 2.0), (2.5, 3.0), (3.5, 4.0)):
            controls.begin_preview_edit()
            controls.update("scale", (intermediate,) * 3)
            controls.update("scale", (final,) * 3)
            controls.end_preview_edit()

        self.assertEqual(len(state.preview.value_undo_stack), 3)

        self.assertTrue(preview.undo_uncommitted())
        self.assertEqual(state.values.scale, (3.0, 3.0, 3.0))
        self.assertTrue(preview.undo_uncommitted())
        self.assertEqual(state.values.scale, (2.0, 2.0, 2.0))
        self.assertTrue(preview.undo_uncommitted())
        self.assertEqual(state.values.scale, (1.0, 1.0, 1.0))
        self.assertTrue(state.preview.enabled)
        self.assertTrue(preview.is_active)
        self.assertTrue(preview.redo_uncommitted())
        self.assertEqual(state.values.scale, (2.0, 2.0, 2.0))
        self.assertTrue(preview.redo_uncommitted())
        self.assertEqual(state.values.scale, (3.0, 3.0, 3.0))
        self.assertTrue(preview.redo_uncommitted())
        self.assertEqual(state.values.scale, (4.0, 4.0, 4.0))

    def test_preview_enabled_after_edits_keeps_their_undo_history(self) -> None:
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
        controls = ControlsFeature(state)
        controls.update("scale", (2.0, 2.0, 2.0))
        controls.update("scale", (3.0, 3.0, 3.0))
        preview = PreviewFeature(state, Selection(), Scene())
        controls.changed = preview.update_preview

        preview.begin()
        self.assertTrue(preview.undo_uncommitted())

        self.assertEqual(state.values.scale, (2.0, 2.0, 2.0))
        self.assertTrue(preview.is_active)

    def test_preview_disabled_keeps_input_undo_without_scene_refresh(self) -> None:
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
            def __init__(self):
                self.set_position_calls = 0

            def cv_position(self, _cv):
                return (0.0, 0.0, 0.0)

            def open_undo(self, _name):
                return None

            def close_undo(self):
                return None

            def exists(self, _node):
                return True

            def set_cv_position(self, _cv, _position):
                self.set_position_calls += 1

            def warning(self, _message, _error=None):
                return None

        state = ToolState()
        scene = Scene()
        preview = PreviewFeature(state, Selection(), scene)
        controls = ControlsFeature(state)
        controls.changed = preview.update_preview

        preview.begin()
        controls.update("scale", (2.0, 2.0, 2.0))
        preview.set_enabled(False)
        restore_calls_after_disable = scene.set_position_calls

        self.assertFalse(preview.is_active)
        self.assertTrue(preview.undo_uncommitted())
        self.assertEqual(state.values.scale, (1.0, 1.0, 1.0))
        self.assertEqual(scene.set_position_calls, restore_calls_after_disable)
        self.assertTrue(preview.redo_uncommitted())
        self.assertEqual(state.values.scale, (2.0, 2.0, 2.0))
        self.assertEqual(scene.set_position_calls, restore_calls_after_disable)
        self.assertFalse(preview.redo_uncommitted())

    def test_rotate_90_button_creates_one_preview_undo_step(self) -> None:
        state = ToolState()
        controls = ControlsFeature(state)
        transform = TransformFeature(state, object(), object())
        transform.before_value_change = controls.capture_preview_value

        transform.rotate_y_90()
        transform.rotate_y_90()
        transform.rotate_y_90()

        self.assertEqual(state.values.rotate, (0.0, 270.0, 0.0))
        self.assertEqual(len(state.preview.value_undo_stack), 3)


if __name__ == "__main__":
    unittest.main()
