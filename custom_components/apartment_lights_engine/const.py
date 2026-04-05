"""Constants for the apartment lights engine."""

from __future__ import annotations

DOMAIN = "apartment_lights_engine"
SERVICE_EVALUATE_ROOM = "evaluate_room"
EVENT_DECISION = "apartment_lights_engine_decision"

ATTR_ROOM = "room"
ATTR_CAUSE = "cause"
ATTR_DRY_RUN = "dry_run"

CAUSE_MAIN_ON = "main_on"
CAUSE_MAIN_OFF = "main_off"
CAUSE_LUX_BRIGHT_STABLE = "lux_bright_stable"
CAUSE_LUX_DARK_STABLE = "lux_dark_stable"
CAUSE_LUX_CHANGED = "lux_changed"
CAUSE_MOTION_ON = "motion_on"
CAUSE_MOTION_OFF = "motion_off"
CAUSE_DOOR_OPEN = "door_open"
CAUSE_ROOM_ON = "room_on"
CAUSE_PRESENCE_GRACE_FINISHED = "presence_grace_finished"
CAUSE_AUTO_TOGGLE = "auto_toggle"
CAUSE_THRESHOLDS_CHANGED = "thresholds_changed"

CAUSES: tuple[str, ...] = (
    CAUSE_MAIN_ON,
    CAUSE_MAIN_OFF,
    CAUSE_LUX_BRIGHT_STABLE,
    CAUSE_LUX_DARK_STABLE,
    CAUSE_LUX_CHANGED,
    CAUSE_MOTION_ON,
    CAUSE_MOTION_OFF,
    CAUSE_DOOR_OPEN,
    CAUSE_ROOM_ON,
    CAUSE_PRESENCE_GRACE_FINISHED,
    CAUSE_AUTO_TOGGLE,
    CAUSE_THRESHOLDS_CHANGED,
)
