"""Pure edit-session lifecycle validation."""

from dataclasses import dataclass

from .domain import SessionStatus
from .errors import EditSessionError


@dataclass
class EditSessionLifecycle:
    """Validate the shared Preview and Color edit-session transitions."""

    status: SessionStatus = SessionStatus.IDLE

    @property
    def is_active(self) -> bool:
        return self.status is SessionStatus.ACTIVE

    def begin(self) -> None:
        """Enter Active unless the session is already active."""
        if self.is_active:
            raise EditSessionError("An edit session is already active")
        self.status = SessionStatus.ACTIVE

    def commit(self) -> None:
        """Finish an Active session while preserving its committed outcome."""
        if not self.is_active:
            raise EditSessionError("Cannot commit an inactive edit session")
        self.status = SessionStatus.COMMITTED

    def rollback(self) -> None:
        """Finish an Active session while preserving its rollback outcome."""
        if not self.is_active:
            raise EditSessionError("Cannot rollback an inactive edit session")
        self.status = SessionStatus.ROLLED_BACK
