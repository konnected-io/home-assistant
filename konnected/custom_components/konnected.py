import aiohttp
import asyncio
import logging
import voluptuous as vol

from aiohttp.hdrs import AUTHORIZATION
from aiohttp.web import Request, Response  # NOQA

from homeassistant.components.binary_sensor import DEVICE_CLASSES_SCHEMA
from homeassistant.components.http import HomeAssistantView
from homeassistant.const import (
        HTTP_BAD_REQUEST, HTTP_INTERNAL_SERVER_ERROR, HTTP_UNAUTHORIZED)
from homeassistant.helpers import discovery

_LOGGER = logging.getLogger(__name__)

DOMAIN = 'konnected'

PIN_TO_ZONE = {1: 1, 2: 2, 5: 3, 6: 4, 7: 5, 9: 6}
ZONE_TO_PIN = {zone: pin for pin, zone in PIN_TO_ZONE.items()}

# TODO: Move string literals into constants
CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: {
            'auth_token': str,
            vol.Optional('home_assistant_url'): str,
            'devices': [{
                vol.Required('id', default=''): vol.Coerce(str),
                'sensors': [{
                    vol.Exclusive('pin', 's_pin'): vol.Any(*PIN_TO_ZONE),
                    vol.Exclusive('zone', 's_pin'): vol.Any(*ZONE_TO_PIN),
                    vol.Required('type', default='motion'): DEVICE_CLASSES_SCHEMA,
                    vol.Optional('name'): str,
                    vol.Inclusive('host', 'manual_host'): str,
                    vol.Inclusive('port', 'manual_host'): int,
                }],
                'actuators': [{
                    vol.Exclusive('pin', 'a_pin'): vol.Any(*PIN_TO_ZONE),
                    vol.Exclusive('zone', 'a_pin'): vol.Any(*ZONE_TO_PIN),
                    # vol.Required('type', default='motion'): DEVICE_CLASSES_SCHEMA,
                    vol.Optional('name'): str,
                    vol.Required('activation', default='high'): vol.All(vol.Lower, vol.Any('high', 'low'))
                }],
            }],
        },
    },
    extra=vol.ALLOW_EXTRA,
)

DEPENDENCIES = ['http']

ENDPOINT_ROOT = '/api/konnected'
UPDATE_ENDPOINT = (
        ENDPOINT_ROOT
        + r'/device/{device_id:[a-zA-Z0-9]+}/{pin_num:[0-9]}/{state:[01]}')

