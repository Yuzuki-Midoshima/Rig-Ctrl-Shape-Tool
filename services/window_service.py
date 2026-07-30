"""Maya event subscriptions used to keep view data current."""

from __future__ import annotations

from collections.abc import Callable, Sequence

import maya.cmds as cmds


class WindowService:
    def watch_scene(
        self,
        refresh_callback: Callable[[], None],
        selection_callback: Callable[[], None],
    ) -> list[int]:
        callbacks = {
            "SelectionChanged": selection_callback,
            "Undo": refresh_callback,
            "Redo": refresh_callback,
        }
        jobs = [
            cmds.scriptJob(event=[event, callback], protected=True)
            for event, callback in callbacks.items()
        ]
        # Maya batch mode accepts scriptJob calls but returns None; GUI mode
        # returns integer ids that must be cleaned up with the window.
        return [job for job in jobs if job is not None]

    def stop_watching(self, jobs: Sequence[int]) -> None:
        for job in jobs:
            if cmds.scriptJob(exists=job):
                cmds.scriptJob(kill=job, force=True)
