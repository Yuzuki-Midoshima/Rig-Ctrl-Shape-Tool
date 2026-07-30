"""Headless PySide6 regression tests for interaction details."""

from __future__ import annotations

import os
import unittest
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtGui, QtWidgets

from rig_ctrl_shape_tool.app import _find_existing_window
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
        self.assertEqual(menu.actions()[0].text(), "Target : Scale Y")
        self.assertEqual(apply_action.text(), "APPLY  Scale Y")
        self.assertEqual(reset_action.text(), "RESET  Scale Y  (1.0000)")

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
        self.assertTrue({"Apply", "Cancel"}.issubset(labels))
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
            current_values=noop,
        )
        window = RigCtrlShapeWindow(
            transform, preview, color, copy_paste, disconnect, controls
        )
        emissions = []
        window.closing.connect(lambda: emissions.append(True))
        window.show()
        self.app.processEvents()
        window.close()
        self.app.processEvents()
        self.assertEqual(emissions, [True])


if __name__ == "__main__":
    unittest.main()
