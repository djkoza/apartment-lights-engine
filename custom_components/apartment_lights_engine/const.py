"""Constants for the apartment lights engine."""

from __future__ import annotations

DOMAIN = "apartment_lights_engine"
SERVICE_EVALUATE_ROOM = "evaluate_room"
EVENT_DECISION = "apartment_lights_engine_decision"

ATTR_ROOM = "room"
ATTR_CAUSE = "cause"
ATTR_DRY_RUN = "dry_run"

CONF_ROOMS = "rooms"
CONF_AUTO_ENABLED_ENTITY = "auto_enabled_entity"
CONF_PRESENCE_ENTITY = "presence_entity"
CONF_DOOR_ENTITY = "door_entity"
CONF_LUX_ENTITY = "lux_entity"
CONF_LUX_ON_THRESHOLD_ENTITY = "lux_on_threshold_entity"
CONF_LUX_OFF_THRESHOLD_ENTITY = "lux_off_threshold_entity"
CONF_MAIN_STATE_ENTITY = "main_state_entity"
CONF_MAIN_ACTION_ENTITIES = "main_action_entities"
CONF_AMBIENT_ENTITY = "ambient_entity"
CONF_ROOM_OFF_ENTITY = "room_off_entity"
CONF_NEIGHBOR_MAIN_ENTITIES = "neighbor_main_entities"
CONF_RESTORE_TIMER_ENTITY = "restore_timer_entity"
CONF_RESTORE_MINUTES_ENTITY = "restore_minutes_entity"
CONF_PRESENCE_GRACE_TIMER_ENTITY = "presence_grace_timer_entity"
CONF_PRESENCE_GRACE_SECONDS_ENTITY = "presence_grace_seconds_entity"
CONF_MAIN_OFF_WINDOW_SECONDS = "main_off_window_seconds"

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
