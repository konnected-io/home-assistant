"""Support for Konnected devices."""
import asyncio
import hmac
import json
import logging
import random
import string

from aiohttp.hdrs import AUTHORIZATION
from aiohttp.web import Request, Response
import voluptuous as vol

from homeassistant.components.binary_sensor import DEVICE_CLASSES_SCHEMA
from homeassistant.components.http import HomeAssistantView
from homeassistant import config_entries
from homeassistant.const import (
    ATTR_ENTITY_ID,
    CONF_ACCESS_TOKEN,
    CONF_BINARY_SENSORS,
    CONF_DEVICES,
    CONF_HOST,
    CONF_ID,
    CONF_NAME,
    CONF_PORT,
    CONF_SENSORS,
    CONF_SWITCHES,
    CONF_TYPE,
    CONF_ZONE,
    HTTP_BAD_REQUEST,
    HTTP_NOT_FOUND,
    HTTP_UNAUTHORIZED,
    STATE_ON,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv

from .config_flow import (
    configured_hosts,
)  # Loading the config flow file will register the flow
from .const import (
    CONF_ACTIVATION,
    CONF_API_HOST,
    CONF_BLINK,
    CONF_DISCOVERY,
    CONF_INVERSE,
    CONF_MOMENTARY,
    CONF_PAUSE,
    CONF_POLL_INTERVAL,
    CONF_REPEAT,
    DOMAIN,
    # PIN_TO_ZONE,
    STATE_HIGH,
    STATE_LOW,
    UPDATE_ENDPOINT,
    # ZONE_TO_PIN,
    ZONES,
)
from .handlers import HANDLERS
from .panel import AlarmPanel

_LOGGER = logging.getLogger(__name__)

_BINARY_SENSOR_SCHEMA = vol.All(
    vol.Schema(
        {
            vol.Exclusive(CONF_ZONE, "s_zone"): vol.In(ZONES),
            vol.Required(CONF_ZONE): vol.In(ZONES),
            vol.Required(CONF_TYPE): DEVICE_CLASSES_SCHEMA,
            vol.Optional(CONF_NAME): cv.string,
            vol.Optional(CONF_INVERSE, default=False): cv.boolean,
        }
    )
)

_SENSOR_SCHEMA = vol.All(
    vol.Schema(
        {
            vol.Exclusive(CONF_ZONE, "s_zone"): vol.In(ZONES),
            vol.Required(CONF_ZONE): vol.In(ZONES),
            vol.Required(CONF_TYPE): vol.All(vol.Lower, vol.In(["dht", "ds18b20"])),
            vol.Optional(CONF_NAME): cv.string,
            vol.Optional(CONF_POLL_INTERVAL): vol.All(
                vol.Coerce(int), vol.Range(min=1)
            ),
        }
    )
)

_SWITCH_SCHEMA = vol.All(
    vol.Schema(
        {
            vol.Exclusive(CONF_ZONE, "s_zone"): vol.In(ZONES),
            vol.Required(CONF_ZONE): vol.In(ZONES),
            vol.Optional(CONF_NAME): cv.string,
            vol.Optional(CONF_ACTIVATION, default=STATE_HIGH): vol.All(
                vol.Lower, vol.Any(STATE_HIGH, STATE_LOW)
            ),
            vol.Optional(CONF_MOMENTARY): vol.All(vol.Coerce(int), vol.Range(min=10)),
            vol.Optional(CONF_PAUSE): vol.All(vol.Coerce(int), vol.Range(min=10)),
            vol.Optional(CONF_REPEAT): vol.All(vol.Coerce(int), vol.Range(min=-1)),
        }
    )
)

# pylint: disable=no-value-for-parameter
CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_ACCESS_TOKEN): cv.string,
                vol.Optional(CONF_API_HOST): vol.Url(),
                vol.Optional(CONF_DEVICES): [
                    {
                        vol.Required(CONF_ID): cv.matches_regex("[0-9a-f]{12}"),
                        vol.Optional(CONF_BINARY_SENSORS): vol.All(
                            cv.ensure_list, [_BINARY_SENSOR_SCHEMA]
                        ),
                        vol.Optional(CONF_SENSORS): vol.All(
                            cv.ensure_list, [_SENSOR_SCHEMA]
                        ),
                        vol.Optional(CONF_SWITCHES): vol.All(
                            cv.ensure_list, [_SWITCH_SCHEMA]
                        ),
                        vol.Optional(CONF_HOST): cv.string,
                        vol.Optional(CONF_PORT): cv.port,
                        vol.Optional(CONF_BLINK, default=True): cv.boolean,
                        vol.Optional(CONF_DISCOVERY, default=True): cv.boolean,
                    }
                ],
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

