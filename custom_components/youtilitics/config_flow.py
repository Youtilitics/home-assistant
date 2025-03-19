"""Config flow for Youtilitics."""
import logging

from homeassistant.helpers import config_entry_oauth2_flow

from .const import DOMAIN

LOGGER =  logging.getLogger(__name__)

class YoutiliticsConfigFlow(config_entry_oauth2_flow.AbstractOAuth2FlowHandler, domain=DOMAIN):
    """Handle OAuth2 config flow for Youtilitics."""

    DOMAIN = DOMAIN

    @property
    def logger(self):
        return LOGGER

    async def async_oauth_create_entry(self, data):
        """Create an entry from OAuth2 data."""
        LOGGER.info("loading from async_oauth_create_entry")
        return self.async_create_entry(title="Youtilitics", data=data)
