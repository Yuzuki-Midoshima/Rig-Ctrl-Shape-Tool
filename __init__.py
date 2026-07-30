"""Rig Controller Shape Tool public API with lazy Maya imports."""


def show():
    from .app import show as _show
    return _show()


__all__ = ["show"]
