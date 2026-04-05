"""Pure decision engine for room lighting."""

from __future__ import annotations

from .const import (
    CAUSE_AUTO_TOGGLE,
    CAUSE_DOOR_OPEN,
    CAUSE_LUX_BRIGHT_STABLE,
    CAUSE_LUX_CHANGED,
    CAUSE_LUX_DARK_STABLE,
    CAUSE_MAIN_OFF,
    CAUSE_MAIN_ON,
    CAUSE_MOTION_OFF,
    CAUSE_MOTION_ON,
    CAUSE_THRESHOLDS_CHANGED,
)
from .model import DecisionResult, DecisionSnapshot, LightAction


def _noop(reason: str) -> DecisionResult:
    return DecisionResult(decision="noop", reason=reason, actions=())


def _main_on(reason: str, *, cancel_restore: bool = False) -> DecisionResult:
    actions = [LightAction.TURN_MAIN_ON]
    if cancel_restore:
        actions.append(LightAction.CANCEL_RESTORE_WINDOW)
    return DecisionResult(decision="turn_main_on", reason=reason, actions=tuple(actions))


def _ambient_on(reason: str) -> DecisionResult:
    return DecisionResult(
        decision="turn_ambient_on",
        reason=reason,
        actions=(LightAction.TURN_AMBIENT_ON,),
    )


def _ambient_off(reason: str) -> DecisionResult:
    return DecisionResult(
        decision="turn_ambient_off",
        reason=reason,
        actions=(LightAction.TURN_AMBIENT_OFF,),
    )


def _start_restore(reason: str) -> DecisionResult:
    return DecisionResult(
        decision="start_restore_window",
        reason=reason,
        actions=(LightAction.START_RESTORE_WINDOW,),
    )


def decide_light_action(snapshot: DecisionSnapshot) -> DecisionResult:
    """Return one deterministic decision for a single trigger cause."""

    if snapshot.lux_on_threshold >= snapshot.lux_off_threshold:
        return _noop("invalid_threshold_order")

    dark = snapshot.lux < snapshot.lux_on_threshold
    bright = snapshot.lux > snapshot.lux_off_threshold
    main_recently_off = (
        not snapshot.main_on
        and snapshot.seconds_since_main_off <= snapshot.main_off_window_seconds
    )

    if not snapshot.auto_enabled:
        return _noop("auto_disabled")

    if snapshot.cause == CAUSE_MOTION_OFF:
        if snapshot.main_on:
            return _start_restore("presence_lost_while_main_was_on")
        return _noop("presence_lost_but_main_already_off")

    if snapshot.cause == CAUSE_MAIN_ON:
        if snapshot.ambient_on:
            return DecisionResult(
                decision="sync_main_and_turn_off_ambient",
                reason="manual_main_on_syncs_cluster_and_turns_off_ambient",
                actions=(LightAction.TURN_MAIN_ON, LightAction.TURN_AMBIENT_OFF),
            )
        return _main_on("manual_main_on_syncs_cluster")

    if snapshot.cause == CAUSE_MAIN_OFF:
        if snapshot.presence_on and not snapshot.ambient_on and dark:
            return _ambient_on("manual_main_off_while_occupied_switches_to_ambient")
        return _noop("main_off_without_dark_occupied_fallback")

    if snapshot.ambient_on and (
        snapshot.cause == CAUSE_LUX_BRIGHT_STABLE
        or (snapshot.cause == CAUSE_THRESHOLDS_CHANGED and bright)
    ):
        return _ambient_off("ambient_off_when_room_is_bright")

    if (
        snapshot.restore_window_active
        and snapshot.cause in {CAUSE_MOTION_ON, CAUSE_DOOR_OPEN}
        and not snapshot.main_on
        and dark
    ):
        return _main_on("quick_return_restores_main", cancel_restore=True)

    if (
        snapshot.cause == CAUSE_LUX_CHANGED
        and snapshot.presence_on
        and not snapshot.ambient_on
        and not snapshot.main_on
        and dark
        and main_recently_off
    ):
        return _ambient_on("lux_drop_after_recent_main_off_restores_ambient")

    if (
        (
            snapshot.cause == CAUSE_LUX_DARK_STABLE
            or (snapshot.cause == CAUSE_THRESHOLDS_CHANGED and dark)
        )
        and snapshot.presence_on
        and not snapshot.main_on
        and not snapshot.ambient_on
    ):
        if snapshot.neighbor_main_on:
            return _main_on("dark_room_with_neighbor_main_on")
        return _ambient_on("dark_room_without_neighbor_main_on")

    if (
        snapshot.cause
        in {
            CAUSE_MOTION_ON,
            CAUSE_DOOR_OPEN,
            CAUSE_AUTO_TOGGLE,
            CAUSE_THRESHOLDS_CHANGED,
        }
        and dark
        and (snapshot.presence_on or snapshot.cause == CAUSE_DOOR_OPEN)
        and not snapshot.main_on
        and not snapshot.ambient_on
    ):
        if snapshot.neighbor_main_on:
            return _main_on("entry_path_prefers_main_due_to_neighbor")
        return _ambient_on("entry_path_prefers_ambient_without_neighbor")

    return _noop("no_rule_matched")
