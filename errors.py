"""Meaningful recoverable errors crossing from use cases into the UI."""


class RigCtrlShapeToolError(Exception):
    """Base exception for user-recoverable tool errors."""


class InvalidSelectionError(RigCtrlShapeToolError):
    pass


class UnsupportedShapeError(RigCtrlShapeToolError):
    pass


class MissingCopyBufferError(RigCtrlShapeToolError):
    pass


class EditSessionError(RigCtrlShapeToolError):
    pass
