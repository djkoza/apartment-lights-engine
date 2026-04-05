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
    CAUSE_PRESENCE_GRACE_FINISHED,
    CAUSE_ROOM_ON,
    CAUSE_THRESHOLDS_CHANGED,
)
from .model import DecisionResult, DecisionSnapshot, LightAction


def _noop(reason: str) -> DecisionResult:
    return DecisionResult(decision="noop", reason=reason, actions=())


def _main_on(
    reason: str,
    *,
    turn_off_ambient: bool = False,
    cancel_restore: bool = False,
) -> DecisionResult:
    actions = [LightAction.TURN_MAIN_ON]
    if turn_off_ambient:
        actions.append(LightAction.TURN_AMBIENT_OFF)
    if cancel_restore:
        actions.append(LightAction.CANCEL_RESTORE_WINDOW)
    return DecisionResult(decision="turn_main_on", reason=reason, actions=tuple(actions))


def _ambient_on(reason: str) -> DecisionResult:
    actions = [LightAction.TURN_AMBIENT_ON]
    return DecisionResult(
        decision="turn_ambient_on",
        reason=reason,
        actions=tuple(actions),
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


def _room_off(
    reason: str,
    *,
    start_restore: bool = False,
    cancel_restore: bool = False,
    cancel_presence_grace: bool = False,
) -> DecisionResult:
    actions: list[LightAction] = []
    if start_restore:
        actions.append(LightAction.START_RESTORE_WINDOW)
    if cancel_restore:
        actions.append(LightAction.CANCEL_RESTORE_WINDOW)
    if cancel_presence_grace:
        actions.append(LightAction.CANCEL_PRESENCE_GRACE_WINDOW)
    actions.append(LightAction.TURN_ROOM_OFF)
    return DecisionResult(decision="turn_room_off", reason=reason, actions=tuple(actions))


def _start_presence_grace(reason: str) -> DecisionResult:
    return DecisionResult(
        decision="start_presence_grace_window",
        reason=reason,
        actions=(LightAction.START_PRESENCE_GRACE_WINDOW,),
    )


def _cancel_presence_grace(reason: str, *, cancel_restore: bool = False) -> DecisionResult:
    actions = []
    if cancel_restore:
        actions.append(LightAction.CANCEL_RESTORE_WINDOW)
    actions.append(LightAction.CANCEL_PRESENCE_GRACE_WINDOW)
    return DecisionResult(
        decision="cancel_presence_grace_window",
        reason=reason,
        actions=tuple(actions),
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

    if (
        snapshot.cause == CAUSE_MOTION_ON
        and snapshot.presence_grace_window_active
        and snapshot.room_on
    ):
        return _cancel_presence_grace(
            "presence_confirmed_after_room_turned_on",
            cancel_restore=snapshot.restore_window_active,
        )

    if snapshot.cause == CAUSE_ROOM_ON:
        if snapshot.room_on and not snapshot.presence_on and not snapshot.presence_grace_window_active:
            return _start_presence_grace("room_turned_on_without_presence_starts_grace_window")
        return _noop("room_turned_on_but_presence_already_confirmed_or_grace_active")

    if snapshot.cause == CAUSE_MOTION_OFF:
        if snapshot.main_on:
            return _room_off(
                "presence_lost_turns_room_off_and_starts_restore_window",
                start_restore=True,
                cancel_presence_grace=snapshot.presence_grace_window_active,
            )
        if snapshot.room_on:
            return _room_off(
                "presence_lost_turns_room_off",
                cancel_presence_grace=snapshot.presence_grace_window_active,
            )
        return _noop("presence_lost_but_room_already_off")

    if snapshot.cause == CAUSE_MAIN_ON:
        if snapshot.ambient_on or snapshot.restore_window_active:
            if snapshot.ambient_on and snapshot.restore_window_active:
                reason = "manual_main_on_syncs_cluster_turns_off_ambient_and_clears_restore_timer"
            elif snapshot.ambient_on:
                reason = "manual_main_on_syncs_cluster_and_turns_off_ambient"
            else:
                reason = "manual_main_on_syncs_cluster_and_clears_restore_timer"
            return _main_on(
                reason,
                turn_off_ambient=snapshot.ambient_on,
                cancel_restore=snapshot.restore_window_active,
            )
        return _main_on("manual_main_on_syncs_cluster")

    if snapshot.cause == CAUSE_MAIN_OFF:
        if snapshot.presence_on and not snapshot.ambient_on:
            if dark:
                return _ambient_on("manual_main_off_while_occupied_switches_to_ambient")
            if snapshot.shutter_closed:
                return _ambient_on(
                    "manual_main_off_with_closed_shutter_switches_to_ambient_without_waiting_for_lux"
                )
        return _noop("main_off_without_dark_occupied_fallback")

    if snapshot.cause == CAUSE_PRESENCE_GRACE_FINISHED:
        if snapshot.room_on and not snapshot.presence_on:
            return _room_off(
                "room_on_without_presence_times_out",
                cancel_restore=snapshot.restore_window_active,
            )
        return _noop("presence_grace_finished_but_room_confirmed_or_already_off")

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
        return _main_on(
            "quick_return_restores_main",
            cancel_restore=True,
        )

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
            return DecisionResult(
                decision="turn_main_on",
                reason="entry_path_prefers_main_due_to_neighbor",
                actions=(LightAction.TURN_MAIN_ON,),
            )
        return _ambient_on("entry_path_prefers_ambient_without_neighbor")

    return _noop("no_rule_matched")
