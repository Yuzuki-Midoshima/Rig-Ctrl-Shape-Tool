"""Maya adapter for curve override colors; it exposes domain values only."""

from __future__ import annotations

from collections.abc import Sequence

import maya.cmds as cmds

from ..domain import ColorMode, ColorOverrideState, ColorValue
from ..maya_utils import is_settable


class ColorService:
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
        for attribute, value in (("overrideEnabled", 1), ("overrideRGBColors", 1)):
            if is_settable(f"{shape}.{attribute}"):
                cmds.setAttr(f"{shape}.{attribute}", value)
        if is_settable(f"{shape}.overrideColorRGB"):
            cmds.setAttr(f"{shape}.overrideColorRGB", *color)

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
            return ColorValue.rgb_color(state.rgb)
        indexed = cmds.colorIndex(state.index, query=True)
        return ColorValue(ColorMode.INDEX, index=state.index, rgb=tuple(indexed[:3]))
