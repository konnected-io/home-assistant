# Konnected Home Assistant Integration

## Status

Early alpha: Expected to work, but requires manual installation, configuration,
and setup. Only for knowledgeable Home Assistant users. Some key features are
still missing.

Currently supported:
- Sensors
- Pushing configuration to device (semi-manual)

Not yet supported:
- Actuators
- Automatic or user-friendly configuration push
- Documentation on configuring it as an actual alarm system

Only possible once accepted as a built-in Home Assistant component:
- Automatic device discovery (may require updating the device firmware)

## Installation

Copy the `custom_components` directory into your Home Assistant configuration
directory (if you already have a `custom_components` directory, copy in the
files, being careful to preserve the directory structure).

## Configuration

Add a `konnected` section to your `configuration.yaml` like the example below:

```yaml
konnected:
    auth_token: 'go34ruahgor'  # This should be a random string and would typically be stored in secrets.yaml
    # If ommitted, the configured Home Assistant base URL will be used.
    home_assistant_url: 'http://192.168.43.101:8123'
    devices:
        # This is the device MAC address with punctuation removed. It can be
        # retrieved from your router or from the device's /status page, under
        # "mac".
        - id: 493e0345045b
          host: '192.168.86.91'
          port: 17065
          # This is required but currently has no effect.
          actuators:
              - zone: 5
                activation: low
          sensors:
              # 'pin' can be used instead of zone if you prefer to specify the GPIO number
              - zone: 1
                # 'type' is one of the types listed at https://home-assistant.io/components/binary_sensor/
                type: motion
                # name is optional but highly recommended
                name: 'Downstairs Hallway'
              - zone: 2
                type: motion
                name: 'Kitchen & Living Room'
              - zone: 3
                type: motion
                name: 'Upstairs Hallway'
              - zone: 4
                type: motion
                name: 'Kids Room Windows'
              - zone: 5
                type: motion
                name: 'Master Bedroom Window'
```

## Setup

To configure your Konnected device to send status updates to Home Assistant
and/or to [re]configure which zones are sensors/actuators, perform the
following setup (this must be performed after installation and configuration
are complete and Home Assistant has been restarted with the new config).

In the Home Assistant frontend, open the 'Services' page. Call the
`konnected.set_device_config` service with the following service data,
replacing the device_id with your own device's ID, as used in the `id` field of
the `devices` configuration section:

```json
{"device_id": "493e0345045b"}
```

Within about a minute, your Konnected device should restart itself and start
sending sensor data to Home Assistant (it should be visible in the frontend as
a change in the icons displayed for the sensors, with a brief delay).
