"""Config flow for Apartment Lights Engine."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector
from homeassistant.util import slugify

from .const import (
    ATTR_ROOM,
    CONF_ALWAYS_DARK,
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
    CONF_ROOMS,
    CONF_SHUTTER_ENTITY,
    CONF_SLEEP_MODE_ENTITY,
    DOMAIN,
)
from .rooms import overlapping_main_and_ambient_entities


ROOM_ID = "room_id"
ACTION_ADD_ROOM = "add_room"
ACTION_EDIT_ROOM = "edit_room"
ACTION_REMOVE_ROOM = "remove_room"


def _rooms_from_entry(entry: config_entries.ConfigEntry) -> dict[str, dict[str, Any]]:
    raw = entry.options.get(CONF_ROOMS)
    if raw is None:
        raw = entry.data.get(CONF_ROOMS, {})
    return dict(raw)


def _room_schema(
    current: dict[str, Any] | None = None,
    *,
    always_dark: bool = False,
) -> vol.Schema:
    """Build one room form schema."""
    current = current or {}
    entity = selector.EntitySelector
    entity_cfg = selector.EntitySelectorConfig
    door_key: Any = vol.Optional(CONF_DOOR_ENTITY)
    if current.get(CONF_DOOR_ENTITY):
        door_key = vol.Optional(CONF_DOOR_ENTITY, default=current[CONF_DOOR_ENTITY])
    shutter_key: Any = vol.Optional(CONF_SHUTTER_ENTITY)
    if current.get(CONF_SHUTTER_ENTITY):
        shutter_key = vol.Optional(CONF_SHUTTER_ENTITY, default=current[CONF_SHUTTER_ENTITY])
    sleep_mode_key: Any = vol.Optional(CONF_SLEEP_MODE_ENTITY)
    if current.get(CONF_SLEEP_MODE_ENTITY):
        sleep_mode_key = vol.Optional(
            CONF_SLEEP_MODE_ENTITY,
            default=current[CONF_SLEEP_MODE_ENTITY],
        )
    schema_fields: dict[Any, Any] = {
        vol.Required(
            CONF_AUTO_ENABLED_ENTITY,
            default=current.get(CONF_AUTO_ENABLED_ENTITY, vol.UNDEFINED),
        ): entity(entity_cfg(domain="input_boolean")),
        vol.Required(
            CONF_PRESENCE_ENTITY,
            default=current.get(CONF_PRESENCE_ENTITY, vol.UNDEFINED),
        ): entity(
            entity_cfg(
                domain="binary_sensor",
                device_class=["motion", "occupancy", "presence"],
            )
        ),
        door_key: entity(entity_cfg(domain="binary_sensor")),
        shutter_key: entity(entity_cfg(domain="cover")),
        sleep_mode_key: entity(
            entity_cfg(domain=["binary_sensor", "input_boolean", "switch"])
        ),
    }

    if not always_dark:
        schema_fields.update(
            {
                vol.Required(
                    CONF_LUX_ENTITY,
                    default=current.get(CONF_LUX_ENTITY, vol.UNDEFINED),
                ): entity(entity_cfg(domain="sensor")),
                vol.Required(
                    CONF_LUX_ON_THRESHOLD_ENTITY,
                    default=current.get(CONF_LUX_ON_THRESHOLD_ENTITY, vol.UNDEFINED),
                ): entity(entity_cfg(domain="input_number")),
                vol.Required(
                    CONF_LUX_OFF_THRESHOLD_ENTITY,
                    default=current.get(CONF_LUX_OFF_THRESHOLD_ENTITY, vol.UNDEFINED),
                ): entity(entity_cfg(domain="input_number")),
            }
        )

    schema_fields.update(
        {
            vol.Required(
                CONF_MAIN_STATE_ENTITY,
                default=current.get(CONF_MAIN_STATE_ENTITY, vol.UNDEFINED),
            ): entity(entity_cfg(domain="light")),
            vol.Required(
                CONF_MAIN_ACTION_ENTITIES,
                default=current.get(CONF_MAIN_ACTION_ENTITIES, []),
            ): entity(entity_cfg(domain="light", multiple=True)),
            vol.Required(
                CONF_AMBIENT_ENTITY,
                default=current.get(CONF_AMBIENT_ENTITY, vol.UNDEFINED),
            ): entity(entity_cfg(domain="light")),
            vol.Required(
                CONF_ROOM_OFF_ENTITY,
                default=current.get(CONF_ROOM_OFF_ENTITY, vol.UNDEFINED),
            ): entity(entity_cfg(domain="light")),
        }
    )

    if not always_dark:
        schema_fields[
            vol.Required(
                CONF_NEIGHBOR_MAIN_ENTITIES,
                default=current.get(CONF_NEIGHBOR_MAIN_ENTITIES, []),
            )
        ] = entity(entity_cfg(domain="light", multiple=True))

    schema_fields.update(
        {
            vol.Required(
                CONF_RESTORE_TIMER_ENTITY,
                default=current.get(CONF_RESTORE_TIMER_ENTITY, vol.UNDEFINED),
            ): entity(entity_cfg(domain="timer")),
            vol.Required(
                CONF_RESTORE_MINUTES_ENTITY,
                default=current.get(CONF_RESTORE_MINUTES_ENTITY, vol.UNDEFINED),
            ): entity(entity_cfg(domain="input_number")),
            vol.Required(
                CONF_PRESENCE_GRACE_TIMER_ENTITY,
                default=current.get(CONF_PRESENCE_GRACE_TIMER_ENTITY, vol.UNDEFINED),
            ): entity(entity_cfg(domain="timer")),
            vol.Required(
                CONF_PRESENCE_GRACE_SECONDS_ENTITY,
                default=current.get(CONF_PRESENCE_GRACE_SECONDS_ENTITY, vol.UNDEFINED),
            ): entity(entity_cfg(domain="input_number")),
            vol.Required(
                CONF_MAIN_OFF_WINDOW_SECONDS,
                default=current.get(CONF_MAIN_OFF_WINDOW_SECONDS, 15.0),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    max=120,
                    step=1,
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
        }
    )

    return vol.Schema(schema_fields)


def _entity_members(hass, entity_id: str) -> tuple[str, ...]:
    """Return child entities when the selected ambient entity is a light group."""
    state = hass.states.get(entity_id) if hass is not None else None
    if state is None:
        return ()

    members = state.attributes.get("entity_id")
    if isinstance(members, str):
        return (members,)
    if isinstance(members, (list, tuple, set)):
        return tuple(member for member in members if isinstance(member, str))
    return ()


class ApartmentLightsEngineConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Apartment Lights Engine."""

    VERSION = 2

    async def async_step_user(self, user_input=None):
        """Create the single config entry."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        return self.async_create_entry(
            title="Apartment Lights Engine",
            data={CONF_ROOMS: {}},
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        return ApartmentLightsEngineOptionsFlow(config_entry)


class ApartmentLightsEngineOptionsFlow(config_entries.OptionsFlow):
    """Edit room mappings for the shared light engine."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._rooms = _rooms_from_entry(config_entry)
        self._room_id: str | None = None
        self._always_dark: bool | None = None

    async def async_step_init(self, user_input=None):
        """Show room management menu."""
        if not self._rooms:
            return await self.async_step_add_room_id()

        return self.async_show_menu(
            step_id="init",
            menu_options=[
                ACTION_ADD_ROOM,
                ACTION_EDIT_ROOM,
                ACTION_REMOVE_ROOM,
            ],
        )

    async def async_step_add_room(self, user_input=None):
        """Route add-room menu action."""
        return await self.async_step_add_room_id()

    async def async_step_add_room_id(self, user_input=None):
        """Ask for a new room id."""
        errors: dict[str, str] = {}
        if user_input is not None:
            room_id = slugify(user_input[ROOM_ID])
            if not room_id:
                errors[ROOM_ID] = "invalid_room_id"
            elif room_id in self._rooms:
                errors[ROOM_ID] = "room_already_exists"
            else:
                self._room_id = room_id
                self._always_dark = False
                return await self.async_step_room_mode()

        schema = vol.Schema(
            {
                vol.Required(ROOM_ID): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                )
            }
        )
        return self.async_show_form(
            step_id="add_room_id",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_edit_room(self, user_input=None):
        """Select one room to edit."""
        if not self._rooms:
            return self.async_abort(reason="no_rooms_configured")

        if user_input is not None:
            self._room_id = user_input[ATTR_ROOM]
            self._always_dark = None
            return await self.async_step_room_mode()

        schema = vol.Schema(
            {
                vol.Required(ATTR_ROOM): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=sorted(self._rooms),
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                )
            }
        )
        return self.async_show_form(step_id="edit_room", data_schema=schema)

    async def async_step_remove_room(self, user_input=None):
        """Remove one configured room."""
        if not self._rooms:
            return self.async_abort(reason="no_rooms_configured")

        if user_input is not None:
            room_id = user_input[ATTR_ROOM]
            self._rooms.pop(room_id, None)
            return self.async_create_entry(title="", data={CONF_ROOMS: self._rooms})

        schema = vol.Schema(
            {
                vol.Required(ATTR_ROOM): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=sorted(self._rooms),
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                )
            }
        )
        return self.async_show_form(step_id="remove_room", data_schema=schema)

    def _current_room(self) -> dict[str, Any]:
        """Return the selected room's current raw config."""
        if self._room_id is None:
            return {}
        return dict(self._rooms.get(self._room_id, {}))

    def _selected_always_dark(self) -> bool:
        """Return the selected always-dark mode for this edit flow."""
        if self._always_dark is not None:
            return self._always_dark
        return bool(self._current_room().get(CONF_ALWAYS_DARK, False))

    async def async_step_room_mode(self, user_input=None):
        """Choose whether this room uses lux-based or always-dark decisions."""
        if user_input is not None:
            self._always_dark = bool(user_input[CONF_ALWAYS_DARK])
            return await self.async_step_room_details()

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_ALWAYS_DARK,
                    default=self._selected_always_dark(),
                ): selector.BooleanSelector()
            }
        )
        return self.async_show_form(
            step_id="room_mode",
            data_schema=schema,
            description_placeholders={"room_id": self._room_id or ""},
        )

    async def async_step_room_details(self, user_input=None):
        """Create or edit one room mapping."""
        errors: dict[str, str] = {}
        always_dark = self._selected_always_dark()
        if user_input is not None:
            if not user_input.get(CONF_MAIN_ACTION_ENTITIES):
                errors[CONF_MAIN_ACTION_ENTITIES] = "required"
            if always_dark:
                user_input[CONF_NEIGHBOR_MAIN_ENTITIES] = []
            elif not user_input.get(CONF_NEIGHBOR_MAIN_ENTITIES):
                # Empty neighbor list is valid. Normalize below.
                user_input[CONF_NEIGHBOR_MAIN_ENTITIES] = []

            overlaps = overlapping_main_and_ambient_entities(
                user_input.get(CONF_MAIN_ACTION_ENTITIES, []),
                user_input[CONF_AMBIENT_ENTITY],
                _entity_members(self.hass, user_input[CONF_AMBIENT_ENTITY]),
            )
            if overlaps:
                errors[CONF_MAIN_ACTION_ENTITIES] = "ambient_overlaps_main_action_entities"

            if not errors and self._room_id is not None:
                cleaned = dict(user_input)
                cleaned[CONF_ALWAYS_DARK] = always_dark
                cleaned[CONF_MAIN_ACTION_ENTITIES] = list(
                    cleaned.get(CONF_MAIN_ACTION_ENTITIES, [])
                )
                if always_dark:
                    cleaned.pop(CONF_LUX_ENTITY, None)
                    cleaned.pop(CONF_LUX_ON_THRESHOLD_ENTITY, None)
                    cleaned.pop(CONF_LUX_OFF_THRESHOLD_ENTITY, None)
                    cleaned.pop(CONF_NEIGHBOR_MAIN_ENTITIES, None)
                else:
                    cleaned[CONF_NEIGHBOR_MAIN_ENTITIES] = list(
                        cleaned.get(CONF_NEIGHBOR_MAIN_ENTITIES, [])
                    )
                self._rooms[self._room_id] = cleaned
                return self.async_create_entry(title="", data={CONF_ROOMS: self._rooms})

        current = self._current_room()

        return self.async_show_form(
            step_id="room_details",
            data_schema=_room_schema(current, always_dark=always_dark),
            errors=errors,
            description_placeholders={"room_id": self._room_id or ""},
        )
