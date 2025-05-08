"""Youtilitics API client."""
from urllib.parse import urlencode
from typing import List, Dict

from homeassistant.helpers.config_entry_oauth2_flow import OAuth2Session
from homeassistant.core import HomeAssistant

from .const import LOGGER, API_URL
from .models import ServiceType, Account, Reading

class YoutiliticsApiError(Exception):
    """Base class for Youtilitics API errors."""

class YoutiliticsApiClient:
    """Class to manage fetching Youtilitics data."""

    def __init__(self, hass: HomeAssistant, entry, implementation) -> None:
        """Initialize the API client."""
        self.oauth_session = OAuth2Session(hass, entry, implementation)
        self.hass = hass
        self._bulk_readings: Dict[str, List[Reading]] = {}  # Store readings per service

    async def _get(self, path: str) -> Dict:
        """Make HTTP request to Youtilitics."""
        async with await self.oauth_session.async_request('GET', f"{API_URL}/{path}") as response:
            if response.status != 200:
                body = await response.text()
                raise YoutiliticsApiError(f"Error fetching data from {path}: {response.status} - {body}")
            return await response.json()

    async def services(self) -> List[Account]:
        """Fetch services."""
        data = await self._get("services")
        return [Account.from_dict(item) for item in data]

    async def service_types(self) -> ServiceType:
        """Fetch service types."""
        data = await self._get("utilities/services")
        return ServiceType.from_dict(data)

    async def get_bulk_readings(self, service_id: str, state: str | None) -> List[Reading]:
        """Fetch bulk readings from a service."""
        LOGGER.info("Loading bulk readings for %s since %s", service_id, state)
        url = f"services/{service_id}"
        if state is not None:
            query = urlencode({"last": state})
            url += f"?{query}"
        data = await self._get(url)
        readings = [Reading.from_dict(item) for item in data]
        self._bulk_readings[service_id] = readings
        return readings

    def get_readings(self, service_id: str) -> List[Reading]:
        """Get stored readings for a given service_id."""
        return self._bulk_readings.get(service_id, [])