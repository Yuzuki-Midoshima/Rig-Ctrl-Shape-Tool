"""Typed repository facade for Maya curve-shape persistence."""

from __future__ import annotations

from collections.abc import Sequence

from .. import curve_io
from ..domain import CurveShapeData, DisplaySettings


class CurveService:
    def capture(self, shape: str) -> CurveShapeData:
        return curve_io.capture_curve_definition(shape)

    def create(self, target: str, definition: CurveShapeData) -> str:
        return curve_io.create_curve_shape(target, definition)

    def display_settings(self, shape: str, attributes: Sequence[str]) -> DisplaySettings:
        return curve_io.shape_display_settings(shape, attributes)

    def apply_display_settings(self, shape: str, settings: DisplaySettings) -> None:
        curve_io.apply_shape_display_settings(shape, settings)

    def match_position(self, target: str, source: str) -> bool:
        return curve_io.match_world_position(target, source)

    def delete_source_if_safe(self, transform: str) -> None:
        curve_io.delete_visual_source_if_safe(transform)

    def create_add_controller(
        self, controller: str, definitions: Sequence[CurveShapeData],
        display_settings: DisplaySettings,
    ) -> str:
        return curve_io.create_add_controller(controller, definitions, display_settings)
