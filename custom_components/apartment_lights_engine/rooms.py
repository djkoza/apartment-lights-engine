"""Static room configuration for the apartment lights engine."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class RoomConfig:
    """Entity mapping for one room."""

    room: str
    auto_enabled_entity: str
    presence_entity: str
    door_entity: str
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
    door_grace_timer_entity: str
    door_grace_seconds_entity: str
    main_off_window_seconds: float = 15.0


ROOM_CONFIGS: dict[str, RoomConfig] = {
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
        door_grace_timer_entity="timer.livingroom_door_grace_window",
        door_grace_seconds_entity="input_number.livingroom_door_grace_seconds",
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
        main_action_entities=(
            "light.raspberry_pi_light_controller_main_bedroom_light",
            "light.bedroom_wled_main",
        ),
        ambient_entity="light.lights_group_bedroom_ambient",
        room_off_entity="light.lights_group_bedroom_all",
        neighbor_main_entities=("light.raspberry_pi_light_controller_main_corridor_light",),
        restore_timer_entity="timer.bedroom_main_restore_window",
        restore_minutes_entity="input_number.bedroom_main_restore_window_minutes",
        door_grace_timer_entity="timer.bedroom_door_grace_window",
        door_grace_seconds_entity="input_number.bedroom_door_grace_seconds",
    ),
}
