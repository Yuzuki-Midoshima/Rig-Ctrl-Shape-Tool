"""Maya adapter for curve override colors; it exposes domain values only."""

from __future__ import annotations

from collections.abc import Sequence
import os
from typing import Any

import maya.cmds as cmds
import PyOpenColorIO as ocio

from ..core.domain import ColorMode, ColorOverrideState, ColorValue
from ..maya.utils import is_settable


class ColorService:
    def __init__(self) -> None:
        self._processor_key: tuple[str, str, str, str] | None = None
        self._display_processor: Any = None
        self._rendering_processor: Any = None

    def capture(self, shape: str) -> ColorOverrideState:
        rgb = cmds.getAttr(f"{shape}.overrideColorRGB")
        value = rgb[0] if isinstance(rgb, list) else rgb
        return ColorOverrideState(
            enabled=bool(cmds.getAttr(f"{shape}.overrideEnabled")),
            use_rgb=bool(cmds.getAttr(f"{shape}.overrideRGBColors")),
            index=int(cmds.getAttr(f"{shape}.overrideColor")),
            rgb=tuple(value),
        )

    def apply(self, shape: str, color: Sequence[float]) -> None:
        if not cmds.objExists(shape) or cmds.referenceQuery(shape, isNodeReferenced=True):
            return
        rendering_color = self.to_rendering_space(color)
        for attribute, value in (("overrideEnabled", 1), ("overrideRGBColors", 1)):
            if is_settable(f"{shape}.{attribute}"):
                cmds.setAttr(f"{shape}.{attribute}", value)
        if is_settable(f"{shape}.overrideColorRGB"):
            cmds.setAttr(f"{shape}.overrideColorRGB", *rendering_color)

    def restore(self, shape: str, state: ColorOverrideState) -> None:
        if not cmds.objExists(shape):
            return
        values = {
            "overrideEnabled": state.enabled,
            "overrideRGBColors": state.use_rgb,
            "overrideColor": state.index,
            "overrideColorRGB": state.rgb,
        }
        for attribute, value in values.items():
            plug = f"{shape}.{attribute}"
            if is_settable(plug):
                try:
                    cmds.setAttr(plug, *value) if isinstance(value, tuple) else cmds.setAttr(plug, value)
                except RuntimeError:
                    continue

    def display_color(self, state: ColorOverrideState) -> ColorValue:
        if not state.enabled:
            return ColorValue.rgb_color((100 / 255.0,) * 3)
        if state.use_rgb:
            return ColorValue.rgb_color(self.to_display_space(state.rgb))
        indexed = cmds.colorIndex(state.index, query=True)
        return ColorValue(ColorMode.INDEX, index=state.index, rgb=tuple(indexed[:3]))

    def to_display_space(self, color: Sequence[float]) -> tuple[float, float, float]:
        """Convert a stored rendering-space value for use in the Qt picker."""
        processors = self._color_processors()
        if processors is None:
            return tuple(color[:3])
        return tuple(processors[0].applyRGB(list(color[:3])))

    def to_rendering_space(self, color: Sequence[float]) -> tuple[float, float, float]:
        """Convert a Qt display-space value before storing it on a Maya shape."""
        processors = self._color_processors()
        if processors is None:
            return tuple(color[:3])
        return tuple(processors[1].applyRGB(list(color[:3])))

    def _color_processors(self) -> tuple[Any, Any] | None:
        if not cmds.colorManagementPrefs(query=True, cmEnabled=True):
            return None
        config_path = cmds.colorManagementPrefs(query=True, configFilePath=True)
        maya_location = os.environ.get("MAYA_LOCATION", "")
        config_path = config_path.replace(
            "<MAYA_RESOURCES>",
            os.path.join(maya_location, "resources"),
        )
        key = (
            config_path,
            cmds.colorManagementPrefs(query=True, renderingSpaceName=True),
            cmds.colorManagementPrefs(query=True, displayName=True),
            cmds.colorManagementPrefs(query=True, viewName=True),
        )
        if key != self._processor_key:
            config = ocio.Config.CreateFromFile(key[0])
            transform = ocio.DisplayViewTransform()
            transform.setSrc(key[1])
            transform.setDisplay(key[2])
            transform.setView(key[3])
            self._display_processor = config.getProcessor(
                transform
            ).getDefaultCPUProcessor()
            self._rendering_processor = config.getProcessor(
                transform,
                ocio.TRANSFORM_DIR_INVERSE,
            ).getDefaultCPUProcessor()
            self._processor_key = key
        return self._display_processor, self._rendering_processor
