"""OAuth2 application credentials for Youtilitics."""
from homeassistant.components.application_credentials import ClientCredential
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_entry_oauth2_flow

from .oauth import YoutiliticsUserImplementation

async def async_get_auth_implementation(
    hass: HomeAssistant, auth_domain: str, credential: ClientCredential
) -> config_entry_oauth2_flow.AbstractOAuth2Implementation:
    """Return auth implementation."""
    return YoutiliticsUserImplementation(
        hass,
        auth_domain,
        credential,
    )
