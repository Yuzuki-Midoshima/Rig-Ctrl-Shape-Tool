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

    def focusInEvent(self, event: QtGui.QFocusEvent) -> None:
        super().focusInEvent(event)
        if event.reason() == QtCore.Qt.FocusReason.MouseFocusReason:
            # Run after the mouse click has positioned the caret.  This makes
            # the first click start a replacement edit; another click while
            # already focused can still target an individual digit.
            QtCore.QTimer.singleShot(0, self.lineEdit().selectAll)

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
            if event.type() == QtCore.QEvent.Type.ShortcutOverride:
                # Maya assigns hotkeys to punctuation such as period.  Claim
                # numeric editing keys while the line edit has focus so Maya's
                # application-level shortcut handling cannot consume the
                # decimal point before QLineEdit receives its key event.
                numeric_keys = {
                    QtCore.Qt.Key.Key_0, QtCore.Qt.Key.Key_1,
                    QtCore.Qt.Key.Key_2, QtCore.Qt.Key.Key_3,
                    QtCore.Qt.Key.Key_4, QtCore.Qt.Key.Key_5,
                    QtCore.Qt.Key.Key_6, QtCore.Qt.Key.Key_7,
                    QtCore.Qt.Key.Key_8, QtCore.Qt.Key.Key_9,
                    QtCore.Qt.Key.Key_Period, QtCore.Qt.Key.Key_Comma,
                    QtCore.Qt.Key.Key_Plus, QtCore.Qt.Key.Key_Minus,
                    QtCore.Qt.Key.Key_Backspace, QtCore.Qt.Key.Key_Delete,
                }
                if event.key() in numeric_keys:
                    event.accept()
                    return False
            elif event.type() == QtCore.QEvent.Type.KeyPress:
                # A click at the far left places the caret before the rendered
                # value (for example ``|0.0000``).  Inserting ``.25`` or
                # ``0.25`` there would make an invalid string, so QDoubleSpinBox
                # rejects the keystroke.  Treat typing at that specific
                # position as starting a replacement value, as Maya numeric
                # fields do.
                replacement_keys = {
                    QtCore.Qt.Key.Key_0, QtCore.Qt.Key.Key_1,
                    QtCore.Qt.Key.Key_2, QtCore.Qt.Key.Key_3,
                    QtCore.Qt.Key.Key_4, QtCore.Qt.Key.Key_5,
                    QtCore.Qt.Key.Key_6, QtCore.Qt.Key.Key_7,
                    QtCore.Qt.Key.Key_8, QtCore.Qt.Key.Key_9,
                    QtCore.Qt.Key.Key_Period, QtCore.Qt.Key.Key_Comma,
                    QtCore.Qt.Key.Key_Plus, QtCore.Qt.Key.Key_Minus,
                }
                if (
                    event.key() in replacement_keys
                    and editor.cursorPosition() == 0
                    and not editor.hasSelectedText()
                ):
                    editor.selectAll()
                elif editor.hasSelectedText() and event.key() in (
                    QtCore.Qt.Key.Key_Period,
                    QtCore.Qt.Key.Key_Comma,
                ):
                    # Bypass QDoubleSpinBox's validator for the intermediate
                    # decimal-only text.  Start a new zero-based fractional
                    # value and consume the key ourselves.
                    self.setValue(0.0)
                    editor.setCursorPosition(editor.text().find(".") + 1)
                    return True
                elif not editor.hasSelectedText():
                    text = editor.text()
                    cursor = editor.cursorPosition()
                    decimal = text.find(".")
                    if event.key() in (
                        QtCore.Qt.Key.Key_Period,
                        QtCore.Qt.Key.Key_Comma,
                    ) and decimal >= 0:
                        # There can only be one decimal separator.  Pressing it
                        # again means "edit the fractional part", not insert a
                        # second separator that the validator will reject.
                        editor.setCursorPosition(decimal + 1)
                        return True
                    if (
                        QtCore.Qt.Key.Key_0 <= event.key() <= QtCore.Qt.Key.Key_9
                        and decimal >= 0
                        and cursor > decimal
                    ):
                        # The display already contains the configured number
                        # of decimal places (0.0000).  Replace the digit under
                        # the caret instead of trying to insert a fifth place.
                        # At the end of the text there is no digit to the
                        # right, so replace the final fractional digit.
                        digit = cursor if cursor < len(text) else cursor - 1
                        if digit > decimal and text[digit].isdigit():
                            replacement = str(event.key() - QtCore.Qt.Key.Key_0)
                            edited = text[:digit] + replacement + text[digit + 1:]
                            try:
                                value = float(edited)
                            except ValueError:
                                return True
                            self.setValue(value)
                            editor.setCursorPosition(
                                min(digit + 1, len(editor.text()))
                            )
                            return True
            elif event.type() in (QtCore.QEvent.Type.MouseButtonPress,
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
    interactionStarted = QtCore.Signal()
    interactionFinished = QtCore.Signal()
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
            slider.sliderPressed.connect(self.interactionStarted)
            slider.sliderReleased.connect(self.interactionFinished)
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
        heading = menu.addAction(f"対象：{title}")
        heading.setEnabled(False)
        heading_font = heading.font()
        heading_font.setBold(True)
        heading.setFont(heading_font)
        menu.addSeparator()
        apply_action = menu.addAction(f"適用  {title}")
        reset_action = menu.addAction(f"リセット  {title}  ({reset_value:.4f})")
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
        # Do not call set_values() here.  QDoubleSpinBox emits valueChanged
        # while its line edit is still being edited; writing the value back to
        # that same field normalizes the text and moves its caret after every
        # keystroke.  In Maya this made editing from the beginning of the text
        # appear to reject keyboard input.
        values = self.values()
        self._syncing = True
        try:
            for slider, value in zip(self.sliders, values):
                slider_value = self._value_to_slider(value)
                if self._slider_center is None:
                    slider.setRange(
                        min(slider.minimum(), slider_value),
                        max(slider.maximum(), slider_value),
                    )
                slider.setValue(slider_value)
        finally:
            self._syncing = False
        self.valuesChanged.emit(values)

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
