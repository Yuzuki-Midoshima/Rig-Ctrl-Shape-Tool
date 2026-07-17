"""Constants grouped by the responsibility that consumes them."""

from dataclasses import dataclass


class CurveDisplayAttributes:
    OVERRIDE_ENABLED = "overrideEnabled"
    OVERRIDE_COLOR = "overrideColor"
    OVERRIDE_RGB_COLORS = "overrideRGBColors"
    OVERRIDE_COLOR_RGB = "overrideColorRGB"
    LINE_WIDTH = "lineWidth"


@dataclass(frozen=True)
class TransformLimits:
    scale_min: float = -10.0
    scale_max: float = 10.0
    rotate_min: float = -180.0
    rotate_max: float = 180.0
    move_min: float = -100.0
    move_max: float = 100.0
