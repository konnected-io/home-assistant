"""
Support for Konnected devices.

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/konnected/
"""
import asyncio
import logging
import hmac
import voluptuous as vol

from aiohttp.hdrs import AUTHORIZATION
from aiohttp.web import Request, Response  # NOQA

from homeassistant.components.binary_sensor import DEVICE_CLASSES_SCHEMA
from homeassistant.components.discovery import SERVICE_KONNECTED
from homeassistant.components.http import HomeAssistantView
from homeassistant.const import (
    HTTP_BAD_REQUEST, HTTP_INTERNAL_SERVER_ERROR, HTTP_UNAUTHORIZED,
    CONF_DEVICES, CONF_SENSORS, CONF_SWITCHES, CONF_HOST, CONF_PORT,
    CONF_ID, CONF_NAME, CONF_TYPE, CONF_PIN, CONF_ZONE, ATTR_STATE)
from homeassistant.helpers import discovery
from homeassistant.helpers import config_validation

_LOGGER = logging.getLogger(__name__)

REQUIREMENTS = ['konnected==0.1.2']

DOMAIN = 'konnected'

PIN_TO_ZONE = {1: 1, 2: 2, 5: 3, 6: 4, 7: 5, 8: 'out', 9: 6}
ZONE_TO_PIN = {zone: pin for pin, zone in PIN_TO_ZONE.items()}

_SENSOR_SCHEMA = vol.All(
    vol.Schema({
        vol.Exclusive(CONF_PIN, 's_pin'): vol.Any(*PIN_TO_ZONE),
        vol.Exclusive(CONF_ZONE, 's_pin'): vol.Any(*ZONE_TO_PIN),
        vol.Required(CONF_TYPE): DEVICE_CLASSES_SCHEMA,
        vol.Optional(CONF_NAME): config_validation.string,
    }), config_validation.has_at_least_one_key(CONF_PIN, CONF_ZONE)
)

_SWITCH_SCHEMA = vol.All(
    vol.Schema({
        vol.Exclusive(CONF_PIN, 'a_pin'): vol.Any(*PIN_TO_ZONE),
        vol.Exclusive(CONF_ZONE, 'a_pin'): vol.Any(*ZONE_TO_PIN),
        vol.Optional(CONF_NAME): config_validation.string,
        vol.Optional('activation', default='high'):
            vol.All(vol.Lower, vol.Any('high', 'low'))
    }), config_validation.has_at_least_one_key(CONF_PIN, CONF_ZONE)
)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema({
            vol.Required('auth_token'): config_validation.string,
            vol.Required(CONF_DEVICES): [{
                vol.Required(CONF_ID, default=''): config_validation.string,
                vol.Optional(CONF_SENSORS): [_SENSOR_SCHEMA],
                vol.Optional(CONF_SWITCHES): [_SWITCH_SCHEMA],
            }],
        }),
    },
    extra=vol.ALLOW_EXTRA,
)

DEPENDENCIES = ['http', 'discovery']

ENDPOINT_ROOT = '/api/konnected'
UPDATE_ENDPOINT = (
    ENDPOINT_ROOT +
    r'/device/{device_id:[a-zA-Z0-9]+}/{pin_num:[0-9]}/{state:[01]}')


async def async_setup(hass, config):
    """Set up the Konnected platform."""
    cfg = config.get(DOMAIN)
    if cfg is None:
        cfg = {}

    auth_token = cfg.get('auth_token')
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {'auth_token': auth_token}

    async def async_device_discovered(service, info):
        """Call when a Konnected device has been discovered."""
        _LOGGER.debug("Discovered a new Konnected device: %s", info)
        host = info.get(CONF_HOST)
        port = info.get(CONF_PORT)

        device = KonnectedDevice(hass, host, port, cfg)
        device.setup()

    discovery.async_listen(
        hass,
        SERVICE_KONNECTED,
        async_device_discovered)

    hass.http.register_view(KonnectedView(auth_token))

    return True


