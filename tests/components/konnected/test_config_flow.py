"""Tests for Konnected Alarm Panel config flow."""
from unittest.mock import patch
from homeassistant.components.konnected import config_flow


async def test_flow_works(hass, aioclient_mock):
    """Test config flow ."""
    flow = config_flow.KonnectedFlowHandler()
    flow.hass = hass

    result = await flow.async_step_user()
    assert result["type"] == "form"
    assert result["step_id"] == "user"

    with patch("konnected.Client") as mock_panel:

        def mock_constructor(host, port):
            """Fake the panel constructor."""
            mock_panel.host = host
            mock_panel.port = port
            return mock_panel

        mock_panel.side_effect = mock_constructor
        mock_panel.get_status.return_value = {
            "mac": "11:22:33:44:55:66",
            "name": "Konnected Pro",
        }

        result = await flow.async_step_user({"port": 1234, "host": "1.2.3.4"})

    assert mock_panel.host == "1.2.3.4"
    assert mock_panel.port == "1234"
    assert len(mock_panel.get_status.mock_calls) == 1

    assert result["type"] == "form"
    assert result["step_id"] == "io"

    result = await flow.async_step_io(
        {
            "1": "Disabled",
            "2": "Binary Sensor",
            "3": "Digital Sensor",
            "4": "Switchable Output",
            "5": "Disabled",
            "6": "Binary Sensor",
            "7": "Digital Sensor",
            "8": "Switchable Output",
            "9": "Disabled",
            "10": "Binary Sensor",
            "11": "Digital Sensor",
            "12": "Disabled",
            "out1": "Switchable Output",
            "alarm1": "Switchable Output",
            "alarm2_out2": "Disabled",
        }
    )

    assert result["type"] == "form"
    assert result["step_id"] == "options_binary"

    result = await flow.async_step_options_binary({"type": "door"})
    assert result["type"] == "form"
    assert result["step_id"] == "options_binary"

    result = await flow.async_step_options_binary(
        {"type": "window", "name": "winder", "inverse": True}
    )
    assert result["type"] == "form"
    assert result["step_id"] == "options_binary"

    result = await flow.async_step_options_binary({"type": "door"})
    assert result["type"] == "form"
    assert result["step_id"] == "options_digital"

    result = await flow.async_step_options_digital({"type": "dht"})
    assert result["type"] == "form"
    assert result["step_id"] == "options_digital"

    result = await flow.async_step_options_digital(
        {"type": "ds18b20", "name": "temper"}
    )
    assert result["type"] == "form"
    assert result["step_id"] == "options_digital"

    result = await flow.async_step_options_digital({"type": "dht"})
    assert result["type"] == "form"
    assert result["step_id"] == "options_switch"

    result = await flow.async_step_options_switch({})
    assert result["type"] == "form"
    assert result["step_id"] == "options_switch"

    result = await flow.async_step_options_switch(
        {
            "name": "switcher",
            "activation": "low",
            "momentary": 50,
            "pause": 100,
            "repeat": 4,
        }
    )
    assert result["type"] == "form"
    assert result["step_id"] == "options_switch"

    result = await flow.async_step_options_switch({})
    assert result["type"] == "form"
    assert result["step_id"] == "options_switch"

    result = await flow.async_step_options_switch({})
    assert result["type"] == "create_entry"
    assert result["data"] == {
        "host": "1.2.3.4",
        "port": 1234,
        "id": "112233445566",
        "binary_sensors": [
            {"zone": "2", "type": "door"},
            {"zone": "6", "type": "window", "name": "winder", "inverse": True},
            {"zone": "10", "type": "door"},
        ],
        "sensors": [
            {"zone": "3", "type": "dht"},
            {"zone": "7", "type": "ds18b20", "name": "temper"},
            {"zone": "11", "type": "dht"},
        ],
        "switches": [
            {"zone": "4"},
            {
                "zone": "8",
                "name": "switcher",
                "activation": "low",
                "momentary": 50,
                "pause": 100,
                "repeat": 4,
            },
            {"zone": "out1"},
            {"zone": "alarm1"},
        ],
    }
