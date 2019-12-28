"""Test Konnected setup process."""
from unittest.mock import patch

from homeassistant.setup import async_setup_component
from homeassistant.components import konnected
from homeassistant.components.konnected import config_flow

from tests.common import mock_coro, MockConfigEntry


async def test_setup_with_no_config(hass):
    """Test that we do not discover anything or try to set up a Konnected panel."""
    with patch.object(hass, "config_entries") as mock_config_entries, patch.object(
        konnected, "configured_devices", return_value=[]
    ):
        assert await async_setup_component(hass, konnected.DOMAIN, {}) is True

    # No flows started
    assert len(mock_config_entries.flow.mock_calls) == 0

    # Default access token used
    assert hass.data[konnected.DOMAIN][konnected.CONF_ACCESS_TOKEN] is not None
    assert hass.data[konnected.DOMAIN][konnected.CONF_API_HOST] is None
    assert konnected.YAML_CONFIGS not in hass.data[konnected.DOMAIN]


async def test_setup_defined_hosts_known_auth(hass):
    """Test we don't initiate a config entry if configured panel is known."""
    with patch.object(hass, "config_entries") as mock_config_entries, patch.object(
        konnected, "configured_devices", return_value=["aabbccddeeff", "112233445566"]
    ):
        assert (
            await async_setup_component(
                hass,
                konnected.DOMAIN,
                {
                    konnected.DOMAIN: {
                        konnected.CONF_ACCESS_TOKEN: "abcdefgh",
                        konnected.CONF_DEVICES: [
                            {
                                config_flow.CONF_ID: "aabbccddeeff",
                                config_flow.CONF_HOST: "0.0.0.0",
                            },
                        ],
                    }
                },
            )
            is True
        )

    # Flow started for discovered panel
    assert len(mock_config_entries.flow.mock_calls) == 0


async def test_setup_defined_hosts_no_known_auth(hass):
    """Test we initiate config entry if config panel is not known."""
    with patch.object(hass, "config_entries") as mock_config_entries, patch.object(
        konnected, "configured_devices", return_value=[]
    ):
        mock_config_entries.flow.async_init.return_value = mock_coro()
        assert (
            await async_setup_component(
                hass,
                konnected.DOMAIN,
                {
                    konnected.DOMAIN: {
                        konnected.CONF_ACCESS_TOKEN: "abcdefgh",
                        konnected.CONF_DEVICES: [{konnected.CONF_ID: "aabbccddeeff"}],
                    }
                },
            )
            is True
        )

    # Flow started for discovered bridge
    assert len(mock_config_entries.flow.mock_calls) == 1
    assert mock_config_entries.flow.mock_calls[0][2]["data"] == {
        config_flow.CONF_ID: "aabbccddeeff",
        config_flow.CONF_BLINK: True,
        config_flow.CONF_DISCOVERY: True,
    }


async def test_config_passed_to_config_entry(hass):
    """Test that configured options for a host are loaded via config entry."""
    entry = MockConfigEntry(
        domain=konnected.DOMAIN,
        data={config_flow.CONF_ID: "aabbccddeeff", config_flow.CONF_HOST: "0.0.0.0"},
    )
    entry.add_to_hass(hass)
    with patch.object(konnected, "AlarmPanel") as mock_panel:
        assert (
            await async_setup_component(
                hass,
                konnected.DOMAIN,
                {
                    konnected.DOMAIN: {
                        konnected.CONF_ACCESS_TOKEN: "abcdefgh",
                        konnected.CONF_DEVICES: [{konnected.CONF_ID: "aabbccddeeff"}],
                    }
                },
            )
            is True
        )

    assert len(mock_panel.mock_calls) == 2
    p_hass, p_entry = mock_panel.mock_calls[0][1]

    assert p_hass is hass
    assert p_entry is entry


async def test_unload_entry(hass):
    """Test being able to unload an entry."""
    entry = MockConfigEntry(
        domain=konnected.DOMAIN, data={konnected.CONF_ID: "aabbccddeeff"}
    )
    entry.add_to_hass(hass)
    hass.data[konnected.DOMAIN] = {"devices": {"aabbccddeeff": "something"}}

    with patch.object(konnected, "AlarmPanel") as mock_panel:
        assert await async_setup_component(hass, konnected.DOMAIN, {}) is True

    assert len(mock_panel.return_value.mock_calls) == 1

    assert await konnected.async_unload_entry(hass, entry)
    assert hass.data[konnected.DOMAIN] == {"devices": {}}
