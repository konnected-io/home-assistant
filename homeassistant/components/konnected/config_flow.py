"""Config flow for konnected.io integration."""
import asyncio
import logging
from collections import OrderedDict
import voluptuous as vol

from homeassistant import config_entries, exceptions
from homeassistant.const import (
    CONF_HOST,
    CONF_ID,
)
from homeassistant.core import callback
from homeassistant.components.binary_sensor import (
    DEVICE_CLASS_DOOR,
    DEVICE_CLASSES as BIN_SENS_TYPES,
)

from .const import DOMAIN  # pylint:disable=unused-import

_LOGGER = logging.getLogger(__name__)

KONN_MANUFACTURER = "konnected.io"
KONN_MODEL = "Konnected"
KONN_MODEL_PRO = "Konnected Pro"
KONN_PANEL_MODEL_NAMES = [KONN_MODEL, KONN_MODEL_PRO]

DATA_SCHEMA_MANUAL = OrderedDict()
DATA_SCHEMA_MANUAL[vol.Required("host")] = str
DATA_SCHEMA_MANUAL[vol.Required("port")] = int


DATA_SCHEMA_KONN_MODEL = OrderedDict()
DATA_SCHEMA_KONN_MODEL[vol.Required("1", default="Disabled")] = vol.In(
    ["Disabled", "Binary Sensor", "Digital Sensor", "Switchable Output"]
)
DATA_SCHEMA_KONN_MODEL[vol.Required("2", default="Disabled")] = vol.In(
    ["Disabled", "Binary Sensor", "Digital Sensor", "Switchable Output"]
)
DATA_SCHEMA_KONN_MODEL[vol.Required("3", default="Disabled")] = vol.In(
    ["Disabled", "Binary Sensor", "Digital Sensor", "Switchable Output"]
)
DATA_SCHEMA_KONN_MODEL[vol.Required("4", default="Disabled")] = vol.In(
    ["Disabled", "Binary Sensor", "Digital Sensor", "Switchable Output"]
)
DATA_SCHEMA_KONN_MODEL[vol.Required("5", default="Disabled")] = vol.In(
    ["Disabled", "Binary Sensor", "Digital Sensor", "Switchable Output"]
)
DATA_SCHEMA_KONN_MODEL[vol.Required("6", default="Disabled")] = vol.In(
    ["Disabled", "Binary Sensor", "Digital Sensor", "Switchable Output"]
)
DATA_SCHEMA_KONN_MODEL[vol.Required("7", default="Disabled")] = vol.In(
    ["Disabled", "Binary Sensor", "Digital Sensor", "Switchable Output"]
)
DATA_SCHEMA_KONN_MODEL[vol.Required("8", default="Disabled")] = vol.In(
    ["Disabled", "Binary Sensor", "Digital Sensor", "Switchable Output"]
)
DATA_SCHEMA_KONN_MODEL[vol.Required("9", default="Disabled")] = vol.In(
    ["Disabled", "Binary Sensor", "Digital Sensor"]
)
DATA_SCHEMA_KONN_MODEL[vol.Required("11", default="Disabled")] = vol.In(
    ["Disabled", "Binary Sensor", "Digital Sensor"]
)
DATA_SCHEMA_KONN_MODEL[vol.Required("12", default="Disabled")] = vol.In(
    ["Disabled", "Binary Sensor", "Digital Sensor"]
)
DATA_SCHEMA_KONN_MODEL[vol.Required("alarm1", default="Disabled")] = vol.In(
    ["Disabled", "Switchable Output"]
)
DATA_SCHEMA_KONN_MODEL[vol.Required("out1", default="Disabled")] = vol.In(
    ["Disabled", "Switchable Output"]
)
DATA_SCHEMA_KONN_MODEL[vol.Required("alarm2_out2", default="Disabled")] = vol.In(
    ["Disabled", "Switchable Output"]
)


