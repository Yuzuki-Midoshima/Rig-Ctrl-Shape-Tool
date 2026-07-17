"""Development entry point that reloads all package modules."""

from __future__ import annotations

import sys

PACKAGE_PREFIX = "rig_ctrl_shape_tool"

for module_name in sorted(
    (name for name in tuple(sys.modules)
     if name == PACKAGE_PREFIX or name.startswith(PACKAGE_PREFIX + ".")),
    key=len,
    reverse=True,
):
    sys.modules.pop(module_name, None)

from rig_ctrl_shape_tool.app import show

show()
