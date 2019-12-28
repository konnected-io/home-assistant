"""Errors for the Hue component."""
from homeassistant.exceptions import HomeAssistantError


class KonnectedException(HomeAssistantError):
    """Base class for Hue exceptions."""


class CannotConnect(KonnectedException):
    """Unable to connect to the panel."""