DATA_SCHEMA_KONN_MODEL_PRO = OrderedDict()
DATA_SCHEMA_KONN_MODEL_PRO[vol.Required("1", default="Disabled")] = vol.In(
    ["Disabled", "Binary Sensor", "Digital Sensor", "Switchable Output"]
)
DATA_SCHEMA_KONN_MODEL_PRO[vol.Required("2", default="Disabled")] = vol.In(
    ["Disabled", "Binary Sensor", "Digital Sensor", "Switchable Output"]
)
DATA_SCHEMA_KONN_MODEL_PRO[vol.Required("3", default="Disabled")] = vol.In(
    ["Disabled", "Binary Sensor", "Digital Sensor", "Switchable Output"]
)
DATA_SCHEMA_KONN_MODEL_PRO[vol.Required("4", default="Disabled")] = vol.In(
    ["Disabled", "Binary Sensor", "Digital Sensor", "Switchable Output"]
)
DATA_SCHEMA_KONN_MODEL_PRO[vol.Required("5", default="Disabled")] = vol.In(
    ["Disabled", "Binary Sensor", "Digital Sensor", "Switchable Output"]
)
DATA_SCHEMA_KONN_MODEL_PRO[vol.Required("6", default="Disabled")] = vol.In(
    ["Disabled", "Binary Sensor", "Digital Sensor", "Switchable Output"]
)
DATA_SCHEMA_KONN_MODEL_PRO[vol.Required("7", default="Disabled")] = vol.In(
    ["Disabled", "Binary Sensor", "Digital Sensor", "Switchable Output"]
)
DATA_SCHEMA_KONN_MODEL_PRO[vol.Required("8", default="Disabled")] = vol.In(
    ["Disabled", "Binary Sensor", "Digital Sensor", "Switchable Output"]
)
DATA_SCHEMA_KONN_MODEL_PRO[vol.Required("9", default="Disabled")] = vol.In(
    ["Disabled", "Binary Sensor", "Digital Sensor"]
)
DATA_SCHEMA_KONN_MODEL_PRO[vol.Required("11", default="Disabled")] = vol.In(
    ["Disabled", "Binary Sensor", "Digital Sensor"]
)
DATA_SCHEMA_KONN_MODEL_PRO[vol.Required("12", default="Disabled")] = vol.In(
    ["Disabled", "Binary Sensor", "Digital Sensor"]
)
DATA_SCHEMA_KONN_MODEL_PRO[vol.Required("alarm1", default="Disabled")] = vol.In(
    ["Disabled", "Switchable Output"]
)
DATA_SCHEMA_KONN_MODEL_PRO[vol.Required("out1", default="Disabled")] = vol.In(
    ["Disabled", "Switchable Output"]
)
DATA_SCHEMA_KONN_MODEL_PRO[vol.Required("alarm2_out2", default="Disabled")] = vol.In(
    ["Disabled", "Switchable Output"]
)


DATA_SCHEMA_BIN_SENSOR_OPTIONS = OrderedDict()
DATA_SCHEMA_BIN_SENSOR_OPTIONS[
    vol.Required("type", default=DEVICE_CLASS_DOOR)
] = vol.In(BIN_SENS_TYPES)
DATA_SCHEMA_BIN_SENSOR_OPTIONS[vol.Optional("name")] = str
DATA_SCHEMA_BIN_SENSOR_OPTIONS[vol.Optional("inverse", default=False)] = bool

DATA_SCHEMA_SENSOR_OPTIONS = OrderedDict()
DATA_SCHEMA_SENSOR_OPTIONS[vol.Required("type")] = vol.In(["dht", "ds18b20"])
DATA_SCHEMA_SENSOR_OPTIONS[vol.Optional("name")] = str
DATA_SCHEMA_SENSOR_OPTIONS[vol.Optional("poll_interval")] = vol.All(
    int, vol.Range(min=1)
)

