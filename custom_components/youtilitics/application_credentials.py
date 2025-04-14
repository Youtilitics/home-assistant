"""OAuth2 application credentials for Youtilitics."""
from homeassistant.components.application_credentials import (
    ClientCredential,
    AuthorizationServer,
)
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

async def async_get_authorization_server(hass: HomeAssistant) -> AuthorizationServer:
    """Return authorization server."""
    return AuthorizationServer(
        authorize_url="https://youtilitics.com/authorize",
        token_url="https://youtilitics.com/token"
    )
