"""Reusable linked numeric field/slider widget."""

from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets


class DigitAwareDoubleSpinBox(QtWidgets.QDoubleSpinBox):
    """Step the decimal place containing the text cursor.

    Maya artists commonly click the digit they intend to edit before using the
    arrow buttons.  QDoubleSpinBox normally ignores that position and always
    uses one fixed singleStep, so we derive the step from the active digit.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._active_step = 0.1
        self.lineEdit().installEventFilter(self)

    def _step_for_position(self, cursor: int) -> float:
        editor = self.lineEdit()
        text = editor.text()
        decimal = text.find(".")
        if decimal < 0:
            decimal = len(text)

        # QLineEdit stores the caret between characters.  The editable place is
        # the digit immediately to its left, matching Maya's numeric fields.
        digit = cursor - 1
        if digit >= 0 and text[digit] == "." and cursor < len(text):
            digit = cursor
        if digit >= 0 and not text[digit].isdigit():
            left = next((index for index in range(digit - 1, -1, -1) if text[index].isdigit()), None)
            right = next((index for index in range(cursor, len(text)) if text[index].isdigit()), None)
            digit = left if left is not None else (right if right is not None else -1)
        if digit < 0 or digit >= len(text) or not text[digit].isdigit():
            return self.singleStep()

        exponent = decimal - digit - 1 if digit < decimal else decimal - digit
        return 10.0 ** exponent

    def _remember_position(self, cursor: int) -> None:
        self._active_step = self._step_for_position(cursor)

    def eventFilter(self, watched: QtCore.QObject, event: QtCore.QEvent) -> bool:
        editor = self.lineEdit()
        if watched is editor:
            if event.type() in (QtCore.QEvent.Type.MouseButtonPress,
                                QtCore.QEvent.Type.MouseButtonRelease):
                cursor = editor.cursorPositionAt(event.position().toPoint())
                self._remember_position(cursor)
            elif event.type() == QtCore.QEvent.Type.KeyRelease and event.key() in (
                QtCore.Qt.Key.Key_Left, QtCore.Qt.Key.Key_Right,
                QtCore.Qt.Key.Key_Home, QtCore.Qt.Key.Key_End,
            ):
                self._remember_position(editor.cursorPosition())
        return super().eventFilter(watched, event)

    def stepBy(self, steps: int) -> None:
        editor = self.lineEdit()
        cursor = editor.cursorPosition()
        self.setValue(self.value() + steps * self._active_step)
        editor.setCursorPosition(min(cursor, len(editor.text())))


class NumericControl(QtWidgets.QWidget):
    valuesChanged = QtCore.Signal(tuple)
    applyRequested = QtCore.Signal(int)
    resetRequested = QtCore.Signal(int)
    _SLIDER_FACTOR = 10000

    def __init__(self, values: tuple[float, ...], limits: tuple[float, float],
                 *, context_label: str, slider_center: float | None = None,
                 parent=None) -> None:
        super().__init__(parent)
        self._syncing = False
        self._limits = limits
        self._slider_center = slider_center
        self.fields: list[QtWidgets.QDoubleSpinBox] = []
        self.sliders: list[QtWidgets.QSlider] = []
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        field_row, slider_row = QtWidgets.QHBoxLayout(), QtWidgets.QHBoxLayout()
        for value in values:
            field = DigitAwareDoubleSpinBox()
            field.setDecimals(4)
            field.setRange(-100000, 100000)
            field.setSingleStep(.1)
            field.setValue(value)
            slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
            if slider_center is None:
                slider.setRange(
                    round(limits[0] * self._SLIDER_FACTOR),
                    round(limits[1] * self._SLIDER_FACTOR),
                )
            else:
                slider.setRange(-self._SLIDER_FACTOR, self._SLIDER_FACTOR)
            slider.setValue(self._value_to_slider(value))
            field.valueChanged.connect(self._from_fields)
            slider.valueChanged.connect(self._from_sliders)
            self.fields.append(field)
            self.sliders.append(slider)
            axis = len(self.fields) - 1
            title = f"{context_label} {'XYZ'[axis]}" if len(values) == 3 else context_label
            self._install_context_menu(field, axis, title, values[axis])
            self._install_context_menu(field.lineEdit(), axis, title, values[axis])
            field_row.addWidget(field)
            slider_row.addWidget(slider)
        layout.addLayout(field_row)
        layout.addLayout(slider_row)

    def _install_context_menu(
        self, widget: QtWidgets.QWidget, axis: int, title: str, reset_value: float
    ) -> None:
        widget.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        widget.customContextMenuRequested.connect(
            lambda position, target=widget, index=axis, heading=title, default=reset_value: self._show_context_menu(
                target, position, index, heading, default
            )
        )

    def _show_context_menu(
        self, widget: QtWidgets.QWidget, position: QtCore.QPoint, axis: int,
        title: str, reset_value: float
    ) -> None:
        menu, apply_action, reset_action = self._create_context_menu(title, reset_value)
        selected = menu.exec(widget.mapToGlobal(position))
        if selected is apply_action:
            self.applyRequested.emit(axis)
        elif selected is reset_action:
            self.resetRequested.emit(axis)

    def _create_context_menu(
        self, title: str, reset_value: float
    ) -> tuple[QtWidgets.QMenu, QtGui.QAction, QtGui.QAction]:
        """Build a self-describing menu for one numeric field."""
        menu = QtWidgets.QMenu(self)
        heading = menu.addAction(f"Target : {title}")
        heading.setEnabled(False)
        heading_font = heading.font()
        heading_font.setBold(True)
        heading.setFont(heading_font)
        menu.addSeparator()
        apply_action = menu.addAction(f"APPLY  {title}")
        reset_action = menu.addAction(f"RESET  {title}  ({reset_value:.4f})")
        return menu, apply_action, reset_action

    def values(self) -> tuple[float, ...]:
        return tuple(field.value() for field in self.fields)

    def set_values(self, values: tuple[float, ...]) -> None:
        self._syncing = True
        try:
            for field, slider, value in zip(self.fields, self.sliders, values):
                field.setValue(value)
                slider_value = self._value_to_slider(value)
                if self._slider_center is None:
                    slider.setRange(
                        min(slider.minimum(), slider_value),
                        max(slider.maximum(), slider_value),
                    )
                slider.setValue(slider_value)
        finally:
            self._syncing = False

    def _from_fields(self, _value: float | None = None) -> None:
        if self._syncing:
            return
        self.set_values(self.values())
        self.valuesChanged.emit(self.values())

    def _from_sliders(self) -> None:
        if self._syncing:
            return
        self._syncing = True
        try:
            for field, slider in zip(self.fields, self.sliders):
                field.setValue(self._slider_to_value(slider.value()))
        finally:
            self._syncing = False
        self.valuesChanged.emit(self.values())

    def _value_to_slider(self, value: float) -> int:
        center = self._slider_center
        if center is None:
            return round(value * self._SLIDER_FACTOR)
        minimum, maximum = self._limits
        span = center - minimum if value <= center else maximum - center
        if span <= 0:
            return 0
        direction = -1.0 if value <= center else 1.0
        distance = abs(value - center) / span
        return round(direction * min(distance, 1.0) * self._SLIDER_FACTOR)

    def _slider_to_value(self, slider_value: int) -> float:
        center = self._slider_center
        if center is None:
            return slider_value / self._SLIDER_FACTOR
        minimum, maximum = self._limits
        ratio = slider_value / self._SLIDER_FACTOR
        span = center - minimum if ratio < 0 else maximum - center
        return center + ratio * span