YAML_CONFIGS = "yaml_configs"
PLATFORMS = ["binary_sensor", "sensor", "switch"]


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Konnected platform."""
    cfg = config.get(DOMAIN)
    if cfg is None:
        cfg = {}

    access_token = cfg.get(CONF_ACCESS_TOKEN) or "".join(
        random.choices(string.ascii_uppercase + string.digits, k=20)
    )
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {
            CONF_ACCESS_TOKEN: access_token,
            CONF_API_HOST: cfg.get(CONF_API_HOST),
        }

    hass.http.register_view(KonnectedView(access_token))

    # Check if they have yaml configured devices
    if CONF_DEVICES not in cfg:
        return True

    configured = configured_hosts(hass)
    devices = cfg[CONF_DEVICES]

    if devices:
        # Store config in hass.data so the config entry can find it
        hass.data[DOMAIN][YAML_CONFIGS] = devices

        for device in devices:
            # If configured, the panel will be set up during config entry phase
            if device.get("host") in configured:
                continue

            # No existing config entry found, try importing it. Use
            # hass.async_add_job to avoid a deadlock.
            hass.async_create_task(
                hass.config_entries.flow.async_init(
                    DOMAIN,
                    context={"source": config_entries.SOURCE_IMPORT},
                    data=device,
                )
            )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up panel from a config entry."""
    AlarmPanel(hass, entry).save_data()
    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )
    if unload_ok:
        hass.data[DOMAIN][CONF_DEVICES].pop(entry.data[CONF_ID])

    return unload_ok


class KonnectedView(HomeAssistantView):
    """View creates an endpoint to receive push updates from the device."""

    url = UPDATE_ENDPOINT
    name = "api:konnected"
    requires_auth = False  # Uses access token from configuration

    def __init__(self, auth_token):
        """Initialize the view."""
        self.auth_token = auth_token

    @staticmethod
    def binary_value(state, activation):
        """Return binary value for GPIO based on state and activation."""
        if activation == STATE_HIGH:
            return 1 if state == STATE_ON else 0
        return 0 if state == STATE_ON else 1

    async def get(self, request: Request, device_id) -> Response:
        """Return the current binary state of a switch."""
        hass = request.app["hass"]
        zone_num = request.query.get("zone")
        data = hass.data[DOMAIN]

        device = data[CONF_DEVICES][device_id]
        if not device:
            return self.json_message(
                "Device " + device_id + " not configured", status_code=HTTP_NOT_FOUND
            )

        try:
            zone = next(
                filter(
                    lambda switch: switch[CONF_ZONE] == zone_num, device[CONF_SWITCHES]
                )
            )
        except StopIteration:
            zone = None

        if not zone:
            return self.json_message(
                format("Switch on zone {} not configured", zone_num),
                status_code=HTTP_NOT_FOUND,
            )

        return self.json(
            {
                "zone": zone_num,
                "state": self.binary_value(
                    hass.states.get(zone[ATTR_ENTITY_ID]).state, zone[CONF_ACTIVATION]
                ),
            }
        )

    async def put(self, request: Request, device_id) -> Response:
        """Receive a sensor update via PUT request and async set state."""
        hass = request.app["hass"]
        data = hass.data[DOMAIN]

        try:  # Konnected 2.2.0 and above supports JSON payloads
            payload = await request.json()
            zone_num = payload["zone"]
        except json.decoder.JSONDecodeError:
            _LOGGER.error(
                (
                    "Your Konnected device software may be out of "
                    "date. Visit https://help.konnected.io for "
                    "updating instructions."
                )
            )

        auth = request.headers.get(AUTHORIZATION, None)
        if not hmac.compare_digest(f"Bearer {self.auth_token}", auth):
            return self.json_message("unauthorized", status_code=HTTP_UNAUTHORIZED)
        zone_num = int(zone_num)
        device = data[CONF_DEVICES].get(device_id)
        if device is None:
            return self.json_message(
                "unregistered device", status_code=HTTP_BAD_REQUEST
            )
        zone_data = device[CONF_BINARY_SENSORS].get(zone_num) or next(
            (s for s in device[CONF_SENSORS] if s[CONF_ZONE] == zone_num), None
        )

        if zone_data is None:
            return self.json_message(
                "unregistered sensor/actuator", status_code=HTTP_BAD_REQUEST
            )

        zone_data["device_id"] = device_id

        for attr in ["state", "temp", "humi", "addr"]:
            value = payload.get(attr)
            handler = HANDLERS.get(attr)
            if value is not None and handler:
                hass.async_create_task(handler(hass, zone_data, payload))

        return self.json_message("ok")

    async def post(self, request: Request, device_id) -> Response:
        """Receive a sensor update via POST request and async set state."""
        hass = request.app["hass"]
        data = hass.data[DOMAIN]

        try:  # Konnected 2.2.0 and above supports JSON payloads
            payload = await request.json()
            zone_num = payload["zone"]
        except json.decoder.JSONDecodeError:
            _LOGGER.error(
                (
                    "Your Konnected device software may be out of "
                    "date. Visit https://help.konnected.io for "
                    "updating instructions."
                )
            )

        auth = request.headers.get(AUTHORIZATION, None)
        if not hmac.compare_digest(f"Bearer {self.auth_token}", auth):
            return self.json_message("unauthorized", status_code=HTTP_UNAUTHORIZED)
        zone_num = int(zone_num)
        device = data[CONF_DEVICES].get(device_id)
        if device is None:
            return self.json_message(
                "unregistered device", status_code=HTTP_BAD_REQUEST
            )
        zone_data = device[CONF_BINARY_SENSORS].get(zone_num) or next(
            (s for s in device[CONF_SENSORS] if s[CONF_ZONE] == zone_num), None
        )

        if zone_data is None:
            return self.json_message(
                "unregistered sensor/actuator", status_code=HTTP_BAD_REQUEST
            )

        zone_data["device_id"] = device_id

        for attr in ["state", "temp", "humi", "addr"]:
            value = payload.get(attr)
            handler = HANDLERS.get(attr)
            if value is not None and handler:
                hass.async_create_task(handler(hass, zone_data, payload))

        return self.json_message("ok")