@asyncio.coroutine
def async_setup(hass, config):
    # TODO: Add schema
    cfg = config.get(DOMAIN)
    devices = {}
    for d in cfg['devices']:
        sensors = {}
        for s in d['sensors']:
            if 'zone' in s:
                pin = ZONE_TO_PIN[s['zone']]
            else:
                pin = s['pin']
            sensors[pin] = {
                'type': s['type'],
                'name': s.get('name', 'Konnected {} Zone {}'.format(d['id'], PIN_TO_ZONE[pin])),
                'state': None,
            }
        devices[d['id']] = {
            'host': d.get('host'),
            'port': d.get('port'),
            'sensors': sensors,
            # TODO: actuators
        }
    data = {
        'devices': devices,
        'auth_token': cfg['auth_token'],
    }
    if 'home_assistant_url' in cfg:
        data['home_assistant_url'] = cfg['home_assistant_url']
    hass.data[DOMAIN] = data
    hass.http.register_view(KonnectedView(cfg, data))
    for d_id in data['devices']:
        discovery_info = {
            'device_id': d_id,
        }
        hass.async_add_job(
            discovery.async_load_platform(
                hass, 'binary_sensor', DOMAIN, discovery_info, config))
            

    @asyncio.coroutine
    def async_device_discovered(service, info):
        """ Called when a Konnected device has been discovered. """
        session = aiohttp.ClientSession()
        base_url = 'http://{}:{}'.format(info['host'], info['port'])
        status = yield from session.get(base_url + '/status')
        status = yield from status.json(content_type=None)
        yield from session.close()
        device_id = status['mac'].replace(':', '')
        if device_id in data['devices']:
            device = data['devices'][device_id]
            if device['host'] is None:
                device['host'] = info['host']
                device['port'] = info['port']
                _LOGGER.info('Set Konnecte %s to %s:%s', device_id, device['host'], device['port'])
            else:
                _LOGGER.info('Set Konnecte %s already registered', device_id)
            return
        else:
            # TODO: Do something useful instead of failing
            _LOGGER.error('Discovered Konnected device %s is not configured', device_id)
            return
        # FIXME: This is all unreachable and probably bit-rotted:
        device_data = {
            'base_url': base_url,
            'device_id': device_id,
            'sensors': {s['pin']: bool(s['state']) for s in status['sensors']},
            'actuators': {s['pin']: bool(s['state']) for s in status['actuators']},
            'entities': {},  # Each entity created inserts itself here
        }
        data['devices'][device_id] = device_data
        discovery_info = {
            'device_id': device_id,
            'sensors': device_data['sensors'],
            'actuators': device_data['actuators'],
        }
        hass.async_add_job(
            discovery.async_load_platform(
                hass, 'binary_sensor', DOMAIN, discovery_info, config))
        _LOGGER.info("Discovered a new Konnected device: %s", device_id)

    @asyncio.coroutine
    def async_set_device_config(call):
        device_id = call.data.get('device_id')
        if device_id not in data['devices']:
            _LOGGER.error('Unable to set config for unregistered device %s',
                          device_id)
            return False
        device_data = data['devices'][device_id]

        session = aiohttp.ClientSession()
        if not (device_data['host'] and device_data['port']):
            _LOGGER.error('Unable to set config for device %s without configured or discovered host/port', device_id)
        device_base_url = 'http://{}:{}'.format(device_data['host'], device_data['port'])
        hass_base_url = data.get('home_assistant_url', hass.config.api.base_url).rstrip('/')
        request_data = {
            'sensors': [{'pin': pin_num} for pin_num in device_data['sensors']],
            'actuators': [], # TODO
            'token': data['auth_token'],
            'apiUrl': hass_base_url + ENDPOINT_ROOT
        }
        url = device_base_url + '/settings'
        _LOGGER.info('Sending settings via PUT to %s: %s', url, request_data)
        response = yield from session.put(url, json=request_data)
        content = yield from response.text()
        _LOGGER.info('Got response %s: %s', response.status, content)
        yield from session.close()
        # TODO: log and return success/failure

    # TODO: Add schema
    hass.services.async_register(DOMAIN, 'set_device_config', async_set_device_config)

    return True

class KonnectedView(HomeAssistantView):
    url = UPDATE_ENDPOINT
    name = 'api:konnected'
    requires_auth = False  # Uses access token from configuration

    def __init__(self, cfg, data):
        self.auth_token = cfg.get('auth_token')
        self.data = data

    @asyncio.coroutine
    def put(self, request: Request, device_id, pin_num, state) -> Response:
        auth = request.headers.get(AUTHORIZATION, None)
        if 'Bearer {}'.format(self.auth_token) != auth:
            return self.json_message(
                "unauthorized", status_code=HTTP_UNAUTHORIZED)
        pin_num = int(pin_num)
        state = bool(int(state))
        device = self.data['devices'].get(device_id)
        if device is None:
            return self.json_message('unregistered device',
                                     status_code=HTTP_BAD_REQUEST)
        pin_data = device['sensors'].get(pin_num)
        if pin_data is None:
            return self.json_message('unregistered sensor',
                                     status_code=HTTP_BAD_REQUEST)
        entity = pin_data.get('entity')
        if entity is None:
            return self.json_message('uninitialized sensor',
                                     status_code=HTTP_INTERNAL_SERVER_ERROR)

        yield from entity.async_set_state(state)
        return self.json_message('ok')
