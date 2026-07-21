"""Shared immutable values used by Feature and UI layers."""


class CurveDisplayAttributes:
    """Shape attributes preserved by Copy/Paste operations."""

    VISIBILITY = "visibility"
    OVERRIDE_ENABLED = "overrideEnabled"
    OVERRIDE_RGB_COLORS = "overrideRGBColors"
    OVERRIDE_COLOR = "overrideColor"
    OVERRIDE_COLOR_RGB = "overrideColorRGB"
    OVERRIDE_DISPLAY_TYPE = "overrideDisplayType"
    OVERRIDE_LEVEL_OF_DETAIL = "overrideLevelOfDetail"
    OVERRIDE_SHADING = "overrideShading"
    LINE_WIDTH = "lineWidth"
    ALWAYS_DRAW_ON_TOP = "alwaysDrawOnTop"

    ALL = (
        VISIBILITY,
        OVERRIDE_ENABLED,
        OVERRIDE_RGB_COLORS,
        OVERRIDE_COLOR,
        OVERRIDE_COLOR_RGB,
        OVERRIDE_DISPLAY_TYPE,
        OVERRIDE_LEVEL_OF_DETAIL,
        OVERRIDE_SHADING,
        LINE_WIDTH,
        ALWAYS_DRAW_ON_TOP,
    )


class TransformLimits:
    """Established numeric ranges for the existing compact controls."""

    SCALE = (-10.0, 10.0)
    ROTATE = (-180.0, 180.0)
    MOVE = (-100.0, 100.0)
    LINE_WIDTH = (-30.0, 30.0)
