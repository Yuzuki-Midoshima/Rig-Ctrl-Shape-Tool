"""Non-modal color picker preserving the tool's preview/apply workflow."""

from __future__ import annotations

from collections.abc import Sequence

from PySide6 import QtCore, QtGui, QtWidgets

from .style import STANDARD_COLORS
from .color_swatches import CurrentColorsWidget


class ColorPreviewDialog(QtWidgets.QDialog):
    """Host QColorDialog with explicit Apply/Cancel and current-color swatches."""

    colorPreviewed = QtCore.Signal(QtGui.QColor)

    def __init__(self, initial: QtGui.QColor,
                 current_colors: Sequence[tuple[str, QtGui.QColor]], parent=None) -> None:
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setModal(False)
        self.setWindowModality(QtCore.Qt.WindowModality.NonModal)
        self.setWindowTitle("Controller Shape Color")
        self.resize(500, 520)
        self.setMinimumSize(440, 460)
        self._original_standard = tuple(
            QtWidgets.QColorDialog.standardColor(index) for index in range(len(STANDARD_COLORS))
        )
        for index, value in enumerate(STANDARD_COLORS):
            QtWidgets.QColorDialog.setStandardColor(index, QtGui.QColor(value))

        self.picker = QtWidgets.QColorDialog(initial, self)
        self.picker.setWindowFlags(QtCore.Qt.WindowType.Widget)
        self.picker.setWindowModality(QtCore.Qt.WindowModality.NonModal)
        self.picker.setOption(QtWidgets.QColorDialog.ColorDialogOption.DontUseNativeDialog, True)
        self.picker.setOption(QtWidgets.QColorDialog.ColorDialogOption.NoButtons, True)
        self.picker.setMinimumSize(410, 370)
        self.picker.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding,
                                  QtWidgets.QSizePolicy.Policy.Expanding)
        self._editing_custom_index: int | None = None

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        layout.addWidget(self.picker, 1)
        layout.addWidget(QtWidgets.QLabel("Current Colors"))
        self.current_colors = CurrentColorsWidget(framed=True, parent=self)
        self.current_colors.set_colors(current_colors)
        self.current_colors.colorClicked.connect(self.select_color)
        layout.addWidget(self.current_colors)
        buttons = QtWidgets.QHBoxLayout()
        cancel = QtWidgets.QPushButton("Cancel")
        apply = QtWidgets.QPushButton("Apply")
        buttons.addWidget(cancel)
        buttons.addWidget(apply)
        layout.addLayout(buttons)
        cancel.clicked.connect(self.reject)
        apply.clicked.connect(self.accept)
        self.picker.currentColorChanged.connect(self._on_picker_color_changed)
        self.finished.connect(self._restore_standard_palette)
        self.picker.show()
        if self.picker.layout():
            self.picker.layout().setContentsMargins(6, 6, 6, 6)
            self.picker.layout().setSpacing(4)
        self._configure_custom_colors()

    def _configure_custom_colors(self) -> None:
        wells = [widget for widget in self.picker.findChildren(QtWidgets.QWidget)
                 if widget.metaObject().className().endswith("QWellArray")]
        self._color_wells = wells
        self._custom_well = (
            max(
                wells,
                key=lambda widget: widget.mapToGlobal(widget.rect().topLeft()).y(),
            )
            if wells
            else None
        )
        for well in wells:
            well.installEventFilter(self)
        if self._custom_well:
            self._custom_well.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        for button in self.picker.findChildren(QtWidgets.QPushButton):
            if "Add to Custom" in button.text() or "カスタム" in button.text():
                button.clicked.connect(self._finish_custom_edit)
            if "Pick Screen Color" in button.text() or "スクリーン" in button.text():
                button.clicked.connect(self._stop_custom_edit)

    def _custom_index_at(self, position: QtCore.QPoint) -> int | None:
        if not self._custom_well or not self._custom_well.rect().contains(position):
            return None
        count = QtWidgets.QColorDialog.customCount()
        columns = 8
        rows = max(1, (count + columns - 1) // columns)
        column = min(columns - 1, max(0, position.x() * columns // max(1, self._custom_well.width())))
        row = min(rows - 1, max(0, position.y() * rows // max(1, self._custom_well.height())))
        index = column * rows + row
        return index if index < count else None

    def _show_custom_menu(self, index: int, global_position: QtCore.QPoint) -> None:
        menu = QtWidgets.QMenu(self)
        edit, remove = menu.addAction("Edit"), menu.addAction("Remove")
        edit.triggered.connect(lambda: self._edit_custom_color(index))
        remove.triggered.connect(lambda: self._remove_custom_color(index))
        menu.popup(global_position)

    def _edit_custom_color(self, index: int) -> None:
        color = QtWidgets.QColorDialog.customColor(index)
        if not color.isValid():
            return
        self._editing_custom_index = index
        self.set_preview_color(color)
        self.colorPreviewed.emit(color)

    def _remove_custom_color(self, index: int) -> None:
        QtWidgets.QColorDialog.setCustomColor(index, QtGui.QColor("white"))
        if self._editing_custom_index == index:
            self._editing_custom_index = None
        if self._custom_well:
            self._custom_well.update()

    def _stop_custom_edit(self) -> None:
        self._editing_custom_index = None

    def _finish_custom_edit(self) -> None:
        if self._editing_custom_index is None:
            return
        QtWidgets.QColorDialog.setCustomColor(self._editing_custom_index, self.picker.currentColor())
        self._editing_custom_index = None
        if self._custom_well:
            self._custom_well.update()

    def _on_picker_color_changed(self, color: QtGui.QColor) -> None:
        if self._editing_custom_index is not None:
            QtWidgets.QColorDialog.setCustomColor(self._editing_custom_index, color)
            if self._custom_well:
                self._custom_well.update()
        self.colorPreviewed.emit(color)

    def eventFilter(self, watched: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if watched in self._color_wells and watched is not self._custom_well:
            if event.type() == QtCore.QEvent.Type.MouseButtonPress:
                self._stop_custom_edit()
            return super().eventFilter(watched, event)
        if watched is not self._custom_well:
            return super().eventFilter(watched, event)
        if event.type() == QtCore.QEvent.Type.MouseButtonPress:
            if event.button() == QtCore.Qt.MouseButton.LeftButton:
                self._stop_custom_edit()
            elif event.button() == QtCore.Qt.MouseButton.RightButton:
                index = self._custom_index_at(event.position().toPoint())
                if index is not None:
                    self._show_custom_menu(index, event.globalPosition().toPoint())
                    return True
            self._custom_well.setFocus()
        elif event.type() == QtCore.QEvent.Type.ContextMenu:
            index = self._custom_index_at(event.pos())
            if index is not None:
                self._show_custom_menu(index, event.globalPos())
                return True
        return super().eventFilter(watched, event)

    def select_color(self, color: QtGui.QColor) -> None:
        self._stop_custom_edit()
        self.picker.setCurrentColor(color)

    def set_preview_color(self, color: QtGui.QColor) -> None:
        """Update the picker display without reapplying color to the scene."""
        blocker = QtCore.QSignalBlocker(self.picker)
        self.picker.setCurrentColor(color)
        del blocker

    def place_next_to(self, window: QtWidgets.QWidget) -> None:
        screen = window.screen() or QtWidgets.QApplication.primaryScreen()
        target = window.frameGeometry().topRight() + QtCore.QPoint(10, 0)
        if screen:
            area = screen.availableGeometry()
            target.setX(min(target.x(), area.right() - self.width()))
            target.setY(min(max(target.y(), area.top()), area.bottom() - self.height()))
        self.move(target)

    def _restore_standard_palette(self) -> None:
        for index, color in enumerate(self._original_standard):
            QtWidgets.QColorDialog.setStandardColor(index, color)
