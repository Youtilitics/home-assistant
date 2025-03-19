"""Sensor platform for Youtilitics."""
from datetime import datetime, timedelta

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy, UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_interval

from . import DOMAIN, YoutiliticsDataCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    await coordinator.async_request_refresh()
    entities = []
    service_types = {value: key for key, value in coordinator.data['service_types'].items()}
    for account in coordinator.data['services']:
        for service in account['services']:
            service_type = service_types[service['type']]
            if service_type == "Electricity":
                unit = UnitOfEnergy.KILO_WATT_HOUR
            elif service_type in {"Gas", "Water"}:
                unit = UnitOfVolume.LITERS
            else:
                continue
            name = f"{service_type} with {account['utility']['name']}"
            entities.append(YoutiliticsSensor(coordinator, service['id'], name, service_type, unit))

    async_add_entities(entities)

    # Schedule daily updates
    async def update_all(now):
        for sensor in entities:
            await sensor.async_update_bulk()

    # Start updates daily at midnight (adjust time as needed)
    async_track_time_interval(hass, update_all, timedelta(minutes=100))
    await update_all(datetime.now())


class YoutiliticsSensor(SensorEntity):
    """Representation of a Youtilitics sensor."""

    def __init__(self, coordinator: YoutiliticsDataCoordinator, service_id: str, name: str, service_type: str, unit):
        """Init sensor."""
        self.entity_id = f"{DOMAIN}.{service_id.replace("-", "_")}"
        self._coordinator = coordinator
        self._service_type = service_type
        self._state = None
        self._unit = unit
        self._attr_name = name
        self._attr_state_class = "measurement"  # For history tracking
        self._service_id = service_id
        self._readings = []

    @property
    def device_class(self):
        """Type of device."""
        if self._service_type == "Electricity":
            return SensorDeviceClass.ENERGY
        if self._service_type == "Water":
            return SensorDeviceClass.WATER
        if self._service_type == "Gas":
            return SensorDeviceClass.GAS
        return None

    @property
    def icon(self):
        """Set an icon."""
        if self._service_type == "Electricity":
            return "mdi:flash"
        if self._service_type == "Water":
            return "mdi:water"
        if self._service_type == "Gas":
            return "mdi:gas-cylinder"
        return "mdi:meter"

    @property
    def state_class(self):
        """Type of state class."""
        return SensorStateClass.TOTAL_INCREASING

    async def async_update(self):
        """Update the sensor."""
        await self._coordinator.async_request_refresh()

    async def async_update_bulk(self):
        """Fetch and process 24h of data once a day."""
        readings = await self._coordinator.api.get_bulk_readings(self._service_id, self._state)
        if readings:
            self._readings = readings
            self._state = readings[-1]["timestamp"]
            await self._inject_history()

    async def _inject_history(self):
        """Push bulk data into HASS history."""
        for reading in self._readings:
            timestamp = reading["timestamp"]
            value = reading["reading"]
            self.hass.states.async_set(
                self.entity_id,
                value,
                {"unit_of_measurement": self._unit},
                force_update=True,
                timestamp=datetime.fromisoformat(timestamp).timestamp()
            )
