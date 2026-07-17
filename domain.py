"""Maya/Qt-independent domain models shared across application layers."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

Color3 = tuple[float, float, float]


class CurveForm(Enum):
    OPEN = 0
    CLOSED = 1
    PERIODIC = 2


class ColorMode(Enum):
    INDEX = "index"
    RGB = "rgb"


class SessionStatus(Enum):
    IDLE = "idle"
    ACTIVE = "active"
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"


@dataclass
class TransformValues:
    """Current transform inputs shared by Feature and Scene Service."""

    uniform: float = 1.0
    scale: tuple[float, float, float] = (1.0, 1.0, 1.0)
    rotate: tuple[float, float, float] = (0.0, 0.0, 0.0)
    move: tuple[float, float, float] = (0.0, 0.0, 0.0)
    line_width: float = 0.0


@dataclass(frozen=True)
class ColorValue:
    mode: ColorMode
    index: int | None = None
    rgb: Color3 | None = None

    @classmethod
    def rgb_color(cls, rgb: Color3) -> "ColorValue":
        return cls(ColorMode.RGB, rgb=clamp_rgb(rgb))


@dataclass(frozen=True)
class ColorOverrideState:
    enabled: bool
    use_rgb: bool
    index: int
    rgb: Color3


@dataclass(frozen=True)
class ColorSwatchData:
    controller: str
    color: ColorValue


@dataclass(frozen=True)
class ColorViewData:
    initial_color: ColorValue
    current_colors: tuple[ColorSwatchData, ...]


@dataclass(frozen=True)
class DisplaySettings:
    """Extensible snapshot of Maya shape display attributes.

    Maya node types and versions do not expose an identical fixed attribute
    set, so the adapter records only attributes that exist and are readable.
    """

    values: tuple[tuple[str, object], ...]

@dataclass(frozen=True)
class CurveShapeData:
    points: tuple[tuple[float, float, float, float], ...]
    knots: tuple[float, ...]
    degree: int
    form: CurveForm
    rational: bool
    dimension: int
    spans: int


@dataclass(frozen=True)
class PlugConnection:
    source_plug: str
    destination_plug: str


def clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def clamp_rgb(rgb: Color3) -> Color3:
    return tuple(clamp(component) for component in rgb)  # type: ignore[return-value]
