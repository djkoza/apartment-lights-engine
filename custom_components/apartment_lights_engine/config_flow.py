"""Config flow for Apartment Lights Engine."""

from __future__ import annotations

from homeassistant import config_entries

from .const import DOMAIN


class ApartmentLightsEngineConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Apartment Lights Engine."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Create the single config entry."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        return self.async_create_entry(
            title="Apartment Lights Engine",
            data={},
        )