DATA_SCHEMA_SWITCH_OPTIONS = OrderedDict()
DATA_SCHEMA_SWITCH_OPTIONS[vol.Optional("name")] = str
DATA_SCHEMA_SWITCH_OPTIONS[vol.Optional("activation")] = vol.In(["low", "high"])
DATA_SCHEMA_SWITCH_OPTIONS[vol.Optional("momentary")] = int
DATA_SCHEMA_SWITCH_OPTIONS[vol.Optional("pause")] = int
DATA_SCHEMA_SWITCH_OPTIONS[vol.Optional("repeat")] = int

DATA_SCHEMA_OPTIONS = {
    "Binary Sensor": DATA_SCHEMA_BIN_SENSOR_OPTIONS,
    "Sensor": DATA_SCHEMA_SENSOR_OPTIONS,
    "Switch": DATA_SCHEMA_SWITCH_OPTIONS,
}


@callback
def configured_hosts(hass):
    """Return a set of the configured hosts."""
    return set(
        entry.data["host"] for entry in hass.config_entries.async_entries(DOMAIN)
    )


class KonnectedFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for NEW_NAME."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def __init__(self):
        """Initialize the Hue flow."""
        self.host = None
        self.port = None
        self.model = None
        self.device_id = None

        self.io_cfg = {}
        self.binary_sensors = []
        self.sensors = []
        self.switches = []
        self.active_cfg = None

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            try:
                # try to obtain the mac address from the device
                import konnected

                self.host = user_input["host"]
                self.port = user_input["port"]
                status = konnected.Client(self.host, str(self.port)).get_status()
                self.device_id = status.get("mac").replace(":", "")
                self.model = status.get("name", "Konnected")
                return await self.async_step_io()

            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user", data_schema=vol.Schema(DATA_SCHEMA_MANUAL), errors=errors
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

        self.model = discovery_info[ATTR_MODEL_NAME]
        self.host = discovery_info.get("host")
        self.port = discovery_info.get("port")

        if any(
            self.host == flow["context"].get("host")
            for flow in self._async_in_progress()
        ):
            return self.async_abort(reason="already_in_progress")

        if self.host in configured_hosts(self.hass):
            return self.async_abort(reason="already_configured")

        # try to obtain the mac address from the device
        import konnected

        self.device_id = (
            konnected.Client(self.host, str(self.port))
            .get_status()
            .get("mac")
            .replace(":", "")
        )
        if not self.device_id:
            return self.async_abort(reason="cannot_connect")

        _LOGGER.info(discovery_info)
        return await self.async_step_io()

    async def async_step_io(self, user_input=None):
        """Allow the user to configure the IO."""
        errors = {}
        if user_input is not None:
            # strip out disabled io and save for options cfg
            self.io_cfg = {}
            for key, value in user_input.items():
                if value != "Disabled":
                    self.io_cfg.update({key: value})
            return await self.async_step_options_binary()

        if self.model == KONN_MODEL_PRO:
            return self.async_show_form(
                step_id="io",
                data_schema=vol.Schema(DATA_SCHEMA_KONN_MODEL_PRO),
                description_placeholders={
                    "model": "Konnected Pro Panel",
                    "host": self.host,
                },
                errors=errors,
            )

        if self.model == KONN_MODEL:
            return self.async_show_form(
                step_id="io",
                data_schema=vol.Schema(DATA_SCHEMA_KONN_MODEL),
                description_placeholders={
                    "model": "Konnected Pro Panel",
                    "host": self.host,
                },
                errors=errors,
            )

        return self.async_abort(reason="not_konn_panel")

    async def async_step_options_binary(self, user_input=None):
        """Allow the user to configure the IO options for binary sensors."""
        errors = {}
        if user_input is not None:
            zone = {"zone": self.active_cfg}
            zone.update(user_input)
            self.binary_sensors.append(zone)
            self.io_cfg.pop(self.active_cfg)
            self.active_cfg = None

        if self.active_cfg:
            return self.async_show_form(
                step_id="options_binary",
                data_schema=vol.Schema(DATA_SCHEMA_BIN_SENSOR_OPTIONS),
                description_placeholders={
                    "zone": "Zone " + self.active_cfg
                    if len(self.active_cfg) < 3
                    else self.active_cfg.upper
                },
                errors=errors,
            )

        # find the next unconfigured binary sensor
        for key, value in self.io_cfg.items():
            if value == "Binary Sensor":
                self.active_cfg = key
                return self.async_show_form(
                    step_id="options_binary",
                    data_schema=vol.Schema(DATA_SCHEMA_BIN_SENSOR_OPTIONS),
                    description_placeholders={
                        "zone": "Zone " + self.active_cfg
                        if len(self.active_cfg) < 3
                        else self.active_cfg.upper
                    },
                    errors=errors,
                )

        return await self.async_step_options_digital()

    async def async_step_options_digital(self, user_input=None):
        """Allow the user to configure the IO options for digital sensors."""
        errors = {}
        if user_input is not None:
            zone = {"zone": self.active_cfg}
            zone.update(user_input)
            self.sensors.append(zone)
            self.io_cfg.pop(self.active_cfg)
            self.active_cfg = None

        if self.active_cfg:
            return self.async_show_form(
                step_id="options_digital",
                data_schema=vol.Schema(DATA_SCHEMA_SENSOR_OPTIONS),
                description_placeholders={
                    "zone": "Zone " + self.active_cfg
                    if len(self.active_cfg) < 3
                    else self.active_cfg.upper()
                },
                errors=errors,
            )

        # find the next unconfigured binary sensor
        for key, value in self.io_cfg.items():
            if value == "Digital Sensor":
                self.active_cfg = key
                return self.async_show_form(
                    step_id="options_digital",
                    data_schema=vol.Schema(DATA_SCHEMA_SENSOR_OPTIONS),
                    description_placeholders={
                        "zone": "Zone " + self.active_cfg
                        if len(self.active_cfg) < 3
                        else self.active_cfg.upper()
                    },
                    errors=errors,
                )

        return await self.async_step_options_switch()

    async def async_step_options_switch(self, user_input=None):
        """Allow the user to configure the IO options for switches."""
        errors = {}
        if user_input is not None:
            zone = {"zone": self.active_cfg}
            zone.update(user_input)
            self.switches.append(zone)
            self.io_cfg.pop(self.active_cfg)
            self.active_cfg = None

        if self.active_cfg:
            return self.async_show_form(
                step_id="options_switch",
                data_schema=vol.Schema(DATA_SCHEMA_SWITCH_OPTIONS),
                description_placeholders={
                    "zone": "Zone " + self.active_cfg
                    if len(self.active_cfg) < 3
                    else self.active_cfg.upper()
                },
                errors=errors,
            )

        # find the next unconfigured binary sensor
        for key, value in self.io_cfg.items():
            if value == "Switchable Output":
                self.active_cfg = key
                return self.async_show_form(
                    step_id="options_switch",
                    data_schema=vol.Schema(DATA_SCHEMA_SWITCH_OPTIONS),
                    description_placeholders={
                        "zone": "Zone " + self.active_cfg
                        if len(self.active_cfg) < 3
                        else self.active_cfg.upper()
                    },
                    errors=errors,
                )

        # Build a config mimicking configuration.yaml
        return await self.async_step_import(
            {
                "host": self.host,
                "port": self.port,
                "id": self.device_id,
                "binary_sensors": self.binary_sensors,
                "sensors": self.sensors,
                "switches": self.switches,
            }
        )

    async def async_step_import(self, import_info):
        """Import a new panel as a config entry.

        This flow is triggered by `async_setup` for both configured and
        discovered panels. Triggered for any panel that does not have a
        config entry yet (based on host).

        This flow is also triggered by `async_step_ssdp`.

        If an existing config file is found, we will validate the info
        and create an entry. Otherwise we will create a new one.
        """
        host = import_info[CONF_HOST]
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
