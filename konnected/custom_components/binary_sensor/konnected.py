import asyncio
import logging

from homeassistant.components.binary_sensor import BinarySensorDevice
from custom_components.konnected import (DOMAIN, PIN_TO_ZONE)
from homeassistant.helpers.entity import Entity

_LOGGER = logging.getLogger(__name__)

DEPENDENCIES = ['konnected']

@asyncio.coroutine
def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    if discovery_info is None:
        return

    data = hass.data[DOMAIN]
    device_id = discovery_info['device_id']
    sensors = [KonnectedBinarySensor(device_id, pin_num, pin_data)
               for pin_num, pin_data in data['devices'][device_id]['sensors'].items()]
    async_add_devices(sensors, True)
    

class KonnectedBinarySensor(BinarySensorDevice):
    def __init__(self, device_id, pin_num, data):
        # This device's config and state only (shared with the global data object)
        self._data = data
        self._device_id = device_id
        self._pin_num = pin_num
        self._state = self._data.get('state')
        self._device_class = self._data.get('type', 'motion')
        self._name = self._data.get('name', 'Konnected {} Zone {}'.format(device_id, PIN_TO_ZONE[pin_num]))
        self._data['entity'] = self
        _LOGGER.info('Created new sensor: %s', self._name)

    @property
    def name(self):
        return self._name

    @property
    def is_on(self):
        """Return the status of the sensor."""
        return self._state

    @property
    def should_poll(self):
        return False

    @property
    def device_class(self):
        return self._device_class

    @asyncio.coroutine
    def async_set_state(self, state):
        self._state = state
        self._data['state'] = state
        self.async_schedule_update_ha_state()
        _LOGGER.info('Setting status of %s pin %s to %s', self._device_id, self.name, state)
