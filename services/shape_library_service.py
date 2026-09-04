"""Optional launcher for the standalone Controller Shape Library window."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import ModuleType


class ShapeLibraryService:
    """Open Controller-Shape-Library without coupling either tool's UI lifetime."""

    _PACKAGE = "controller_shape_library.ui.main_window"

    @staticmethod
    def _sibling_root() -> Path:
        return Path(__file__).resolve().parents[2] / "Controller-Shape-Library"

    def _load_window_module(self) -> ModuleType:
        try:
            return importlib.import_module(self._PACKAGE)
        except ModuleNotFoundError as error:
            # A source checkout beside this tool is the normal development
            # layout. Installed Maya modules resolve on the first import.
            if error.name != "controller_shape_library":
                raise
            sibling = self._sibling_root()
            if not (sibling / "controller_shape_library" / "__init__.py").is_file():
                raise RuntimeError(
                    "Controller Shape Library was not found. Install or place "
                    "Controller-Shape-Library beside Rig-Ctrl-Shape-Tool."
                ) from error
            sibling_text = str(sibling)
            if sibling_text not in sys.path:
                sys.path.insert(0, sibling_text)
            importlib.invalidate_caches()
            return importlib.import_module(self._PACKAGE)

    def show(self) -> object:
        """Show the library's independent singleton window."""
        module = self._load_window_module()
        return module.show()
