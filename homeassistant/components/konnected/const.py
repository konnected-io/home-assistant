"""Konnected constants."""

DOMAIN = "konnected"

CONF_ACTIVATION = "activation"
CONF_API_HOST = "api_host"
CONF_MOMENTARY = "momentary"
CONF_PAUSE = "pause"
CONF_POLL_INTERVAL = "poll_interval"
CONF_PRECISION = "precision"
CONF_REPEAT = "repeat"
CONF_INVERSE = "inverse"
CONF_BLINK = "blink"
CONF_DISCOVERY = "discovery"
CONF_DHT_SENSORS = "dht_sensors"
CONF_DS18B20_SENSORS = "ds18b20_sensors"

STATE_LOW = "low"
STATE_HIGH = "high"

ZONES = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, "alarm1", "out1", "alarm2_out2"]

ENDPOINT_ROOT = "/api/konnected"
UPDATE_ENDPOINT = ENDPOINT_ROOT + r"/device/{device_id:[a-zA-Z0-9]+}"
SIGNAL_SENSOR_UPDATE = "konnected.{}.update"
SIGNAL_DS18B20_NEW = "konnected.ds18b20.new"
