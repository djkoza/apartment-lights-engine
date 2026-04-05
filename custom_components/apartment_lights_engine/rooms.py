"""Room configuration helpers for the apartment lights engine."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .const import (
    CONF_AMBIENT_ENTITY,
    CONF_AUTO_ENABLED_ENTITY,
    CONF_DOOR_ENTITY,
    CONF_LUX_ENTITY,
    CONF_LUX_OFF_THRESHOLD_ENTITY,
    CONF_LUX_ON_THRESHOLD_ENTITY,
    CONF_MAIN_ACTION_ENTITIES,
    CONF_MAIN_OFF_WINDOW_SECONDS,
    CONF_MAIN_STATE_ENTITY,
    CONF_NEIGHBOR_MAIN_ENTITIES,
    CONF_PRESENCE_ENTITY,
    CONF_PRESENCE_GRACE_SECONDS_ENTITY,
    CONF_PRESENCE_GRACE_TIMER_ENTITY,
    CONF_RESTORE_MINUTES_ENTITY,
    CONF_RESTORE_TIMER_ENTITY,
    CONF_ROOM_OFF_ENTITY,
    CONF_SHUTTER_ENTITY,
)


@dataclass(slots=True, frozen=True)
class RoomConfig:
    """Entity mapping for one room."""

    room: str
    auto_enabled_entity: str
    presence_entity: str
    door_entity: str | None
    lux_entity: str
    lux_on_threshold_entity: str
    lux_off_threshold_entity: str
    main_state_entity: str
    main_action_entities: tuple[str, ...]
    ambient_entity: str
    room_off_entity: str
    neighbor_main_entities: tuple[str, ...]
    restore_timer_entity: str
    restore_minutes_entity: str
    presence_grace_timer_entity: str
    presence_grace_seconds_entity: str
    main_off_window_seconds: float = 15.0
    shutter_entity: str | None = None


def overlapping_main_and_ambient_entities(
    main_action_entities: tuple[str, ...] | list[str],
    ambient_entity: str,
    ambient_members: tuple[str, ...] | list[str] = (),
) -> tuple[str, ...]:
    """Return direct or group-member overlaps between main and ambient paths."""
    main_entities = tuple(entity_id for entity_id in main_action_entities if entity_id)
    ambient_member_set = {entity_id for entity_id in ambient_members if entity_id}

    overlaps = {
        entity_id
        for entity_id in main_entities
        if entity_id == ambient_entity or entity_id in ambient_member_set
    }
    return tuple(sorted(overlaps))


def room_config_to_dict(room: RoomConfig) -> dict[str, Any]:
    """Serialize one room config for config entry storage."""
    data = asdict(room)
    data[CONF_MAIN_ACTION_ENTITIES] = list(room.main_action_entities)
    data[CONF_NEIGHBOR_MAIN_ENTITIES] = list(room.neighbor_main_entities)
    return data


def room_config_from_dict(room_id: str, raw: dict[str, Any]) -> RoomConfig:
    """Deserialize one room config from config entry storage."""
    return RoomConfig(
        room=room_id,
        auto_enabled_entity=raw[CONF_AUTO_ENABLED_ENTITY],
        presence_entity=raw[CONF_PRESENCE_ENTITY],
        door_entity=raw.get(CONF_DOOR_ENTITY) or None,
        lux_entity=raw[CONF_LUX_ENTITY],
        lux_on_threshold_entity=raw[CONF_LUX_ON_THRESHOLD_ENTITY],
        lux_off_threshold_entity=raw[CONF_LUX_OFF_THRESHOLD_ENTITY],
        main_state_entity=raw[CONF_MAIN_STATE_ENTITY],
        main_action_entities=tuple(raw.get(CONF_MAIN_ACTION_ENTITIES, [])),
        ambient_entity=raw[CONF_AMBIENT_ENTITY],
        room_off_entity=raw[CONF_ROOM_OFF_ENTITY],
        neighbor_main_entities=tuple(raw.get(CONF_NEIGHBOR_MAIN_ENTITIES, [])),
        restore_timer_entity=raw[CONF_RESTORE_TIMER_ENTITY],
        restore_minutes_entity=raw[CONF_RESTORE_MINUTES_ENTITY],
        presence_grace_timer_entity=raw[CONF_PRESENCE_GRACE_TIMER_ENTITY],
        presence_grace_seconds_entity=raw[CONF_PRESENCE_GRACE_SECONDS_ENTITY],
        main_off_window_seconds=float(raw.get(CONF_MAIN_OFF_WINDOW_SECONDS, 15.0)),
        shutter_entity=raw.get(CONF_SHUTTER_ENTITY) or None,
    )


def room_configs_to_storage(rooms: dict[str, RoomConfig]) -> dict[str, dict[str, Any]]:
    """Serialize room configs for config entries."""
    return {room_id: room_config_to_dict(cfg) for room_id, cfg in rooms.items()}


def room_configs_from_storage(raw: dict[str, Any] | None) -> dict[str, RoomConfig]:
    """Deserialize room configs from config entries."""
    if not raw:
        return {}
    return {
        room_id: room_config_from_dict(room_id, room_raw)
        for room_id, room_raw in raw.items()
        if isinstance(room_raw, dict)
    }


# Legacy bootstrap defaults used only to migrate existing installs that were created
# before room mappings were stored in the config entry.
LEGACY_DEFAULT_ROOM_CONFIGS: dict[str, RoomConfig] = {
    "livingroom": RoomConfig(
        room="livingroom",
        auto_enabled_entity="input_boolean.auto_lights_livingroom",
        presence_entity="binary_sensor.livingroom_motion_presence",
        door_entity="binary_sensor.livingroom_door_contact_contact",
        lux_entity="sensor.livingroom_motion_illuminance",
        lux_on_threshold_entity="input_number.livingroom_lux_on_threshold",
        lux_off_threshold_entity="input_number.livingroom_lux_off_threshold",
        main_state_entity="light.raspberry_pi_light_controller_main_livingroom_light",
        main_action_entities=(
            "light.raspberry_pi_light_controller_main_livingroom_light",
            "light.livingroom_wled_main",
        ),
        ambient_entity="light.lights_group_livingroom_ambient",
        room_off_entity="light.lights_group_livingroom_all",
        neighbor_main_entities=(
            "light.raspberry_pi_light_controller_main_corridor_light",
            "light.raspberry_pi_light_controller_main_kitchen_light",
        ),
        restore_timer_entity="timer.livingroom_main_restore_window",
        restore_minutes_entity="input_number.livingroom_main_restore_window_minutes",
        presence_grace_timer_entity="timer.livingroom_presence_grace_window",
        presence_grace_seconds_entity="input_number.livingroom_presence_grace_seconds",
    ),
    "bedroom": RoomConfig(
        room="bedroom",
        auto_enabled_entity="input_boolean.auto_lights_bedroom",
        presence_entity="binary_sensor.bedroom_motion_presence",
        door_entity="binary_sensor.bedroom_door_contact_contact",
        lux_entity="sensor.bedroom_motion_illuminance",
        lux_on_threshold_entity="input_number.bedroom_lux_on_threshold",
        lux_off_threshold_entity="input_number.bedroom_lux_off_threshold",
        main_state_entity="light.raspberry_pi_light_controller_main_bedroom_light",
        main_action_entities=("light.raspberry_pi_light_controller_main_bedroom_light",),
        ambient_entity="light.lights_group_bedroom_ambient",
        room_off_entity="light.lights_group_bedroom_all",
        neighbor_main_entities=("light.raspberry_pi_light_controller_main_corridor_light",),
        restore_timer_entity="timer.bedroom_main_restore_window",
        restore_minutes_entity="input_number.bedroom_main_restore_window_minutes",
        presence_grace_timer_entity="timer.bedroom_presence_grace_window",
        presence_grace_seconds_entity="input_number.bedroom_presence_grace_seconds",
    ),
    "corridor": RoomConfig(
        room="corridor",
        auto_enabled_entity="input_boolean.auto_lights_corridor",
        presence_entity="binary_sensor.corridor_motion_presence",
        door_entity="binary_sensor.entrance_door_contact_contact",
        lux_entity="sensor.corridor_motion_illuminance",
        lux_on_threshold_entity="input_number.corridor_lux_on_threshold",
        lux_off_threshold_entity="input_number.corridor_lux_off_threshold",
        main_state_entity="light.raspberry_pi_light_controller_main_corridor_light",
        main_action_entities=("light.raspberry_pi_light_controller_main_corridor_light",),
        ambient_entity="light.lights_group_corridor_ambient",
        room_off_entity="light.lights_group_corridor_all",
        neighbor_main_entities=(
            "light.raspberry_pi_light_controller_main_bedroom_light",
            "light.raspberry_pi_light_controller_main_kitchen_light",
            "light.raspberry_pi_light_controller_main_livingroom_light",
        ),
        restore_timer_entity="timer.corridor_main_restore_window",
        restore_minutes_entity="input_number.corridor_main_restore_window_minutes",
        presence_grace_timer_entity="timer.corridor_presence_grace_window",
        presence_grace_seconds_entity="input_number.corridor_presence_grace_seconds",
    ),
    "kitchen": RoomConfig(
        room="kitchen",
        auto_enabled_entity="input_boolean.auto_lights_kitchen",
        presence_entity="binary_sensor.kitchen_motion_presence",
        door_entity=None,
        lux_entity="sensor.kitchen_motion_illuminance",
        lux_on_threshold_entity="input_number.kitchen_lux_on_threshold",
        lux_off_threshold_entity="input_number.kitchen_lux_off_threshold",
        main_state_entity="light.raspberry_pi_light_controller_main_kitchen_light",
        main_action_entities=("light.raspberry_pi_light_controller_main_kitchen_light",),
        ambient_entity="light.lights_group_kitchen_ambient",
        room_off_entity="light.lights_group_kitchen_all",
        neighbor_main_entities=(
            "light.raspberry_pi_light_controller_main_livingroom_light",
            "light.raspberry_pi_light_controller_main_corridor_light",
        ),
        restore_timer_entity="timer.kitchen_main_restore_window",
        restore_minutes_entity="input_number.kitchen_main_restore_window_minutes",
        presence_grace_timer_entity="timer.kitchen_presence_grace_window",
        presence_grace_seconds_entity="input_number.kitchen_presence_grace_seconds",
        shutter_entity="cover.raspberry_pi_shutter_controller_kitchen_kitchen_shutter",
    ),
}
