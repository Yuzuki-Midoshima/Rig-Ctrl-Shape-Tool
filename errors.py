"""Meaningful recoverable errors crossing from use cases into the UI."""


class RigCtrlShapeToolError(Exception):
    """Base exception for user-recoverable tool errors."""


class InvalidSelectionError(RigCtrlShapeToolError):
    """Raised when the active selection cannot satisfy a use case."""


class UnsupportedShapeError(RigCtrlShapeToolError):
    """Raised for referenced or unsupported controller shapes."""


class MissingCopyBufferError(RigCtrlShapeToolError):
    """Raised when the copied controller no longer exists."""


class EditSessionError(RigCtrlShapeToolError):
    """Raised when an edit-session transition is invalid."""
