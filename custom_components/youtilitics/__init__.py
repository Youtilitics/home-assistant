"""The Youtilitics integration."""
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.config_entry_oauth2_flow import async_get_config_entry_implementation

from .const import DOMAIN, LOGGER
from .coordinator import YoutiliticsDataCoordinator

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Youtilitics integration."""
    LOGGER.info("async_setup with config: %s", config)
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Youtilitics config."""

    try:
        implementation = await async_get_config_entry_implementation(hass, entry)
    except ValueError as e:
        # Remove invalid implementation from config entry then raise AuthFailed
        hass.config_entries.async_update_entry(
            entry, data={"auth_implementation": None}
        )
        raise ConfigEntryAuthFailed from e

    # Set up coordinator to sync data
    yt_coordinator = YoutiliticsDataCoordinator(
        hass,
        entry,
        implementation
    )

    # Initial data fetch
    await yt_coordinator.async_config_entry_first_refresh()

    # Store coordinator and session
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": yt_coordinator,
        # "oauth_session": oauth_session
    }

    # Forward setup to sensor platform
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    await hass.config_entries.async_unload_platforms(entry, ["sensor"])
    hass.data[DOMAIN].pop(entry.entry_id)
    return True
