"""Manual controller-CV editing through Maya's native manipulators."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from ..core.errors import InvalidSelectionError

if TYPE_CHECKING:
    from ..services import MayaSceneService, SelectionService


class DirectEditFeature:
    """Enter and leave component editing without changing controller transforms."""

    def __init__(self, selection: SelectionService, scene: MayaSceneService) -> None:
        self._selection = selection
        self._scene = scene
        self._controllers: list[str] = []
        self.cancel_color: Callable[[], None] = lambda: None
        self.cancel_preview: Callable[[], None] = lambda: None
        self.rebase_values: Callable[[], None] = lambda: None

    @property
    def is_active(self) -> bool:
        return bool(self._controllers)

    def set_enabled(self, enabled: bool) -> None:
        self.begin() if enabled else self.finish()

    def begin(self) -> None:
        controllers = self._selection.controllers()
        cvs = [
            cv
            for controller in controllers
            for cv in self._selection.controller_cvs(controller)
        ]
        if not cvs:
            raise InvalidSelectionError("NURBSカーブシェイプを持つコントローラーを選択してください")
        self.cancel_color()
        self.cancel_preview()
        self._controllers = list(controllers)
        self._scene.enter_component_edit(cvs)

    def finish(self) -> None:
        if not self._controllers:
            return
        controllers = [node for node in self._controllers if self._scene.exists(node)]
        self._scene.leave_component_edit(controllers)
        self._controllers.clear()
        # The manually adjusted CVs are now the baseline for subsequent tool
        # operations; stale numeric inputs must not be applied a second time.
        self.rebase_values()

    def retarget_selection(self) -> bool:
        """Keep Direct Edit active and follow a newly selected controller."""
        if not self.is_active:
            return False
        controllers = self._selection.controllers()
        if not controllers or controllers == self._controllers:
            return False
        cvs = [
            cv
            for controller in controllers
            for cv in self._selection.controller_cvs(controller)
        ]
        if not cvs:
            return False
        self._controllers = list(controllers)
        self._scene.enter_component_edit(cvs)
        return True

    def select_next_shape(self) -> bool:
        """Replace Maya's double-click CV selection with the next curve shape."""
        if not self.is_active or not self._scene.pointer_is_over_viewport():
            return False
        shapes = [
            shape
            for controller in self._controllers
            for shape in self._selection.curve_shapes(controller)
        ]
        if not shapes:
            return False

        selected = self._selection.selected_component_shapes()
        current = next((shape for shape in selected if shape in shapes), None)
        next_shape = (
            shapes[(shapes.index(current) + 1) % len(shapes)]
            if current
            else shapes[0]
        )
        cvs = self._selection.shape_cvs(next_shape)
        if not cvs:
            return False
        self._scene.enter_component_edit(cvs)
        return True
