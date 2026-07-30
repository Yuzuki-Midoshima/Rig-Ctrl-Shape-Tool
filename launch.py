"""Shelf entry point that reloads the package in long-running Maya sessions."""

from __future__ import annotations

import sys


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

from rig_ctrl_shape_tool.app import show  # noqa: E402

show()
