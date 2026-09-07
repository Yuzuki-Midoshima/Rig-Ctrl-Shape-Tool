"""Feature implementations exposed to the composition root."""

from importlib import import_module


_FEATURE_MODULES = {
    "ColorFeature": "color",
    "ControlsFeature": "controls",
    "DisconnectFeature": "disconnect",
    "PreviewFeature": "preview",
    "CopyPasteFeature": "copy_paste",
    "TransformFeature": "transform",
}

__all__ = list(_FEATURE_MODULES)


def __getattr__(name: str):
    if name not in _FEATURE_MODULES:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    feature = getattr(import_module(f".{_FEATURE_MODULES[name]}", __name__), name)
    globals()[name] = feature
    return feature
