"""Shelf entry point that reloads the package in long-running Maya sessions."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


PACKAGE_PREFIX = "rig_ctrl_shape_tool"

# Maya keeps imported Python modules until the application exits. Clearing only
# this package ensures a shelf relaunch uses the installed files without
# requiring artists to restart Maya after an update.
for module_name in sorted(
    (
        name
        for name in tuple(sys.modules)
        if name == PACKAGE_PREFIX or name.startswith(PACKAGE_PREFIX + ".")
    ),
    key=len,
    reverse=True,
):
    sys.modules.pop(module_name, None)

# The installed folder is intentionally named ``Rig-Ctrl-Shape-Tool`` for
# display.  Since hyphens are not valid in Python package names, register that
# folder under the import-safe package name used by the source code.
package_dir = Path(__file__).resolve().parent
package_spec = importlib.util.spec_from_file_location(
    PACKAGE_PREFIX,
    package_dir / "__init__.py",
    submodule_search_locations=[str(package_dir)],
)
if package_spec is None or package_spec.loader is None:
    raise ImportError(f"Unable to load {PACKAGE_PREFIX} from {package_dir}")

package = importlib.util.module_from_spec(package_spec)
sys.modules[PACKAGE_PREFIX] = package
package_spec.loader.exec_module(package)

from rig_ctrl_shape_tool.app import show  # noqa: E402

show()
