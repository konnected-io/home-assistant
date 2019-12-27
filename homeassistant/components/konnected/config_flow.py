"""Config flow for konnected.io integration."""
import asyncio
import logging
import voluptuous as vol
from homeassistant import core, config_entries, exceptions
from homeassistant.const import (
    CONF_HOST,
    CONF_ID,
)
from homeassistant.core import callback

from .const import DOMAIN  # pylint:disable=unused-import

_LOGGER = logging.getLogger(__name__)

KONN_MANUFACTURER = "konnected.io"
KONN_PANEL_MODEL_NAMES = ["Konnected", "Konnected Pro"]

# TODO adjust the data schema to the data that you need
DATA_SCHEMA = vol.Schema({"host": str, "username": str, "password": str})


@callback
def configured_hosts(hass):
    """Return a set of the configured hosts."""
    return set(
        entry.data["host"] for entry in hass.config_entries.async_entries(DOMAIN)
    )


async def validate_input(hass: core.HomeAssistant, data):
    """Validate the user input allows us to connect.

    Data has the keys from DATA_SCHEMA with values provided by the user.
    """
    # TODO validate the data can be used to set up a connection.
    # If you cannot connect:
    # throw CannotConnect
    # If the authentication is wrong:
    # InvalidAuth

    # Return some info we want to store in the config entry.
    return {"title": "Name of the device"}


class KonnectedConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for NEW_NAME."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)

                return self.async_create_entry(title=info["title"], data=user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )

    async def async_step_ssdp(self, discovery_info):
        """Handle a discovered konnected panel.

        This flow is triggered by the SSDP component. It will check if the
        host is already configured and delegate to the import step if not.
        """
        from homeassistant.components.ssdp import ATTR_MANUFACTURER, ATTR_MODEL_NAME

        _LOGGER.error(discovery_info)
        if discovery_info[ATTR_MANUFACTURER] != KONN_MANUFACTURER:
            return self.async_abort(reason="not_konn_panel")

        if not any(
            name in discovery_info.get(ATTR_MODEL_NAME, "")
            for name in KONN_PANEL_MODEL_NAMES
        ):
            return self.async_abort(reason="not_konn_panel")

        host = self.context["host"] = discovery_info.get("host")

        if any(
            host == flow["context"].get("host") for flow in self._async_in_progress()
        ):
            return self.async_abort(reason="already_in_progress")

        if host in configured_hosts(self.hass):
            return self.async_abort(reason="already_configured")

        return self.async_abort(reason="already_configured")
        # return await self.async_step_import(
        #    {
        #        "host": host,
        #    }
        # )

    async def async_step_import(self, import_info):
        """Import a new panel as a config entry.

        This flow is triggered by `async_setup` for both configured and
        discovered panels. Triggered for any panel that does not have a
        config entry yet (based on host).

        This flow is also triggered by `async_step_ssdp`.

        If an existing config file is found, we will validate the info
        and create an entry. Otherwise we will create a new one.
        """
        host = self.context[CONF_HOST] = import_info[CONF_HOST]
        device_id = import_info[CONF_ID]

        # Remove all other entries of panels with same ID or host
        same_panel_entries = [
            entry.entry_id
            for entry in self.hass.config_entries.async_entries(DOMAIN)
            if entry.data[CONF_ID] == device_id or entry.data[CONF_HOST] == host
        ]

        if same_panel_entries:
            await asyncio.wait(
                [
                    self.hass.config_entries.async_remove(entry_id)
                    for entry_id in same_panel_entries
                ]
            )

        return self.async_create_entry(
            title="Konnected.io Alarm Panel", data=import_info,
        )


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(exceptions.HomeAssistantError):
    """Error to indicate there is invalid auth."""
