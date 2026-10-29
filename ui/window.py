"""Main window: widgets, layout, and signal routing only."""

from __future__ import annotations

from collections.abc import Callable

from PySide6 import QtCore, QtGui, QtWidgets

from ..core.domain import ColorValue, ColorViewData
from ..core.errors import InvalidSelectionError, RigCtrlShapeToolError
from ..features import (
    ColorFeature,
    ControlsFeature,
    CopyPasteFeature,
    DisconnectFeature,
    DirectEditFeature,
    PreviewFeature,
    TransformFeature,
)
from ..services import ShapeLibraryService
from .controls import NumericControl
from .color_dialog import ColorPreviewDialog
from .color_swatches import CurrentColorsWidget
from .sections import SectionHeader
from .style import (
    APPLY_STYLE,
    DISCONNECT_STYLE,
    FIELD_RANGES,
    RESET_STYLE,
    WINDOW_LAUNCH_STYLE,
)


class RigCtrlShapeWindow(QtWidgets.QDialog):
    closing = QtCore.Signal()
    _EMPTY_PICKER_COLOR = (100 / 255.0,) * 3

    def __init__(self, transform: TransformFeature, preview: PreviewFeature,
                 color: ColorFeature, copy_paste: CopyPasteFeature, disconnect: DisconnectFeature,
                 controls: ControlsFeature, shape_library: ShapeLibraryService,
                 direct_edit: DirectEditFeature | None = None, parent=None) -> None:
        super().__init__(parent)
        self.transform_feature = transform
        self.preview_feature = preview
        self.color_feature = color
        self.copy_paste_feature = copy_paste
        self.disconnect_feature = disconnect
        self.controls_feature = controls
        self.shape_library_service = shape_library
        self.direct_edit_feature = direct_edit
        self.setObjectName("RigCtrlShapeTool")
        self.setWindowTitle("リグコントローラーシェイプツール")
        self.setMinimumWidth(280)
        self._controls: dict[str, NumericControl] = {}
        self._color_dialog: ColorPreviewDialog | None = None
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(3)
        specs = (
            ("uniform", "均等スケール", (1.0,)),
            ("scale", "スケール", (1.0, 1.0, 1.0)),
            ("rotate", "回転", (0.0, 0.0, 0.0)),
            ("move", "移動", (0.0, 0.0, 0.0)),
            ("line_width", "ライン幅", (1.0,)),
            ("joint_size", "ジョイントサイズ", (1.0,)),
        )
        for key, label, defaults in specs:
            header = SectionHeader(label)
            root.addWidget(header)
            control = NumericControl(
                defaults,
                FIELD_RANGES[key],
                context_label=label,
                slider_center=defaults[0] if key == "joint_size" else None,
            )
            root.addWidget(control)
            self._controls[key] = control
            header.resetClicked.connect(lambda key=key: self._reset(key))
            control.valuesChanged.connect(lambda values, key=key: self.controls_feature.update(key, values))
            control.interactionStarted.connect(self.controls_feature.begin_preview_edit)
            control.interactionFinished.connect(self.controls_feature.end_preview_edit)
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
            if key != "joint_size":
                separator = self._separator()
                if key == "line_width":
                    # Keep this final numeric pair visually grouped while
                    # retaining the same divider used by every other section.
                    separator.setFixedHeight(1)
                root.addWidget(separator)
        root.addWidget(self._separator())
        compact_actions = QtWidgets.QVBoxLayout()
        compact_actions.setSpacing(1)
        self.preview_box = QtWidgets.QCheckBox("リアルタイムプレビュー")
        self.preview_box.toggled.connect(self.preview_feature.set_enabled)
        self.preview_box.setChecked(self.preview_feature.is_enabled)
        preview_modes = QtWidgets.QHBoxLayout()
        preview_modes.addWidget(self.preview_box)
        preview_modes.addStretch(1)
        self.direct_edit_box = QtWidgets.QCheckBox("直接編集")
        self.direct_edit_box.setObjectName("directEditCheckBox")
        self.direct_edit_box.setEnabled(self.direct_edit_feature is not None)
        self.direct_edit_box.toggled.connect(self._toggle_direct_edit)
        preview_modes.addWidget(self.direct_edit_box)
        compact_actions.addLayout(preview_modes)
        apply = QtWidgets.QPushButton("適用")
        apply.setFixedHeight(34)
        apply.setStyleSheet(APPLY_STYLE)
        apply.clicked.connect(self._apply)
        compact_actions.addWidget(apply)
        color_header = SectionHeader("カラー")
        compact_actions.addWidget(color_header)
        color_header.resetClicked.connect(self._reset_color)
        compact_actions.addWidget(QtWidgets.QLabel("現在のカラー"))
        self.color_row = CurrentColorsWidget(framed=False, parent=self)
        self.color_row.colorClicked.connect(self._reuse_color)
        compact_actions.addWidget(self.color_row)
        pick = QtWidgets.QPushButton("カラーを選択")
        pick.setObjectName("pickColorButton")
        pick.setFixedHeight(28)
        pick.setStyleSheet(WINDOW_LAUNCH_STYLE)
        pick.clicked.connect(self._pick_color)
        compact_actions.addWidget(pick)
        compact_actions.addWidget(QtWidgets.QLabel("シェイプ"))
        shape_library_button = QtWidgets.QPushButton("シェイプライブラリ")
        shape_library_button.setObjectName("shapeLibraryButton")
        shape_library_button.setFixedHeight(28)
        shape_library_button.setStyleSheet(WINDOW_LAUNCH_STYLE)
        shape_library_button.clicked.connect(
            lambda: self._run_user_action(self.shape_library_service.show)
        )
        compact_actions.addWidget(shape_library_button)
        compact_actions.addWidget(QtWidgets.QLabel("貼り付けモード"))
        root.addLayout(compact_actions)
        modes = QtWidgets.QHBoxLayout()
        self.replace = QtWidgets.QRadioButton("置き換え")
        self.replace.setChecked(True)
        self.add = QtWidgets.QRadioButton("追加")
        modes.addWidget(self.replace)
        modes.addWidget(self.add)
        root.addLayout(modes)
        actions = QtWidgets.QHBoxLayout()
        copy = QtWidgets.QPushButton("リグをコピー")
        paste = QtWidgets.QPushButton("リグをペースト")
        copy.clicked.connect(lambda: self._run_user_action(self.copy_paste_feature.copy))
        paste.clicked.connect(self._paste)
        actions.addWidget(copy)
        actions.addWidget(paste)
        root.addLayout(actions)
        disc = QtWidgets.QPushButton("すべてのノード接続を解除")
        disc.setFixedHeight(18)
        disc.setStyleSheet(DISCONNECT_STYLE)
        disc.clicked.connect(self._disconnect)
        root.addWidget(disc)
        reset = QtWidgets.QPushButton("すべての値をリセット")
        reset.setFixedHeight(32)
        reset.setStyleSheet(RESET_STYLE)
        reset.clicked.connect(self._reset_all)
        root.addWidget(reset)
        self.resize(280, self.sizeHint().height())
    def eventFilter(self, watched: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if (
            event.type() == QtCore.QEvent.Type.MouseButtonDblClick
            and self.direct_edit_feature
            and self.direct_edit_box.isChecked()
        ):
            QtCore.QTimer.singleShot(0, self._select_next_direct_edit_shape)
        return super().eventFilter(watched, event)

    def _select_next_direct_edit_shape(self) -> None:
        if self.direct_edit_feature and self.direct_edit_box.isChecked():
            try:
                self.direct_edit_feature.select_next_shape()
            except (RuntimeError, ValueError):
                pass

    @staticmethod
    def _separator() -> QtWidgets.QFrame:
        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        return line

    def _run_user_action(self, action: Callable[[], None]) -> None:
        try:
            action()
        except RigCtrlShapeToolError as error:
            QtWidgets.QMessageBox.warning(self, "リグコントローラーシェイプツール", str(error))
        except (RuntimeError, ValueError) as error:
            QtWidgets.QMessageBox.warning(self, "リグコントローラーシェイプツール", str(error))

    def _confirm(self, message: str) -> bool:
        buttons = (
            QtWidgets.QMessageBox.StandardButton.Yes
            | QtWidgets.QMessageBox.StandardButton.No
        )
        result = QtWidgets.QMessageBox.warning(
            self,
            "リグコントローラーシェイプツール",
            message,
            buttons,
            QtWidgets.QMessageBox.StandardButton.No,
        )
        return result == QtWidgets.QMessageBox.StandardButton.Yes

    def _paste(self) -> None:
        def action() -> None:
            if self.copy_paste_feature.paste_target_has_connections() and not self._confirm(
                "貼り付け先に接続があります。貼り付けを続行しますか？"
            ):
                return
            paste = (
                self.copy_paste_feature.paste_add
                if self.add.isChecked()
                else self.copy_paste_feature.paste_replace
            )
            paste()

        self._run_user_action(action)

    def _disconnect(self) -> None:
        rename_controller = self._confirm_disconnect_name()
        if rename_controller is None:
            return
        self._run_user_action(
            lambda: self.disconnect_feature.disconnect_selected(rename_controller)
        )

    def _confirm_disconnect_name(self) -> bool | None:
        """Ask whether Disconnect should normalize the controller's name."""
        dialog = QtWidgets.QMessageBox(self)
        dialog.setIcon(QtWidgets.QMessageBox.Icon.Warning)
        dialog.setWindowTitle("リグコントローラーシェイプツール")
        dialog.setText("選択したコントローラーから、すべてのノード接続を解除します。")
        dialog.setInformativeText("解除後のコントローラー名を選択してください。")
        rename_button = dialog.addButton(
            "controller に変更",
            QtWidgets.QMessageBox.ButtonRole.AcceptRole,
        )
        keep_button = dialog.addButton(
            "現在の名前を維持",
            QtWidgets.QMessageBox.ButtonRole.ActionRole,
        )
        cancel_button = dialog.addButton(QtWidgets.QMessageBox.StandardButton.Cancel)
        dialog.setDefaultButton(rename_button)
        dialog.setEscapeButton(cancel_button)
        dialog.exec()
        clicked = dialog.clickedButton()
        if clicked is rename_button:
            return True
        if clicked is keep_button:
            return False
        return None

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
        if group in ("uniform", "line_width", "joint_size"):
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

    def commit_active_preview(self) -> bool:
        """Commit visible CV edits before another tool changes transforms.

        Transform utilities such as Freeze Transformations can otherwise run
        while Preview still owns the original CV positions.  A later preview
        refresh would then restore that stale baseline over the frozen shape.
        """
        if not self.preview_feature.is_active:
            return False
        self.transform_feature.apply()
        return True

    def _toggle_direct_edit(self, enabled: bool) -> None:
        if self.direct_edit_feature is None:
            return
        if enabled and self.preview_box.isChecked():
            self.preview_box.setChecked(False)
        try:
            self.direct_edit_feature.set_enabled(enabled)
            application = QtWidgets.QApplication.instance()
            if application:
                if enabled:
                    # Process after Maya resolves the curve below the click.
                    application.installEventFilter(self)
                else:
                    application.removeEventFilter(self)
            if not enabled:
                self.sync_values()
        except RigCtrlShapeToolError as error:
            blocker = QtCore.QSignalBlocker(self.direct_edit_box)
            self.direct_edit_box.setChecked(not enabled)
            del blocker
            QtWidgets.QMessageBox.warning(self, "リグコントローラーシェイプツール", str(error))

    def _pick_color(self) -> None:
        if self._color_dialog and self._color_dialog.isVisible():
            self._color_dialog.raise_()
            self._color_dialog.activateWindow()
            return
        if self.preview_feature.is_enabled:
            self.preview_box.setChecked(False)
        try:
            view_data = self.color_feature.begin_edit()
        except InvalidSelectionError:
            # The picker is also useful before a controller is selected.  It
            # will attach to a valid curve through handle_selection_changed().
            view_data = ColorViewData(
                ColorValue.rgb_color(self._EMPTY_PICKER_COLOR), ()
            )
        except RigCtrlShapeToolError as error:
            QtWidgets.QMessageBox.warning(self, "リグコントローラーシェイプツール", str(error))
            return
        self._open_color_dialog(view_data)

    def _reset_color(self) -> None:
        restored = self.color_feature.reset()
        if restored is not None and self._color_dialog:
            self._color_dialog.set_preview_color(self._to_qcolor(restored))

    def _open_color_dialog(self, view_data: ColorViewData) -> None:
        colors = self._dialog_colors(view_data)
        try:
            dialog = ColorPreviewDialog(self._to_qcolor(view_data.initial_color), colors, self)
            self._color_dialog = dialog
            dialog.colorPreviewed.connect(self._preview_color)
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

    def _preview_color(self, color: QtGui.QColor) -> None:
        """Preview only after the picker has a controller edit session."""
        if self.color_feature.is_active:
            self.color_feature.update_preview(self._from_qcolor(color))

    def sync_values(self) -> None:
        values = self.controls_feature.current_values()
        for key, control in self._controls.items():
            value = getattr(values, key)
            control.set_values((value,) if isinstance(value, float) else value)

    def restore_undo_values(self) -> None:
        if self.controls_feature.restore_undo_values():
            self.sync_values()
        self.refresh_colors()

    def restore_uncommitted_preview(self) -> bool:
        if not self.preview_feature.undo_uncommitted():
            return False
        self.sync_values()
        self.refresh_colors()
        return True

    def restore_uncommitted_preview_redo(self) -> bool:
        if not self.preview_feature.redo_uncommitted():
            return False
        self.sync_values()
        self.refresh_colors()
        return True

    def restore_redo_values(self) -> None:
        if self.controls_feature.restore_redo_values():
            self.sync_values()
        self.refresh_colors()

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

    def handle_selection_changed(self) -> None:
        """Retarget persistent edit modes to Maya's current selection."""
        self.preview_feature.update_preview()
        if self.direct_edit_feature and self.direct_edit_box.isChecked():
            try:
                self.direct_edit_feature.retarget_selection()
            except (RuntimeError, ValueError):
                # SelectionChanged can fire for transient Maya selections;
                # keep the mode armed and wait for the next valid controller.
                pass
        dialog = self._color_dialog
        if not dialog or not dialog.isVisible():
            self.refresh_colors()
            return
        try:
            view_data = self.color_feature.retarget_selection()
        except RigCtrlShapeToolError:
            self.refresh_colors()
            return
        dialog.set_current_colors(self._dialog_colors(view_data))
        dialog.set_preview_color(self._to_qcolor(view_data.initial_color))
        self.refresh_colors()

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

    def _dialog_colors(
        self,
        view_data: ColorViewData,
    ) -> tuple[tuple[str, QtGui.QColor], ...]:
        return tuple(
            (swatch.controller, self._to_qcolor(swatch.color))
            for swatch in view_data.current_colors
        )

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        application = QtWidgets.QApplication.instance()
        if application:
            application.removeEventFilter(self)
        if self.direct_edit_box.isChecked():
            self.direct_edit_box.setChecked(False)
        if self._color_dialog:
            self._color_dialog.reject()
        self.closing.emit()
        super().closeEvent(event)
