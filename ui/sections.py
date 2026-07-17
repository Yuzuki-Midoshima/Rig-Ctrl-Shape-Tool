"""Small layout helpers for section headers."""

from PySide6 import QtCore, QtWidgets


class SectionHeader(QtWidgets.QWidget):
    resetClicked = QtCore.Signal()

    def __init__(self, title: str, parent=None) -> None:
        super().__init__(parent)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QtWidgets.QLabel(title))
        layout.addStretch()
        button = QtWidgets.QToolButton()
        icon = QtWidgets.QApplication.style().standardIcon(
            QtWidgets.QStyle.StandardPixmap.SP_BrowserReload
        )
        button.setIcon(icon)
        button.setFixedSize(18, 18)
        button.clicked.connect(self.resetClicked)
        layout.addWidget(button)
