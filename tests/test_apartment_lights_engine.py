"""Regression tests for the apartment lights engine."""

from __future__ import annotations

import unittest

from custom_components.apartment_lights_engine.const import (
    CAUSE_AUTO_TOGGLE,
    CAUSE_DOOR_OPEN,
    CAUSE_LUX_BRIGHT_STABLE,
    CAUSE_LUX_CHANGED,
    CAUSE_LUX_DARK_STABLE,
    CAUSE_MAIN_OFF,
    CAUSE_MAIN_ON,
    CAUSE_MOTION_OFF,
    CAUSE_MOTION_ON,
    CAUSE_PRESENCE_GRACE_FINISHED,
    CAUSE_ROOM_ON,
    CAUSE_THRESHOLDS_CHANGED,
)
from custom_components.apartment_lights_engine.engine import decide_light_action
from custom_components.apartment_lights_engine.model import DecisionSnapshot, LightAction
from custom_components.apartment_lights_engine.rooms import (
    LEGACY_DEFAULT_ROOM_CONFIGS,
    RoomConfig,
    overlapping_main_and_ambient_entities,
    room_configs_from_storage,
    room_configs_to_storage,
)


def snapshot(**overrides: object) -> DecisionSnapshot:
    """Build a default livingroom-like snapshot for tests."""
    base = dict(
        room="livingroom",
        cause=CAUSE_MOTION_ON,
        auto_enabled=True,
        presence_on=True,
        lux=30.0,
        lux_on_threshold=80.0,
        lux_off_threshold=120.0,
        main_on=False,
        ambient_on=False,
        room_on=False,
        neighbor_main_on=False,
        restore_window_active=False,
        presence_grace_window_active=False,
        seconds_since_main_off=999.0,
        main_off_window_seconds=15.0,
    )
    base.update(overrides)
    return DecisionSnapshot(**base)


