"""Application-owned runtime state; no Maya or Qt dependencies."""

from __future__ import annotations

from dataclasses import dataclass, field
from .domain import ColorOverrideState, TransformValues
from .sessions import EditSessionLifecycle


@dataclass
class PreviewState:
    positions: dict[str, tuple[float, float, float]] = field(default_factory=dict)
    line_widths: dict[str, float] = field(default_factory=dict)
    undo_open: bool = False
    enabled: bool = False
    lifecycle: EditSessionLifecycle = field(default_factory=EditSessionLifecycle)

    def clear(self) -> None:
        """Discard captured scene data while retaining the lifecycle outcome."""
        self.positions.clear()
        self.line_widths.clear()
        self.undo_open = False


@dataclass
class ColorSession:
    original: dict[str, ColorOverrideState]
    lifecycle: EditSessionLifecycle = field(default_factory=EditSessionLifecycle)
    undo_open: bool = False


@dataclass
class CopyBuffer:
    controller: str | None = None


@dataclass
class WindowState:
    event_jobs: list[int] = field(default_factory=list)
    closing: bool = False


@dataclass
class ToolState:
    values: TransformValues = field(default_factory=TransformValues)
    preview: PreviewState = field(default_factory=PreviewState)
    color_session: ColorSession | None = None
    color_reset_states: dict[str, ColorOverrideState] = field(default_factory=dict)
    copy_buffer: CopyBuffer = field(default_factory=CopyBuffer)
    window: WindowState = field(default_factory=WindowState)
    line_width_dirty: bool = False

    def reset_values(self) -> None:
        self.values = TransformValues()
        self.line_width_dirty = True
