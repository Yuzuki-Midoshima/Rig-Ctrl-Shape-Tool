"""Maya event subscriptions used to keep view data current."""

from __future__ import annotations

from collections.abc import Callable, Sequence

import maya.cmds as cmds


class WindowService:
    EVENTS = ("SelectionChanged", "Undo", "Redo")

    def watch_scene(self, callback: Callable[[], None]) -> list[int]:
        jobs = [cmds.scriptJob(event=[event, callback], protected=True) for event in self.EVENTS]
        # Maya batch mode accepts scriptJob calls but returns None; GUI mode
        # returns integer ids that must be cleaned up with the window.
        return [job for job in jobs if job is not None]

    def stop_watching(self, jobs: Sequence[int]) -> None:
        for job in jobs:
            if cmds.scriptJob(exists=job):
                cmds.scriptJob(kill=job, force=True)