class ApartmentLightsEngineTests(unittest.TestCase):
    """High-signal regression cases for the decision engine."""

    def test_manual_main_on_turns_off_ambient(self) -> None:
        result = decide_light_action(snapshot(cause=CAUSE_MAIN_ON, main_on=True, ambient_on=True))
        self.assertEqual(
            result.actions,
            (LightAction.TURN_MAIN_ON, LightAction.TURN_AMBIENT_OFF),
        )

    def test_manual_main_on_clears_pending_restore_but_not_presence_grace(self) -> None:
        result = decide_light_action(
            snapshot(
                cause=CAUSE_MAIN_ON,
                main_on=True,
                ambient_on=True,
                restore_window_active=True,
                presence_grace_window_active=True,
            )
        )
        self.assertEqual(
            result.actions,
            (
                LightAction.TURN_MAIN_ON,
                LightAction.TURN_AMBIENT_OFF,
                LightAction.CANCEL_RESTORE_WINDOW,
            ),
        )

    def test_manual_main_off_while_occupied_goes_to_ambient_when_dark(self) -> None:
        result = decide_light_action(
            snapshot(cause=CAUSE_MAIN_OFF, main_on=False, ambient_on=False, presence_on=True, lux=20.0)
        )
        self.assertEqual(result.actions, (LightAction.TURN_AMBIENT_ON,))

    def test_ambient_turns_off_when_room_gets_bright(self) -> None:
        result = decide_light_action(
            snapshot(cause=CAUSE_LUX_BRIGHT_STABLE, ambient_on=True, lux=150.0)
        )
        self.assertEqual(result.actions, (LightAction.TURN_AMBIENT_OFF,))

    def test_manual_main_off_with_closed_shutter_turns_on_ambient_before_lux_drops(self) -> None:
        result = decide_light_action(
            snapshot(
                cause=CAUSE_MAIN_OFF,
                main_on=False,
                ambient_on=False,
                presence_on=True,
                lux=100.0,
                shutter_closed=True,
            )
        )
        self.assertEqual(result.actions, (LightAction.TURN_AMBIENT_ON,))

    def test_recent_main_off_plus_lux_drop_restores_ambient(self) -> None:
        result = decide_light_action(
            snapshot(
                cause=CAUSE_LUX_CHANGED,
                presence_on=True,
                main_on=False,
                ambient_on=False,
                lux=50.0,
                seconds_since_main_off=4.0,
            )
        )
        self.assertEqual(result.actions, (LightAction.TURN_AMBIENT_ON,))

    def test_dark_entry_prefers_main_when_neighbor_main_is_on(self) -> None:
        result = decide_light_action(
            snapshot(cause=CAUSE_MOTION_ON, presence_on=True, neighbor_main_on=True)
        )
        self.assertEqual(result.actions, (LightAction.TURN_MAIN_ON,))

    def test_dark_entry_prefers_ambient_without_neighbor(self) -> None:
        result = decide_light_action(
            snapshot(cause=CAUSE_DOOR_OPEN, presence_on=False, neighbor_main_on=False)
        )
        self.assertEqual(result.actions, (LightAction.TURN_AMBIENT_ON,))

    def test_threshold_change_dark_reuses_same_main_vs_ambient_logic(self) -> None:
        result = decide_light_action(
            snapshot(cause=CAUSE_THRESHOLDS_CHANGED, presence_on=True, neighbor_main_on=True)
        )
        self.assertEqual(result.actions, (LightAction.TURN_MAIN_ON,))

    def test_motion_off_starts_restore_window_only_when_main_was_on(self) -> None:
        result = decide_light_action(snapshot(cause=CAUSE_MOTION_OFF, main_on=True, room_on=True))
        self.assertEqual(
            result.actions,
            (LightAction.START_RESTORE_WINDOW, LightAction.TURN_ROOM_OFF),
        )

    def test_motion_off_turns_room_off_when_only_ambient_is_on(self) -> None:
        result = decide_light_action(
            snapshot(cause=CAUSE_MOTION_OFF, main_on=False, ambient_on=True, room_on=True)
        )
        self.assertEqual(result.actions, (LightAction.TURN_ROOM_OFF,))

    def test_quick_return_overrides_normal_dark_entry_path(self) -> None:
        """Regression for the failed salon scenario from 2026-04-05."""
        result = decide_light_action(
            snapshot(
                cause=CAUSE_MOTION_ON,
                presence_on=True,
                lux=33.0,
                main_on=False,
                ambient_on=False,
                neighbor_main_on=False,
                restore_window_active=True,
            )
        )
        self.assertEqual(
            result.actions,
            (LightAction.TURN_MAIN_ON, LightAction.CANCEL_RESTORE_WINDOW),
        )

    def test_quick_return_from_door_open_without_presence_only_restores_main(self) -> None:
        result = decide_light_action(
            snapshot(
                cause=CAUSE_DOOR_OPEN,
                presence_on=False,
                lux=33.0,
                main_on=False,
                ambient_on=False,
                neighbor_main_on=False,
                restore_window_active=True,
            )
        )
        self.assertEqual(
            result.actions,
            (LightAction.TURN_MAIN_ON, LightAction.CANCEL_RESTORE_WINDOW),
        )

    def test_motion_on_does_not_start_ambient_if_main_is_already_on(self) -> None:
        """Regression for 2026-04-05: quick return restored main, then motion tried to add ambient."""
        result = decide_light_action(
            snapshot(
                cause=CAUSE_MOTION_ON,
                presence_on=True,
                lux=33.0,
                main_on=True,
                ambient_on=False,
                neighbor_main_on=False,
                restore_window_active=False,
            )
        )
        self.assertEqual(result.actions, ())

    def test_motion_on_confirms_presence_and_cancels_presence_grace(self) -> None:
        result = decide_light_action(
            snapshot(
                cause=CAUSE_MOTION_ON,
                presence_on=True,
                room_on=True,
                ambient_on=True,
                presence_grace_window_active=True,
            )
        )
        self.assertEqual(result.actions, (LightAction.CANCEL_PRESENCE_GRACE_WINDOW,))

    def test_motion_on_confirms_presence_and_cancels_presence_grace_and_restore(self) -> None:
        result = decide_light_action(
            snapshot(
                cause=CAUSE_MOTION_ON,
                presence_on=True,
                room_on=True,
                ambient_on=True,
                presence_grace_window_active=True,
                restore_window_active=True,
            )
        )
        self.assertEqual(
            result.actions,
            (
                LightAction.CANCEL_RESTORE_WINDOW,
                LightAction.CANCEL_PRESENCE_GRACE_WINDOW,
            ),
        )

    def test_room_on_without_presence_starts_presence_grace(self) -> None:
        result = decide_light_action(
            snapshot(
                cause=CAUSE_ROOM_ON,
                presence_on=False,
                room_on=True,
                ambient_on=True,
            )
        )
        self.assertEqual(result.actions, (LightAction.START_PRESENCE_GRACE_WINDOW,))

    def test_presence_grace_finished_turns_room_off_if_presence_never_arrived(self) -> None:
        result = decide_light_action(
            snapshot(
                cause=CAUSE_PRESENCE_GRACE_FINISHED,
                presence_on=False,
                room_on=True,
                ambient_on=True,
            )
        )
        self.assertEqual(result.actions, (LightAction.TURN_ROOM_OFF,))

    def test_presence_grace_finished_turns_room_off_and_cancels_restore(self) -> None:
        result = decide_light_action(
            snapshot(
                cause=CAUSE_PRESENCE_GRACE_FINISHED,
                presence_on=False,
                room_on=True,
                ambient_on=True,
                restore_window_active=True,
            )
        )
        self.assertEqual(
            result.actions,
            (
                LightAction.CANCEL_RESTORE_WINDOW,
                LightAction.TURN_ROOM_OFF,
            ),
        )

    def test_auto_disabled_is_noop(self) -> None:
        result = decide_light_action(snapshot(auto_enabled=False, cause=CAUSE_AUTO_TOGGLE))
        self.assertEqual(result.actions, ())

    def test_invalid_threshold_order_is_noop(self) -> None:
        result = decide_light_action(
            snapshot(
                cause=CAUSE_MOTION_ON,
                lux_on_threshold=120.0,
                lux_off_threshold=80.0,
            )
        )
        self.assertEqual(result.actions, ())
        self.assertEqual(result.reason, "invalid_threshold_order")

    def test_room_configs_roundtrip_storage(self) -> None:
        raw = room_configs_to_storage(LEGACY_DEFAULT_ROOM_CONFIGS)
        restored = room_configs_from_storage(raw)
        self.assertEqual(set(restored), set(LEGACY_DEFAULT_ROOM_CONFIGS))
        self.assertEqual(
            restored["livingroom"].presence_grace_timer_entity,
            "timer.livingroom_presence_grace_window",
        )
        self.assertEqual(
            restored["bedroom"].main_action_entities,
            ("light.raspberry_pi_light_controller_main_bedroom_light",),
        )
        self.assertEqual(
            restored["corridor"].neighbor_main_entities,
            (
                "light.raspberry_pi_light_controller_main_bedroom_light",
                "light.raspberry_pi_light_controller_main_kitchen_light",
                "light.raspberry_pi_light_controller_main_livingroom_light",
            ),
        )
        self.assertEqual(
            restored["kitchen"].neighbor_main_entities,
            (
                "light.raspberry_pi_light_controller_main_livingroom_light",
                "light.raspberry_pi_light_controller_main_corridor_light",
            ),
        )
        self.assertIsNone(restored["livingroom"].shutter_entity)
        self.assertEqual(
            restored["kitchen"].shutter_entity,
            "cover.raspberry_pi_shutter_controller_kitchen_kitchen_shutter",
        )

    def test_room_config_roundtrip_preserves_optional_shutter_entity(self) -> None:
        raw = room_configs_to_storage(
            {
                "bedroom": RoomConfig(
                    room="bedroom",
                    auto_enabled_entity="input_boolean.auto_lights_bedroom",
                    presence_entity="binary_sensor.bedroom_motion_presence",
                    door_entity="binary_sensor.bedroom_door_contact_contact",
                    lux_entity="sensor.bedroom_motion_illuminance",
                    lux_on_threshold_entity="input_number.bedroom_lux_on_threshold",
                    lux_off_threshold_entity="input_number.bedroom_lux_off_threshold",
                    main_state_entity="light.main",
                    main_action_entities=("light.main",),
                    ambient_entity="light.ambient",
                    room_off_entity="light.room",
                    neighbor_main_entities=("light.neighbor",),
                    restore_timer_entity="timer.restore",
                    restore_minutes_entity="input_number.restore",
                    presence_grace_timer_entity="timer.grace",
                    presence_grace_seconds_entity="input_number.grace",
                    shutter_entity="cover.bedroom_shutter",
                )
            }
        )
        restored = room_configs_from_storage(raw)
        self.assertEqual(restored["bedroom"].shutter_entity, "cover.bedroom_shutter")

    def test_room_configs_from_empty_storage(self) -> None:
        self.assertEqual(room_configs_from_storage(None), {})
        self.assertEqual(room_configs_from_storage({}), {})

    def test_overlap_helper_detects_direct_ambient_overlap(self) -> None:
        self.assertEqual(
            overlapping_main_and_ambient_entities(
                ["light.main", "light.ambient"],
                "light.ambient",
            ),
            ("light.ambient",),
        )

    def test_overlap_helper_detects_ambient_group_member_overlap(self) -> None:
        self.assertEqual(
            overlapping_main_and_ambient_entities(
                ["light.main", "light.wled_main"],
                "light.ambient_group",
                ["light.wled_main"],
            ),
            ("light.wled_main",),
        )

    def test_overlap_helper_ignores_distinct_main_and_ambient_paths(self) -> None:
        self.assertEqual(
            overlapping_main_and_ambient_entities(
                ["light.main"],
                "light.ambient_group",
                ["light.other_ambient"],
            ),
            (),
        )


if __name__ == "__main__":
    unittest.main()
