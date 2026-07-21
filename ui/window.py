"""Main window: widgets, layout, and signal routing only."""

from __future__ import annotations

from collections.abc import Callable

from PySide6 import QtCore, QtGui, QtWidgets

from ..core.domain import ColorValue, ColorViewData
from ..core.errors import RigCtrlShapeToolError
from ..features import (
    ColorFeature,
    ControlsFeature,
    CopyPasteFeature,
    DisconnectFeature,
    PreviewFeature,
    TransformFeature,
)
from .controls import NumericControl
from .color_dialog import ColorPreviewDialog
from .color_swatches import CurrentColorsWidget
from .sections import SectionHeader
from .style import APPLY_STYLE, DISCONNECT_STYLE, FIELD_RANGES, RESET_STYLE


class RigCtrlShapeWindow(QtWidgets.QDialog):
    closing = QtCore.Signal()

    def __init__(self, transform: TransformFeature, preview: PreviewFeature,
                 color: ColorFeature, copy_paste: CopyPasteFeature, disconnect: DisconnectFeature,
                 controls: ControlsFeature, parent=None) -> None:
        super().__init__(parent)
        self.transform_feature = transform
        self.preview_feature = preview
        self.color_feature = color
        self.copy_paste_feature = copy_paste
        self.disconnect_feature = disconnect
        self.controls_feature = controls
        self.setObjectName("RigCtrlShapeTool")
        self.setWindowTitle("Rig Controller Shape Tool")
        self.setMinimumWidth(280)
        self._controls: dict[str, NumericControl] = {}
        self._color_dialog: ColorPreviewDialog | None = None
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(3)
        specs = (
            ("uniform", "Uniform Scale", (1.0,)),
            ("scale", "Scale", (1.0, 1.0, 1.0)),
            ("rotate", "Rotate", (0.0, 0.0, 0.0)),
            ("move", "Move", (0.0, 0.0, 0.0)),
            ("line_width", "Line Width", (0.0,)),
        )
        for key, label, defaults in specs:
            header = SectionHeader(label)
            root.addWidget(header)
            control = NumericControl(
                defaults,
                FIELD_RANGES[key],
                context_label=label,
            )
            root.addWidget(control)
            self._controls[key] = control
            header.resetClicked.connect(lambda key=key: self._reset(key))
            control.valuesChanged.connect(lambda values, key=key: self.controls_feature.update(key, values))
            control.applyRequested.connect(
                lambda axis, key=key: self._apply_context_value(key, axis)
            )
            control.resetRequested.connect(
                lambda axis, key=key: self._reset_context_value(key, axis)
            )
            if key == "rotate":
                row = QtWidgets.QHBoxLayout()
                callbacks = (
                    ("X +90", self.transform_feature.rotate_x_90),
                    ("Y +90", self.transform_feature.rotate_y_90),
                    ("Z +90", self.transform_feature.rotate_z_90),
                )
                for text, callback in callbacks:
                    button = QtWidgets.QPushButton(text)
                    button.clicked.connect(
                        lambda _=False, cb=callback: self._rotate(cb)
                    )
                    row.addWidget(button)
                root.addLayout(row)
            if key != "line_width":
                root.addWidget(self._separator())
        root.addWidget(self._separator())
        color_header = SectionHeader("Color")
        root.addWidget(color_header)
        color_header.resetClicked.connect(self._reset_color)
        root.addWidget(QtWidgets.QLabel("Current Colors"))
        self.color_row = CurrentColorsWidget(framed=False, parent=self)
        self.color_row.colorClicked.connect(self._reuse_color)
        root.addWidget(self.color_row)
        pick = QtWidgets.QPushButton("Pick Color")
        pick.setFixedHeight(28)
        pick.clicked.connect(self._pick_color)
        root.addWidget(pick)
        self.preview_box = QtWidgets.QCheckBox("Real Time Preview")
        self.preview_box.toggled.connect(self.preview_feature.set_enabled)
        root.addWidget(self.preview_box)
        apply = QtWidgets.QPushButton("Apply")
        apply.setFixedHeight(32)
        apply.setStyleSheet(APPLY_STYLE)
        apply.clicked.connect(self._apply)
        root.addWidget(apply)
        root.addWidget(QtWidgets.QLabel("Paste Mode"))
        modes = QtWidgets.QHBoxLayout()
        self.replace = QtWidgets.QRadioButton("Replace")
        self.replace.setChecked(True)
        self.add = QtWidgets.QRadioButton("Add")
        modes.addWidget(self.replace)
        modes.addWidget(self.add)
        root.addLayout(modes)
        actions = QtWidgets.QHBoxLayout()
        copy = QtWidgets.QPushButton("Copy Rig")
        paste = QtWidgets.QPushButton("Paste Rig")
        copy.clicked.connect(lambda: self._run_user_action(self.copy_paste_feature.copy))
        paste.clicked.connect(lambda: self._run_user_action(
            self.copy_paste_feature.paste_add
            if self.add.isChecked()
            else self.copy_paste_feature.paste_replace
        ))
        actions.addWidget(copy)
        actions.addWidget(paste)
        root.addLayout(actions)
        disc = QtWidgets.QPushButton("Disconnect All Nodes")
        disc.setFixedHeight(18)
        disc.setStyleSheet(DISCONNECT_STYLE)
        disc.clicked.connect(
            lambda: self._run_user_action(
                self.disconnect_feature.disconnect_selected
            )
        )
        root.addWidget(disc)
        reset = QtWidgets.QPushButton("Reset All Values")
        reset.setFixedHeight(32)
        reset.setStyleSheet(RESET_STYLE)
        reset.clicked.connect(self._reset_all)
        root.addWidget(reset)
        self.resize(280, self.sizeHint().height())

    @staticmethod
    def _separator() -> QtWidgets.QFrame:
        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        return line

    def _run_user_action(self, action: Callable[[], None]) -> None:
        try:
            action()
        except RigCtrlShapeToolError as error:
            QtWidgets.QMessageBox.warning(self, "Rig Controller Shape Tool", str(error))
        except (RuntimeError, ValueError) as error:
            QtWidgets.QMessageBox.warning(self, "Rig Controller Shape Tool", str(error))

    def _reset(self, key: str) -> None:
        self.controls_feature.reset(key)
        self.sync_values()

    def _reset_all(self) -> None:
        self.controls_feature.reset_all()
        self.sync_values()

    def _reset_axis(self, group: str, axis: int) -> None:
        self.controls_feature.reset_axis(group, axis)
        self.sync_values()

    def _reset_context_value(self, group: str, axis: int) -> None:
        if group in ("uniform", "line_width"):
            self._reset(group)
        else:
            self._reset_axis(group, axis)

    def _apply_context_value(self, group: str, axis: int) -> None:
        if self.preview_feature.is_enabled:
            self.preview_box.setChecked(False)
        self._run_user_action(lambda: self.transform_feature.apply_value(group, axis))

    def _rotate(self, callback: Callable[[], None]) -> None:
        callback()
        self.sync_values()
        self.preview_feature.update_preview()

    def _apply(self) -> None:
        self._run_user_action(self.transform_feature.apply)
        self.preview_box.setChecked(False)

    def _pick_color(self) -> None:
        if self._color_dialog and self._color_dialog.isVisible():
            self._color_dialog.raise_()
            self._color_dialog.activateWindow()
            return
        if self.preview_feature.is_enabled:
            self.preview_box.setChecked(False)
        try:
            view_data = self.color_feature.begin_edit()
        except RigCtrlShapeToolError as error:
            QtWidgets.QMessageBox.warning(self, "Rig Controller Shape Tool", str(error))
            return
        self._open_color_dialog(view_data)

    def _reset_color(self) -> None:
        restored = self.color_feature.reset()
        if restored is not None and self._color_dialog:
            self._color_dialog.set_preview_color(self._to_qcolor(restored))

    def _open_color_dialog(self, view_data: ColorViewData) -> None:
        colors = [(swatch.controller, self._to_qcolor(swatch.color))
                  for swatch in view_data.current_colors]
        try:
            dialog = ColorPreviewDialog(self._to_qcolor(view_data.initial_color), colors, self)
            self._color_dialog = dialog
            dialog.colorPreviewed.connect(
                lambda color: self.color_feature.update_preview(self._from_qcolor(color))
            )
            dialog.finished.connect(self._finish_color_dialog)
            dialog.place_next_to(self)
            # QDialog.open() enforces window modality even when setModal(False)
            # was requested. show() keeps Maya interactive during color preview.
            dialog.show()
        except Exception:
            self.color_feature.rollback()
            self._color_dialog = None
            raise

    def _finish_color_dialog(self, result: int) -> None:
        if result == QtWidgets.QDialog.DialogCode.Accepted:
            self.color_feature.commit()
        else:
            self.color_feature.rollback()
        self._color_dialog = None

    def sync_values(self) -> None:
        values = self.controls_feature.current_values()
        for key, control in self._controls.items():
            value = getattr(values, key)
            control.set_values((value,) if isinstance(value, float) else value)

    def refresh_colors(self) -> None:
        try:
            view_data = self.color_feature.get_current_view_data()
        except RigCtrlShapeToolError:
            self.color_row.set_colors(())
            return
        self.color_row.set_colors(tuple(
            (swatch.controller, self._to_qcolor(swatch.color))
            for swatch in view_data.current_colors
        ))

    def handle_color_state_changed(self) -> None:
        """Refresh color data and close a dialog after external rollback."""
        self.refresh_colors()
        if (
            self._color_dialog
            and self._color_dialog.isVisible()
            and not self.color_feature.is_active
        ):
            self._color_dialog.reject()

    def _reuse_color(self, color: QtGui.QColor) -> None:
        if self._color_dialog and self._color_dialog.isVisible():
            self._color_dialog.select_color(color)
            return
        if self.preview_feature.is_enabled:
            self.preview_box.setChecked(False)
        try:
            view_data = self.color_feature.begin_edit()
        except RigCtrlShapeToolError:
            return
        if view_data:
            self._open_color_dialog(view_data)
            if self._color_dialog:
                self._color_dialog.select_color(color)

    @staticmethod
    def _to_qcolor(value: ColorValue) -> QtGui.QColor:
        return QtGui.QColor.fromRgbF(*(value.rgb or (0.0, 0.0, 0.0)))

    @staticmethod
    def _from_qcolor(value: QtGui.QColor) -> ColorValue:
        return ColorValue.rgb_color((value.redF(), value.greenF(), value.blueF()))

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        if self._color_dialog:
            self._color_dialog.reject()
        self.closing.emit()
        super().closeEvent(event)
