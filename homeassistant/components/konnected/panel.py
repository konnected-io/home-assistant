"""Support for Konnected devices."""
import logging

from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_STATE,
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
)
from homeassistant.helpers.dispatcher import dispatcher_send

from .const import (
    CONF_ACTIVATION,
    CONF_API_HOST,
    CONF_BLINK,
    CONF_DHT_SENSORS,
    CONF_DISCOVERY,
    CONF_DS18B20_SENSORS,
    CONF_INVERSE,
    CONF_MOMENTARY,
    CONF_PAUSE,
    CONF_POLL_INTERVAL,
    CONF_REPEAT,
    DOMAIN,
    ENDPOINT_ROOT,
    # PIN_TO_ZONE,
    SIGNAL_SENSOR_UPDATE,
    STATE_LOW,
    # ZONE_TO_PIN,
)

_LOGGER = logging.getLogger(__name__)


class AlarmPanel:
    """A representation of a Konnected alarm panel."""

    def __init__(self, hass, config_entry):
        """Initialize the Konnected device."""
        self.hass = hass
        self.config_entry = config_entry
        self.config = (
            config_entry.data
        )  # the configuration.yaml data contained in a device entry
        self.host = self.config.get(CONF_HOST)
        self.port = self.config.get(CONF_PORT)

        import konnected

        self.client = konnected.Client(self.host, str(self.port))
        self.status = self.client.get_status()

    @property
    def device_id(self):
        """Device id is the MAC address as string with punctuation removed."""
        return self.config.get(CONF_ID)

    @property
    def stored_configuration(self):
        """Return the configuration stored in `hass.data` for this device."""
        return self.hass.data[DOMAIN][CONF_DEVICES].get(self.device_id)

    def setup(self):
        """Set up a newly discovered Konnected device."""
        _LOGGER.info(
            "Discovered Konnected device %s. Open http://%s:%s in a "
            "web browser to view device status.",
            self.device_id,
            self.host,
            self.port,
        )
        self.save_data()
        self.update_initial_states()
        self.sync_device_config()

    def save_data(self):
        """Save the device configuration to `hass.data`."""
        binary_sensors = {}
        for entity in self.config.get(CONF_BINARY_SENSORS) or []:
            zone = entity[CONF_ZONE]

            binary_sensors[zone] = {
                CONF_TYPE: entity[CONF_TYPE],
                CONF_NAME: entity.get(
                    CONF_NAME, "Konnected {} Zone {}".format(self.device_id[6:], zone)
                ),
                CONF_INVERSE: entity.get(CONF_INVERSE),
                ATTR_STATE: None,
            }
            _LOGGER.debug(
                "Set up binary_sensor %s (initial state: %s)",
                binary_sensors[zone].get("name"),
                binary_sensors[zone].get(ATTR_STATE),
            )

        actuators = []
        for entity in self.config.get(CONF_SWITCHES) or []:
            zone = entity[CONF_ZONE]

            act = {
                CONF_ZONE: zone,
                CONF_NAME: entity.get(
                    CONF_NAME,
                    "Konnected {} Actuator {}".format(self.device_id[6:], zone),
                ),
                ATTR_STATE: None,
                CONF_ACTIVATION: entity[CONF_ACTIVATION],
                CONF_MOMENTARY: entity.get(CONF_MOMENTARY),
                CONF_PAUSE: entity.get(CONF_PAUSE),
                CONF_REPEAT: entity.get(CONF_REPEAT),
            }
            actuators.append(act)
            _LOGGER.debug("Set up switch %s", act)

        sensors = []
        for entity in self.config.get(CONF_SENSORS) or []:
            zone = entity[CONF_ZONE]

            sensor = {
                CONF_ZONE: zone,
                CONF_NAME: entity.get(
                    CONF_NAME, "Konnected {} Sensor {}".format(self.device_id[6:], zone)
                ),
                CONF_TYPE: entity[CONF_TYPE],
                CONF_POLL_INTERVAL: entity.get(CONF_POLL_INTERVAL),
            }
            sensors.append(sensor)
            _LOGGER.debug(
                "Set up %s sensor %s (initial state: %s)",
                sensor.get(CONF_TYPE),
                sensor.get(CONF_NAME),
                sensor.get(ATTR_STATE),
            )

        device_data = {
            CONF_BINARY_SENSORS: binary_sensors,
            CONF_SENSORS: sensors,
            CONF_SWITCHES: actuators,
            CONF_BLINK: self.config.get(CONF_BLINK),
            CONF_DISCOVERY: self.config.get(CONF_DISCOVERY),
        }

        if CONF_DEVICES not in self.hass.data[DOMAIN]:
            self.hass.data[DOMAIN][CONF_DEVICES] = {}

        _LOGGER.debug(
            "Storing data in hass.data[%s][%s][%s]: %s",
            DOMAIN,
            CONF_DEVICES,
            self.device_id,
            device_data,
        )
        self.hass.data[DOMAIN][CONF_DEVICES][self.device_id] = device_data

    def binary_sensor_configuration(self):
        """Return the configuration map for syncing binary sensors."""
        return [{"zone": p} for p in self.stored_configuration[CONF_BINARY_SENSORS]]

    def actuator_configuration(self):
        """Return the configuration map for syncing actuators."""
        return [
            {
                "zone": data.get(CONF_ZONE),
                "trigger": (0 if data.get(CONF_ACTIVATION) in [0, STATE_LOW] else 1),
            }
            for data in self.stored_configuration[CONF_SWITCHES]
        ]

    def dht_sensor_configuration(self):
        """Return the configuration map for syncing DHT sensors."""
        return [
            {
                CONF_ZONE: sensor[CONF_ZONE],
                CONF_POLL_INTERVAL: sensor[CONF_POLL_INTERVAL],
            }
            for sensor in self.stored_configuration[CONF_SENSORS]
            if sensor[CONF_TYPE] == "dht"
        ]

    def ds18b20_sensor_configuration(self):
        """Return the configuration map for syncing DS18B20 sensors."""
        return [
            {"zone": sensor[CONF_ZONE]}
            for sensor in self.stored_configuration[CONF_SENSORS]
            if sensor[CONF_TYPE] == "ds18b20"
        ]

    def update_initial_states(self):
        """Update the initial state of each sensor from status poll."""
        for sensor_data in self.status.get("sensors"):
            sensor_config = self.stored_configuration[CONF_BINARY_SENSORS].get(
                sensor_data.get(CONF_ZONE), {}
            )
            entity_id = sensor_config.get(ATTR_ENTITY_ID)

            state = bool(sensor_data.get(ATTR_STATE))
            if sensor_config.get(CONF_INVERSE):
                state = not state

            dispatcher_send(self.hass, SIGNAL_SENSOR_UPDATE.format(entity_id), state)

    def desired_settings_payload(self):
        """Return a dict representing the desired device configuration."""
        desired_api_host = (
            self.config.get(CONF_API_HOST) or self.hass.config.api.base_url
        )
        desired_api_endpoint = desired_api_host + ENDPOINT_ROOT

        return {
            "sensors": self.binary_sensor_configuration(),
            "actuators": self.actuator_configuration(),
            "dht_sensors": self.dht_sensor_configuration(),
            "ds18b20_sensors": self.ds18b20_sensor_configuration(),
            "auth_token": self.config.get(CONF_ACCESS_TOKEN),
            "endpoint": desired_api_endpoint,
            "blink": self.config.get(CONF_BLINK),
            "discovery": self.config.get(CONF_DISCOVERY),
        }

    def current_settings_payload(self):
        """Return a dict of configuration currently stored on the device."""
        settings = self.status["settings"]
        if not settings:
            settings = {}

        return {
            "sensors": [{"zone": s[CONF_ZONE]} for s in self.status.get("sensors")],
            "actuators": self.status.get("actuators"),
            "dht_sensors": self.status.get(CONF_DHT_SENSORS),
            "ds18b20_sensors": self.status.get(CONF_DS18B20_SENSORS),
            "auth_token": settings.get("token"),
            "endpoint": settings.get("apiUrl"),
            "blink": settings.get(CONF_BLINK),
            "discovery": settings.get(CONF_DISCOVERY),
        }

    def sync_device_config(self):
        """Sync the new zone configuration to the Konnected device if needed."""
        _LOGGER.debug(
            "Device %s settings payload: %s",
            self.device_id,
            self.desired_settings_payload(),
        )
        if self.desired_settings_payload() != self.current_settings_payload():
            _LOGGER.info("pushing settings to device %s", self.device_id)
            self.client.put_settings(**self.desired_settings_payload())
