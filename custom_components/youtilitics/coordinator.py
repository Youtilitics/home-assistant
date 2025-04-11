"""Youtilitics data coordinator."""
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, LOGGER
from .youtilitics import YoutiliticsApiClient, YoutiliticsApiError


class YoutiliticsDataCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Youtilitics data."""

    def __init__(self, hass: HomeAssistant, entry, implementation) -> None:
        """Initialize the coordinator."""
        self.api = YoutiliticsApiClient(hass, entry, implementation)

        LOGGER.info("starting data coordinator")
        super().__init__(
            hass,
            name=DOMAIN,
            logger=LOGGER,
            update_interval=timedelta(hours=2),
        )

    async def _async_update_data(self):
        """Fetch data from API."""
        self.logger.info("coordinator: async update data")
        try:
            return {'services': await self.api.services(), 'service_types': await self.api.service_types()}
        except YoutiliticsApiError as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err

    def _async_refresh_finished(self) -> None:
        super()._async_refresh_finished()
        LOGGER.info("refresh finished: %s", self.data)
