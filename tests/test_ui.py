"""Headless PySide6 regression tests for interaction details."""

from __future__ import annotations

import os
import unittest
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtGui, QtTest, QtWidgets

from rig_ctrl_shape_tool.app import _find_existing_window
from rig_ctrl_shape_tool.core.errors import InvalidSelectionError
from rig_ctrl_shape_tool.ui.color_dialog import ColorPreviewDialog
from rig_ctrl_shape_tool.ui.controls import DigitAwareDoubleSpinBox, NumericControl
from rig_ctrl_shape_tool.ui.window import RigCtrlShapeWindow


class UiInteractionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def test_context_menu_identifies_one_axis(self) -> None:
        control = NumericControl((1.0, 1.0, 1.0), (0.0, 10.0), context_label="Scale")
        menu, apply_action, reset_action = control._create_context_menu("Scale Y", 1.0)
        self.assertEqual(menu.actions()[0].text(), "対象：Scale Y")
        self.assertEqual(apply_action.text(), "適用  Scale Y")
        self.assertEqual(reset_action.text(), "リセット  Scale Y  (1.0000)")

    def test_digit_step_follows_cursor_place(self) -> None:
        field = DigitAwareDoubleSpinBox()
        field.setDecimals(4)
        field.setValue(123.4567)
        editor = field.lineEdit()
        editor.setText("123.4567")
        self.assertEqual(field._step_for_position(1), 100.0)
        self.assertEqual(field._step_for_position(2), 10.0)
        self.assertEqual(field._step_for_position(3), 1.0)
        self.assertAlmostEqual(field._step_for_position(5), 0.1)
        self.assertAlmostEqual(field._step_for_position(8), 0.0001)

    def test_spinbox_value_change_emits_without_losing_focus(self) -> None:
        control = NumericControl(
            (1.0, 1.0, 1.0),
            (0.0, 10.0),
            context_label="Scale",
        )
        changes = []
        control.valuesChanged.connect(changes.append)

        control.fields[1].setValue(2.5)

        self.assertEqual(changes, [(1.0, 2.5, 1.0)])
        self.assertEqual(
            control.sliders[1].value(),
            round(2.5 * control._SLIDER_FACTOR),
        )

    def test_field_edit_does_not_rewrite_text_or_move_caret(self) -> None:
        control = NumericControl((0.0,), (-10.0, 10.0), context_label="Move")
        field = control.fields[0]
        editor = field.lineEdit()
        editor.setText("2.0000")
        editor.setCursorPosition(0)

        control._from_fields()

        self.assertEqual(editor.text(), "2.0000")
        self.assertEqual(editor.cursorPosition(), 0)
        self.assertEqual(
            control.sliders[0].value(),
            round(2.0 * control._SLIDER_FACTOR),
        )

    def test_decimal_key_is_claimed_from_maya_shortcuts(self) -> None:
        field = DigitAwareDoubleSpinBox()
        editor = field.lineEdit()
        event = QtGui.QKeyEvent(
            QtCore.QEvent.Type.ShortcutOverride,
            QtCore.Qt.Key.Key_Period,
            QtCore.Qt.KeyboardModifier.NoModifier,
            ".",
        )

        QtWidgets.QApplication.sendEvent(editor, event)

        self.assertTrue(event.isAccepted())

    def test_decimal_typed_at_start_replaces_existing_value(self) -> None:
        field = DigitAwareDoubleSpinBox()
        field.setDecimals(4)
        editor = field.lineEdit()
        editor.setCursorPosition(0)

        QtTest.QTest.keyClicks(editor, ".25")

        self.assertAlmostEqual(field.value(), 0.25)

    def test_typing_over_fractional_digit_replaces_it(self) -> None:
        field = DigitAwareDoubleSpinBox()
        field.setDecimals(4)
        editor = field.lineEdit()
        editor.setCursorPosition(2)

        QtTest.QTest.keyClick(editor, QtCore.Qt.Key.Key_7)

        self.assertEqual(editor.text(), "0.7000")
        self.assertAlmostEqual(field.value(), 0.7)

    def test_typing_at_fractional_end_replaces_last_digit(self) -> None:
        field = DigitAwareDoubleSpinBox()
        field.setDecimals(4)
        editor = field.lineEdit()
        editor.setCursorPosition(len(editor.text()))

        QtTest.QTest.keyClick(editor, QtCore.Qt.Key.Key_7)

        self.assertEqual(editor.text(), "0.0007")
        self.assertAlmostEqual(field.value(), 0.0007)

    def test_existing_decimal_key_moves_to_fractional_part(self) -> None:
        field = DigitAwareDoubleSpinBox()
        field.setDecimals(4)
        editor = field.lineEdit()
        editor.setCursorPosition(len(editor.text()))

        QtTest.QTest.keyClick(editor, QtCore.Qt.Key.Key_Period)

        self.assertEqual(editor.cursorPosition(), 2)

    def test_first_click_focus_selects_the_existing_value(self) -> None:
        other = QtWidgets.QLineEdit()
        field = DigitAwareDoubleSpinBox()
        container = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(container)
        layout.addWidget(other)
        layout.addWidget(field)
        container.show()
        other.setFocus()
        self.app.processEvents()

        QtTest.QTest.mouseClick(field.lineEdit(), QtCore.Qt.MouseButton.LeftButton)
        self.app.processEvents()

        self.assertEqual(field.lineEdit().selectedText(), field.lineEdit().text())
        container.close()

    def test_joint_size_default_is_at_slider_center(self) -> None:
        control = NumericControl(
            (1.0,), (0.0, 30.0),
            context_label="Joint Size", slider_center=1.0,
        )
        slider = control.sliders[0]
        self.assertEqual(slider.value(), 0)
        slider.setValue(slider.minimum())
        self.assertEqual(control.fields[0].value(), 0.0)
        slider.setValue(slider.maximum())
        self.assertEqual(control.fields[0].value(), 30.0)

    def test_color_dialog_has_current_colors_and_explicit_actions(self) -> None:
        colors = (("yellow_ctrl", QtGui.QColor("yellow")),
                  ("red_ctrl", QtGui.QColor("red")),
                  ("blue_ctrl", QtGui.QColor("blue")))
        dialog = ColorPreviewDialog(QtGui.QColor("yellow"), colors)
        dialog.show()
        self.app.processEvents()
        swatches = [
            button
            for button in dialog.current_colors.findChildren(QtWidgets.QToolButton)
            if button.isVisible()
        ]
        labels = {button.text() for button in dialog.findChildren(QtWidgets.QPushButton)}
        self.assertEqual([button.toolTip() for button in swatches], [item[0] for item in colors])
        self.assertTrue({"適用", "キャンセル"}.issubset(labels))
        self.assertFalse(dialog.isModal())
        self.assertEqual(
            dialog.windowModality(), QtCore.Qt.WindowModality.NonModal
        )
        updated = (
            ("green_ctrl", QtGui.QColor("green")),
            ("cyan_ctrl", QtGui.QColor("cyan")),
        )
        dialog.set_current_colors(updated)
        self.app.processEvents()
        swatches = [
            button
            for button in dialog.current_colors.findChildren(QtWidgets.QToolButton)
            if button.isVisible()
        ]
        self.assertEqual(
            [button.toolTip() for button in swatches],
            [item[0] for item in updated],
        )
        previewed = []
        dialog.colorPreviewed.connect(previewed.append)
        swatches[1].click()
        self.assertEqual(previewed[-1].name(), QtGui.QColor("cyan").name())
        self.assertEqual(dialog.picker.currentColor().name(), QtGui.QColor("cyan").name())
        dialog.close()

    def test_custom_color_context_menu_uses_japanese_labels(self) -> None:
        dialog = ColorPreviewDialog(QtGui.QColor("white"), ())
        menu, edit, remove = dialog._create_custom_menu()
        self.assertEqual(edit.text(), "編集")
        self.assertEqual(remove.text(), "削除")
        menu.close()
        dialog.close()

    def test_existing_top_level_window_is_found(self) -> None:
        window = QtWidgets.QWidget()
        window.setObjectName("RigCtrlShapeTool")
        window.show()
        self.app.processEvents()
        self.assertIs(_find_existing_window(None), window)
        window.close()

    def test_main_window_emits_closing_once(self) -> None:
        noop = lambda *args, **kwargs: None
        transform = SimpleNamespace(
            rotate_x_90=noop, rotate_y_90=noop, rotate_z_90=noop,
            apply=noop, apply_value=noop,
        )
        preview = SimpleNamespace(
            set_enabled=noop, refresh=noop, is_enabled=False,
        )
        color = SimpleNamespace(
            begin_edit=noop, reset=noop,
            update_preview=noop, commit=noop, rollback=noop,
            get_current_view_data=noop,
        )
        copy_paste = SimpleNamespace(copy=noop, paste_replace=noop, paste_add=noop)
        disconnect = SimpleNamespace(disconnect_selected=noop)
        controls = SimpleNamespace(
            update=noop, reset=noop, reset_all=noop, reset_axis=noop,
            current_values=noop, begin_preview_edit=noop, end_preview_edit=noop,
        )
        shape_library = SimpleNamespace(show=noop)
        window = RigCtrlShapeWindow(
            transform, preview, color, copy_paste, disconnect, controls,
            shape_library,
        )
        emissions = []
        window.closing.connect(lambda: emissions.append(True))
        window.show()
        self.app.processEvents()
        window.close()
        self.app.processEvents()
        self.assertEqual(emissions, [True])

    def test_direct_edit_checkbox_is_right_of_preview_and_toggles_mode(self) -> None:
        noop = lambda *args, **kwargs: None
        toggles = []
        window = RigCtrlShapeWindow(
            SimpleNamespace(rotate_x_90=noop, rotate_y_90=noop,
                            rotate_z_90=noop, apply=noop, apply_value=noop),
            SimpleNamespace(set_enabled=noop, refresh=noop, is_enabled=False),
            SimpleNamespace(begin_edit=noop, reset=noop, update_preview=noop,
                            commit=noop, rollback=noop, get_current_view_data=noop),
            SimpleNamespace(copy=noop, paste_replace=noop, paste_add=noop),
            SimpleNamespace(disconnect_selected=noop),
            SimpleNamespace(update=noop, reset=noop, reset_all=noop,
                            reset_axis=noop, current_values=lambda: SimpleNamespace(
                                uniform=1.0, scale=(1.0, 1.0, 1.0),
                                rotate=(0.0, 0.0, 0.0), move=(0.0, 0.0, 0.0),
                                line_width=1.0, joint_size=1.0),
                            begin_preview_edit=noop, end_preview_edit=noop),
            SimpleNamespace(show=noop),
            SimpleNamespace(set_enabled=toggles.append),
        )
        checkbox = window.findChild(QtWidgets.QCheckBox, "directEditCheckBox")
        self.assertIsNotNone(checkbox)
        self.assertTrue(checkbox.isEnabled())

        checkbox.setChecked(True)
        checkbox.setChecked(False)

        self.assertEqual(toggles, [True, False])
        window.close()

    def test_shape_library_button_is_compact_and_launches_window(self) -> None:
        noop = lambda *args, **kwargs: None
        launched = []
        transform = SimpleNamespace(
            rotate_x_90=noop, rotate_y_90=noop, rotate_z_90=noop,
            apply=noop, apply_value=noop,
        )
        preview = SimpleNamespace(set_enabled=noop, refresh=noop, is_enabled=False)
        color = SimpleNamespace(begin_edit=noop, reset=noop, update_preview=noop,
                                commit=noop, rollback=noop, get_current_view_data=noop)
        copy_paste = SimpleNamespace(copy=noop, paste_replace=noop, paste_add=noop)
        disconnect = SimpleNamespace(disconnect_selected=noop)
        controls = SimpleNamespace(update=noop, reset=noop, reset_all=noop,
                                   reset_axis=noop, current_values=noop,
                                   begin_preview_edit=noop, end_preview_edit=noop)
        shape_library = SimpleNamespace(show=lambda: launched.append(True))
        window = RigCtrlShapeWindow(
            transform, preview, color, copy_paste, disconnect, controls,
            shape_library,
        )
        button = window.findChild(QtWidgets.QPushButton, "shapeLibraryButton")
        self.assertIsNotNone(button)
        color_button = window.findChild(QtWidgets.QPushButton, "pickColorButton")
        self.assertIsNotNone(color_button)
        self.assertEqual(button.height(), color_button.height())
        self.assertEqual(button.styleSheet(), color_button.styleSheet())
        button.click()
        self.assertEqual(launched, [True])
        window.close()

    def test_color_picker_opens_without_a_controller_selection(self) -> None:
        noop = lambda *args, **kwargs: None
        color = SimpleNamespace(
            begin_edit=lambda: (_ for _ in ()).throw(
                InvalidSelectionError("no controller")
            ),
            reset=noop, update_preview=noop, commit=noop, rollback=noop,
            get_current_view_data=lambda: (_ for _ in ()).throw(
                InvalidSelectionError("no controller")
            ),
            is_active=False,
        )
        window = RigCtrlShapeWindow(
            SimpleNamespace(rotate_x_90=noop, rotate_y_90=noop,
                            rotate_z_90=noop, apply=noop, apply_value=noop),
            SimpleNamespace(set_enabled=noop, refresh=noop, is_enabled=False),
            color,
            SimpleNamespace(copy=noop, paste_replace=noop, paste_add=noop),
            SimpleNamespace(disconnect_selected=noop),
            SimpleNamespace(update=noop, reset=noop, reset_all=noop,
                            reset_axis=noop, current_values=noop,
                            begin_preview_edit=noop, end_preview_edit=noop),
            SimpleNamespace(show=noop),
        )

        window.findChild(QtWidgets.QPushButton, "pickColorButton").click()
        self.app.processEvents()

        self.assertIsNotNone(window._color_dialog)
        self.assertTrue(window._color_dialog.isVisible())
        window.close()

    def test_selection_change_retargets_real_time_preview(self) -> None:
        noop = lambda *args, **kwargs: None
        preview_updates = []
        color = SimpleNamespace(
            begin_edit=noop, reset=noop, update_preview=noop,
            commit=noop, rollback=noop,
            get_current_view_data=lambda: (_ for _ in ()).throw(
                InvalidSelectionError("no controller")
            ),
        )
        window = RigCtrlShapeWindow(
            SimpleNamespace(rotate_x_90=noop, rotate_y_90=noop,
                            rotate_z_90=noop, apply=noop, apply_value=noop),
            SimpleNamespace(set_enabled=noop,
                            update_preview=lambda: preview_updates.append(True),
                            is_enabled=True),
            color,
            SimpleNamespace(copy=noop, paste_replace=noop, paste_add=noop),
            SimpleNamespace(disconnect_selected=noop),
            SimpleNamespace(update=noop, reset=noop, reset_all=noop,
                            reset_axis=noop, current_values=noop,
                            begin_preview_edit=noop, end_preview_edit=noop),
            SimpleNamespace(show=noop),
        )

        window.handle_selection_changed()

        self.assertEqual(preview_updates, [True])
        window.close()

    def test_disconnect_passes_keep_name_choice_to_feature(self) -> None:
        noop = lambda *args, **kwargs: None
        choices = []
        window = RigCtrlShapeWindow(
            SimpleNamespace(rotate_x_90=noop, rotate_y_90=noop,
                            rotate_z_90=noop, apply=noop, apply_value=noop),
            SimpleNamespace(set_enabled=noop, update_preview=noop,
                            is_enabled=False),
            SimpleNamespace(begin_edit=noop, reset=noop, update_preview=noop,
                            commit=noop, rollback=noop,
                            get_current_view_data=noop),
            SimpleNamespace(copy=noop, paste_replace=noop, paste_add=noop),
            SimpleNamespace(disconnect_selected=choices.append),
            SimpleNamespace(update=noop, reset=noop, reset_all=noop,
                            reset_axis=noop, current_values=noop,
                            begin_preview_edit=noop, end_preview_edit=noop),
            SimpleNamespace(show=noop),
        )
        window._confirm_disconnect_name = lambda: False

        window._disconnect()

        self.assertEqual(choices, [False])
        window.setObjectName("")
        window.close()


if __name__ == "__main__":
    unittest.main()
