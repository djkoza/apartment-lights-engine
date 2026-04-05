"""Home Assistant adapter for the apartment lights engine."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from .const import (
    ATTR_CAUSE,
    ATTR_DRY_RUN,
    ATTR_ROOM,
    CAUSES,
    DOMAIN,
    EVENT_DECISION,
    SERVICE_EVALUATE_ROOM,
)
from .engine import decide_light_action
from .model import DecisionSnapshot, LightAction
from .rooms import ROOM_CONFIGS, RoomConfig

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the apartment lights engine."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry) -> bool:
    """Set up the apartment lights engine from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    await _async_register_services(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry) -> bool:
    """Unload the apartment lights engine config entry."""
    entries = hass.config_entries.async_entries(DOMAIN)
    if len(entries) <= 1 and hass.services.has_service(DOMAIN, SERVICE_EVALUATE_ROOM):
        hass.services.async_remove(DOMAIN, SERVICE_EVALUATE_ROOM)
        hass.data.get(DOMAIN, {}).pop("service_registered", None)
    return True


async def _async_register_services(hass: HomeAssistant) -> None:
    import voluptuous as vol

    from homeassistant.helpers import config_validation as cv

    if hass.data[DOMAIN].get("service_registered"):
        return

    service_evaluate_schema = vol.Schema(
        {
            vol.Required(ATTR_ROOM): vol.In(sorted(ROOM_CONFIGS)),
            vol.Required(ATTR_CAUSE): vol.In(CAUSES),
            vol.Optional(ATTR_DRY_RUN, default=False): cv.boolean,
        }
    )

    try:
        from homeassistant.core import ServiceCall, SupportsResponse
    except ImportError:  # pragma: no cover - compatibility path
        from homeassistant.core import ServiceCall

        SupportsResponse = None

    async def async_handle_evaluate(call: ServiceCall) -> dict[str, object] | None:
        room = call.data[ATTR_ROOM]
        cause = call.data[ATTR_CAUSE]
        dry_run = call.data[ATTR_DRY_RUN]
        room_config = ROOM_CONFIGS[room]
        snapshot = _build_snapshot(hass, room_config, cause)
        decision = decide_light_action(snapshot)

        payload = {
            "room": room,
            "cause": cause,
            "snapshot": snapshot.as_dict(),
            "decision": decision.as_dict(),
            "dry_run": dry_run,
        }
        hass.bus.async_fire(EVENT_DECISION, payload)
        _LOGGER.info(
            "Apartment lights decision room=%s cause=%s decision=%s reason=%s actions=%s",
            room,
            cause,
            decision.decision,
            decision.reason,
            [action.value for action in decision.actions],
        )
        if decision.reason == "invalid_threshold_order":
            _LOGGER.warning(
                "Apartment lights invalid threshold order room=%s lux_on_threshold=%s lux_off_threshold=%s",
                room,
                snapshot.lux_on_threshold,
                snapshot.lux_off_threshold,
            )

        if not dry_run:
            await _async_execute_actions(hass, room_config, decision.actions)

        if SupportsResponse is not None:
            return payload
        return None

    register_kwargs: dict[str, Any] = {
        "schema": service_evaluate_schema,
    }
    if SupportsResponse is not None:
        register_kwargs["supports_response"] = SupportsResponse.OPTIONAL

    hass.services.async_register(
        DOMAIN,
        SERVICE_EVALUATE_ROOM,
        async_handle_evaluate,
        **register_kwargs,
    )
    hass.data[DOMAIN]["service_registered"] = True


def _build_snapshot(hass: HomeAssistant, room: RoomConfig, cause: str) -> DecisionSnapshot:
    """Create one immutable snapshot before any action is executed."""
    main_state = hass.states.get(room.main_state_entity)
    seconds_since_main_off = room.main_off_window_seconds + 1
    if main_state is not None and main_state.state == "off":
        seconds_since_main_off = _seconds_since_last_changed(hass, room.main_state_entity)

    return DecisionSnapshot(
        room=room.room,
        cause=cause,
        auto_enabled=_is_on(hass, room.auto_enabled_entity),
        presence_on=_is_on(hass, room.presence_entity),
        lux=_float_state(hass, room.lux_entity, default=999.0),
        lux_on_threshold=_float_state(hass, room.lux_on_threshold_entity, default=80.0),
        lux_off_threshold=_float_state(hass, room.lux_off_threshold_entity, default=120.0),
        main_on=_is_on(hass, room.main_state_entity),
        ambient_on=_is_on(hass, room.ambient_entity),
        neighbor_main_on=any(_is_on(hass, entity_id) for entity_id in room.neighbor_main_entities),
        restore_window_active=_state(hass, room.restore_timer_entity) == "active",
        seconds_since_main_off=seconds_since_main_off,
        main_off_window_seconds=room.main_off_window_seconds,
    )


def _state(hass: HomeAssistant, entity_id: str) -> str:
    state = hass.states.get(entity_id)
    return state.state if state is not None else "unknown"


def _is_on(hass: HomeAssistant, entity_id: str) -> bool:
    return _state(hass, entity_id) == "on"


def _float_state(hass: HomeAssistant, entity_id: str, *, default: float) -> float:
    state = hass.states.get(entity_id)
    if state is None:
        return default
    try:
        return float(state.state)
    except (TypeError, ValueError):
        return default


def _seconds_since_last_changed(hass: HomeAssistant, entity_id: str) -> float:
    state = hass.states.get(entity_id)
    if state is None or state.last_changed is None:
        return 0.0
    from homeassistant.util import dt as dt_util

    delta = dt_util.utcnow() - state.last_changed
    return max(0.0, delta.total_seconds())


async def _async_execute_actions(
    hass: HomeAssistant,
    room: RoomConfig,
    actions: tuple[LightAction, ...],
) -> None:
    """Execute one precomputed plan without branching."""
    from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
    from homeassistant.components.timer import DOMAIN as TIMER_DOMAIN
    from homeassistant.const import CONF_ENTITY_ID

    for action in actions:
        if action == LightAction.TURN_MAIN_ON:
            await hass.services.async_call(
                LIGHT_DOMAIN,
                "turn_on",
                {CONF_ENTITY_ID: list(room.main_action_entities)},
                blocking=True,
            )
        elif action == LightAction.TURN_AMBIENT_ON:
            await hass.services.async_call(
                LIGHT_DOMAIN,
                "turn_on",
                {CONF_ENTITY_ID: room.ambient_entity},
                blocking=True,
            )
        elif action == LightAction.TURN_AMBIENT_OFF:
            await hass.services.async_call(
                LIGHT_DOMAIN,
                "turn_off",
                {CONF_ENTITY_ID: room.ambient_entity},
                blocking=True,
            )
        elif action == LightAction.START_RESTORE_WINDOW:
            minutes = max(
                1,
                int(round(_float_state(hass, room.restore_minutes_entity, default=5.0))),
            )
            await hass.services.async_call(
                TIMER_DOMAIN,
                "start",
                {
                    CONF_ENTITY_ID: room.restore_timer_entity,
                    "duration": str(timedelta(minutes=minutes)),
                },
                blocking=True,
            )
        elif action == LightAction.CANCEL_RESTORE_WINDOW:
            await hass.services.async_call(
                TIMER_DOMAIN,
                "cancel",
                {CONF_ENTITY_ID: room.restore_timer_entity},
                blocking=True,
            )
