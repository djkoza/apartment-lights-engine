"""Pure models for the apartment lights engine."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum


class LightAction(str, Enum):
    """Single side-effect that may be executed after a decision."""

    TURN_MAIN_ON = "turn_main_on"
    TURN_AMBIENT_ON = "turn_ambient_on"
    TURN_AMBIENT_OFF = "turn_ambient_off"
    TURN_ROOM_OFF = "turn_room_off"
    START_RESTORE_WINDOW = "start_restore_window"
    CANCEL_RESTORE_WINDOW = "cancel_restore_window"
    START_DOOR_GRACE_WINDOW = "start_door_grace_window"
    CANCEL_DOOR_GRACE_WINDOW = "cancel_door_grace_window"


@dataclass(slots=True, frozen=True)
class DecisionSnapshot:
    """Immutable snapshot used by the decision engine."""

    room: str
    cause: str
    auto_enabled: bool
    presence_on: bool
    lux: float
    lux_on_threshold: float
    lux_off_threshold: float
    main_on: bool
    ambient_on: bool
    room_on: bool
    neighbor_main_on: bool
    restore_window_active: bool
    door_grace_window_active: bool
    seconds_since_main_off: float
    main_off_window_seconds: float

    def as_dict(self) -> dict[str, object]:
        """Serialize for logs and service responses."""
        return asdict(self)


@dataclass(slots=True, frozen=True)
class DecisionResult:
    """Decision output produced from a single snapshot."""

    decision: str
    reason: str
    actions: tuple[LightAction, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, object]:
        """Serialize for logs and service responses."""
        return {
            "decision": self.decision,
            "reason": self.reason,
            "actions": [action.value for action in self.actions],
        }
