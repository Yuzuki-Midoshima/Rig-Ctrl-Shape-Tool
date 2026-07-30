"""Shared current-controller-color swatch strip."""

from __future__ import annotations

from collections.abc import Sequence

from PySide6 import QtCore, QtGui, QtWidgets


class CurrentColorsWidget(QtWidgets.QFrame):
    """Compact, left-aligned color chips matching Maya's dark tool styling."""

    colorClicked = QtCore.Signal(QtGui.QColor)

    def __init__(self, *, framed: bool, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("currentColorsWidget")
        self.setFixedHeight(32 if framed else 24)
        self.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel if framed else QtWidgets.QFrame.Shape.NoFrame)
        self.setStyleSheet(
            "QFrame#currentColorsWidget { background: #333333; }"
            "QToolButton { border: 1px solid #222222; margin: 0px; padding: 0px; }"
            "QToolButton:hover { border: 1px solid #DDDDDD; }"
        )
        self._layout = QtWidgets.QHBoxLayout(self)
        self._layout.setContentsMargins(2, 2, 2, 2)
        self._layout.setSpacing(4 if framed else 0)
        self._layout.addStretch(1)

    def set_colors(self, colors: Sequence[tuple[str, QtGui.QColor]]) -> None:
        while self._layout.count() > 1:
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.hide()
                widget.deleteLater()
        for controller, color in colors:
            swatch = QtWidgets.QToolButton(self)
            swatch.setFixedSize(20, 20)
            swatch.setToolTip(controller)
            swatch.setStyleSheet(f"background-color: {color.name()};")
            swatch.clicked.connect(
                lambda _checked=False, value=QtGui.QColor(color): self.colorClicked.emit(value)
            )
            self._layout.insertWidget(self._layout.count() - 1, swatch)