class KonnectedDevice(object):
    """A representation of a single Konnected device."""

    def __init__(self, hass, host, port, config):
        """Initialize the Konnected device."""
        self.hass = hass
        self.host = host
        self.port = port
        self.user_config = config

        import konnected
        self.client = konnected.Client(host, str(port))
        self.status = self.client.get_status()
        _LOGGER.info('Initialized Konnected device %s', self.device_id)

    def setup(self):
        """Set up a newly discovered Konnected device."""
        user_config = self.config()
        if user_config:
            _LOGGER.debug('Configuring Konnected device %s', self.device_id)
            self.save_data()
            self.hass.async_add_job(self.sync_device)
            self.hass.async_add_job(
                discovery.async_load_platform(
                    self.hass, 'binary_sensor',
                    DOMAIN, {'device_id': self.device_id}))
            self.hass.async_add_job(
                discovery.async_load_platform(
                    self.hass, 'switch', DOMAIN,
                    {'device_id': self.device_id}))

    @property
    def device_id(self):
        """Device id is the MAC address as string with punctuation removed."""
        return self.status['mac'].replace(':', '')

    def config(self):
        """Return an object representing the user defined configuration."""
        device_id = self.device_id
        valid_keys = [device_id, device_id.upper(),
                      device_id[6:], device_id.upper()[6:]]
        configured_devices = self.user_config[CONF_DEVICES]
        return next((device for device in
                     configured_devices if device[CONF_ID] in valid_keys),
                    None)

    def save_data(self):
        """Save the device configuration to `hass.data`.

        TODO: This can probably be refactored and tidied up.
        """
        sensors = {}
        for entity in self.config().get(CONF_SENSORS) or []:
            if CONF_ZONE in entity:
                pin = ZONE_TO_PIN[entity[CONF_ZONE]]
            else:
                pin = entity[CONF_PIN]

            sensor_status = next((sensor for sensor in
                                  self.status.get('sensors') if
                                  sensor.get(CONF_PIN) == pin), {})
            if sensor_status.get(ATTR_STATE):
                initial_state = bool(int(sensor_status.get(ATTR_STATE)))
            else:
                initial_state = None

            sensors[pin] = {
                CONF_TYPE: entity[CONF_TYPE],
                CONF_NAME: entity.get(CONF_NAME, 'Konnected {} Zone {}'.format(
                    self.device_id[6:], PIN_TO_ZONE[pin])),
                ATTR_STATE: initial_state
            }
            _LOGGER.debug('Set up sensor %s (initial state: %s)',
                          sensors[pin].get('name'),
                          sensors[pin].get(ATTR_STATE))

        actuators = {}
        for entity in self.config().get(CONF_SWITCHES) or []:
            if 'zone' in entity:
                pin = ZONE_TO_PIN[entity['zone']]
            else:
                pin = entity['pin']

            actuator_status = next((actuator for actuator in
                                    self.status.get('actuators') if
                                    actuator.get('pin') == pin), {})
            if actuator_status.get(ATTR_STATE):
                initial_state = bool(int(actuator_status.get(ATTR_STATE)))
            else:
                initial_state = None

            actuators[pin] = {
                CONF_NAME: entity.get(
                    CONF_NAME, 'Konnected {} Actuator {}'.format(
                        self.device_id[6:], PIN_TO_ZONE[pin])),
                ATTR_STATE: initial_state,
                'activation': entity['activation'],
            }
            _LOGGER.debug('Set up actuator %s (initial state: %s)',
                          actuators[pin].get(CONF_NAME),
                          actuators[pin].get(ATTR_STATE))

        device_data = {
            'client': self.client,
            CONF_SENSORS: sensors,
            CONF_SWITCHES: actuators,
            CONF_HOST: self.host,
            CONF_PORT: self.port,
        }

        if CONF_DEVICES not in self.hass.data[DOMAIN]:
            self.hass.data[DOMAIN][CONF_DEVICES] = {}

        _LOGGER.debug('Storing data in hass.data[konnected]: %s', device_data)
        self.hass.data[DOMAIN][CONF_DEVICES][self.device_id] = device_data

    @property
    def stored_configuration(self):
        """Return the configuration stored in `hass.data` for this device."""
        return self.hass.data[DOMAIN][CONF_DEVICES][self.device_id]

    def sensor_configuration(self):
        """Return the configuration map for syncing sensors."""
        return [{'pin': p} for p in
                self.stored_configuration[CONF_SENSORS].keys()]

    def actuator_configuration(self):
        """Return the configuration map for syncing actuators."""
        return [{'pin': p,
                 'trigger': (0 if data.get('activation') in [0, 'low'] else 1)}
                for p, data in
                self.stored_configuration[CONF_SWITCHES].items()]

    def sync_device(self):
        """Sync the new pin configuration to the Konnected device."""
        desired_sensor_configuration = self.sensor_configuration()
        current_sensor_configuration = [
            {'pin': s[CONF_PIN]} for s in self.status.get('sensors')]
        _LOGGER.debug('%s: desired sensor config: %s', self.device_id,
                      desired_sensor_configuration)
        _LOGGER.debug('%s: current sensor config: %s', self.device_id,
                      current_sensor_configuration)

        desired_actuator_config = self.actuator_configuration()
        current_actuator_config = self.status.get('actuators')
        _LOGGER.debug('%s: desired actuator config: %s', self.device_id,
                      desired_actuator_config)
        _LOGGER.debug('%s: current actuator config: %s', self.device_id,
                      current_actuator_config)

        if (desired_sensor_configuration != current_sensor_configuration) or \
                (current_actuator_config != desired_actuator_config):
            _LOGGER.debug('pushing settings to device %s', self.device_id)
            self.client.put_settings(
                desired_sensor_configuration,
                desired_actuator_config,
                self.hass.data[DOMAIN].get('auth_token'),
                self.hass.config.api.base_url + ENDPOINT_ROOT
            )


class KonnectedView(HomeAssistantView):
    """View creates an endpoint to receive push updates from the device."""

    url = UPDATE_ENDPOINT
    name = 'api:konnected'
    requires_auth = False  # Uses access token from configuration

    def __init__(self, auth_token):
        """Initialize the view."""
        self.auth_token = auth_token

    @asyncio.coroutine
    def put(self, request: Request, device_id, pin_num, state) -> Response:
        """Receive a sensor update via PUT request and async set state."""
        hass = request.app['hass']
        data = hass.data[DOMAIN]

        auth = request.headers.get(AUTHORIZATION, None)
        if not hmac.compare_digest('Bearer {}'.format(self.auth_token), auth):
            return self.json_message(
                "unauthorized", status_code=HTTP_UNAUTHORIZED)
        pin_num = int(pin_num)
        state = bool(int(state))
        device = data[CONF_DEVICES].get(device_id)
        if device is None:
            return self.json_message('unregistered device',
                                     status_code=HTTP_BAD_REQUEST)
        pin_data = device[CONF_SENSORS].get(pin_num) or \
            device[CONF_SWITCHES].get(pin_num)

        if pin_data is None:
            return self.json_message('unregistered sensor/actuator',
                                     status_code=HTTP_BAD_REQUEST)
        entity = pin_data.get('entity')
        if entity is None:
            return self.json_message('uninitialized sensor/actuator',
                                     status_code=HTTP_INTERNAL_SERVER_ERROR)

        yield from entity.async_set_state(state)
        return self.json_message('ok')
