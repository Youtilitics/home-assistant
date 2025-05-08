"""Sensor platform for Youtilitics."""
from datetime import datetime, timedelta
import logging

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy, UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DOMAIN, YoutiliticsDataCoordinator
from .models import ServiceType

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    """Set up sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entities = []
    service_types: ServiceType = coordinator.data['service_types']
    # Create reverse mapping for service type IDs to names
    type_map = {
        service_types.electricity: "Electricity",
        service_types.gas: "Gas",
        service_types.water: "Water"
    }
    for account in coordinator.data['services']:
        for service in account.services:
            service_type = type_map.get(service.type)
            if not service_type:
                _LOGGER.warning(f"Unknown service type ID {service.type} for service {service.id}")
                continue
            if service_type == "Electricity":
                unit = UnitOfEnergy.KILO_WATT_HOUR
            elif service_type == "Gas":
                unit = UnitOfVolume.CUBIC_METERS
            elif service_type == "Water":
                unit = UnitOfVolume.LITERS
            else:
                _LOGGER.debug(f"Skipping unsupported service type {service_type} for service {service.id}")
                continue
            name_base = f"{service_type} with {account.utility.name}"
            service_id_clean = service.id.replace("-", "_")
            # Define entity IDs
            interval_entity_id = f"sensor.{DOMAIN}_{service_id_clean}_interval"
            meter_entity_id = f"sensor.{DOMAIN}_{service_id_clean}_meter"
            # Create interval sensor
            interval_sensor = YoutiliticsSensor(
                coordinator=coordinator,
                service_id=service.id,
                name=f"{name_base} Interval",
                service_type=service_type,
                unit=unit
            )
            # Create meter sensor
            meter_sensor = YoutiliticsMeterSensor(
                coordinator=coordinator,
                service_id=service.id,
                name=f"{name_base} Meter",
                service_type=service_type,
                unit=unit
            )
            # Set entity IDs explicitly
            interval_sensor.entity_id = interval_entity_id
            meter_sensor.entity_id = meter_entity_id
            _LOGGER.debug(f"Creating interval sensor with entity_id={interval_entity_id}")
            _LOGGER.debug(f"Creating meter sensor with entity_id={meter_entity_id}")
            entities.extend([interval_sensor, meter_sensor])

    async_add_entities(entities)

    # Schedule daily bulk updates at midnight
    async def update_all(now):
        for sensor in entities:
            if hasattr(sensor, 'async_update_bulk'):
                await sensor.async_update_bulk()

    async_track_time_interval(hass, update_all, timedelta(days=1))

class YoutiliticsSensor(RestoreEntity, SensorEntity):
    """Sensor for interval-based Youtilitics data (non-cumulative)."""

    def __init__(
        self,
        coordinator: YoutiliticsDataCoordinator,
        service_id: str,
        name: str,
        service_type: str,
        unit: str
    ):
        """Initialize the interval sensor."""
        super().__init__()
        self._coordinator = coordinator
        self._service_id = service_id
        self._service_type = service_type
        self._unit = unit
        self._attr_name = name
        self._attr_unique_id = f"{service_id}_interval"
        self._last_timestamp = None
        self._latest_reading = None
        self._history_backfilled = False

    @property
    def state_class(self):
        """Return the state class."""
        return SensorStateClass.MEASUREMENT

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return self._unit

    @property
    def icon(self):
        """Return an icon."""
        if self._service_type == "Electricity":
            return "mdi:flash"
        if self._service_type == "Water":
            return "mdi:water"
        if self._service_type == "Gas":
            return "mdi:gas-cylinder"
        return "mdi:meter"

    @property
    def native_value(self):
        """Return the sensor state."""
        if self._latest_reading is None:
            readings = self._coordinator.api.get_readings(self._service_id)
            if not readings:
                _LOGGER.debug(f"No readings for service {self._service_id}")
                return None
            self._latest_reading = readings[-1]
        if self._latest_reading.unit != self._unit:
            _LOGGER.warning(f"Unit mismatch for service {self._service_id}: expected {self._unit}, got {self._latest_reading.unit}")
            return None
        return self._latest_reading.reading

    @property
    def available(self) -> bool:
        """Return if the sensor is available."""
        readings = self._coordinator.api.get_readings(self._service_id)
        return bool(readings)

    async def async_update_bulk(self):
        """Fetch and process data."""
        start_time = datetime.now()
        readings = await self._coordinator.api.get_bulk_readings(self._service_id, self._last_timestamp)
        if not readings:
            _LOGGER.debug(f"No new bulk readings for service {self._service_id}")
            return

        # Sort readings by timestamp to ensure correct order
        readings.sort(key=lambda x: x.timestamp)
        # Process readings (minimal state updates during regular updates)
        for reading in readings:
            if reading.unit != self._unit:
                _LOGGER.warning(f"Skipping reading with unit {reading.unit} for service {self._service_id}")
                continue
            self._latest_reading = reading
            self._last_timestamp = reading.timestamp.isoformat()

        # Record only the latest state during regular updates
        if readings:
            latest_reading = readings[-1]
            self.hass.states.async_set(
                self.entity_id,
                latest_reading.reading,
                {"unit_of_measurement": self._unit, "last_timestamp": self._last_timestamp},
                timestamp=latest_reading.timestamp.timestamp()
            )

        elapsed = (datetime.now() - start_time).total_seconds()
        _LOGGER.info(f"Processed {len(readings)} bulk readings for service {self._service_id} in {elapsed:.2f} seconds")

    async def async_backfill_history(self):
        """Backfill historical data in the background."""
        if self._history_backfilled:
            _LOGGER.debug(f"History already backfilled for {self.entity_id}")
            return

        start_time = datetime.now()
        # Fetch all readings (initial load may have last_timestamp=None)
        readings = await self._coordinator.api.get_bulk_readings(self._service_id, None)
        if not readings:
            _LOGGER.debug(f"No readings to backfill for service {self._service_id}")
            self._history_backfilled = True
            return

        # Sort readings by timestamp
        readings.sort(key=lambda x: x.timestamp)
        # Process readings in batches (e.g., per day)
        current_day = None
        batch = []
        for reading in readings:
            if reading.unit != self._unit:
                continue
            reading_day = reading.timestamp.date()
            if current_day is None:
                current_day = reading_day
            if reading_day != current_day:
                # Process batch for the previous day
                await self._process_history_batch(batch)
                batch = []
                current_day = reading_day
            batch.append(reading)

        # Process the last batch
        if batch:
            await self._process_history_batch(batch)

        self._history_backfilled = True
        elapsed = (datetime.now() - start_time).total_seconds()
        _LOGGER.info(f"Backfilled history for {self.entity_id} with {len(readings)} readings in {elapsed:.2f} seconds")

    async def _process_history_batch(self, batch):
        """Process a batch of readings for history backfill."""
        if not batch:
            return
        # Record states for the batch (e.g., one state per hour to reduce writes)
        for i, reading in enumerate(batch):
            if i % 4 == 0:  # Write every 4th reading (once per hour)
                self.hass.states.async_set(
                    self.entity_id,
                    reading.reading,
                    {"unit_of_measurement": self._unit, "last_timestamp": reading.timestamp.isoformat()},
                    timestamp=reading.timestamp.timestamp()
                )
        # Update latest state
        self._latest_reading = batch[-1]
        self._last_timestamp = self._latest_reading.timestamp.isoformat()

    async def async_added_to_hass(self):
        """Run when entity is added to Home Assistant."""
        await super().async_added_to_hass()
        # Restore last known timestamp to avoid re-fetching old data
        last_state = await self.async_get_last_state()
        if last_state and last_state.attributes.get('last_timestamp'):
            self._last_timestamp = last_state.attributes.get('last_timestamp')
        if last_state and last_state.attributes.get('history_backfilled'):
            self._history_backfilled = last_state.attributes.get('history_backfilled') == 'true'
        # Trigger initial bulk update (minimal state updates)
        await self.async_update_bulk()
        # Start background history backfill
        self.hass.async_create_task(self.async_backfill_history())

    @property
    def extra_state_attributes(self):
        """Return additional state attributes."""
        return {
            'last_timestamp': self._last_timestamp,
            'history_backfilled': 'true' if self._history_backfilled else 'false'
        }

class YoutiliticsMeterSensor(RestoreEntity, SensorEntity):
    """Sensor for cumulative Youtilitics data (total increasing)."""

    def __init__(
        self,
        coordinator: YoutiliticsDataCoordinator,
        service_id: str,
        name: str,
        service_type: str,
        unit: str
    ):
        """Initialize the meter sensor."""
        super().__init__()
        self._coordinator = coordinator
        self._service_id = service_id
        self._service_type = service_type
        self._unit = unit
        self._attr_name = name
        self._attr_unique_id = f"{service_id}_meter"
        self._cumulative_total = 0.0
        self._last_timestamp = None
        self._last_processed_reading_id = None
        self._history_backfilled = False

    @property
    def device_class(self):
        """Return the device class."""
        if self._service_type == "Electricity":
            return SensorDeviceClass.ENERGY
        if self._service_type == "Water":
            return SensorDeviceClass.WATER
        if self._service_type == "Gas":
            return SensorDeviceClass.GAS
        return None

    @property
    def state_class(self):
        """Return the state class."""
        return SensorStateClass.TOTAL_INCREASING

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return self._unit

    @property
    def icon(self):
        """Return an icon."""
        if self._service_type == "Electricity":
            return "mdi:flash"
        if self._service_type == "Water":
            return "mdi:water"
        if self._service_type == "Gas":
            return "mdi:gas-cylinder"
        return "mdi:meter"

    @property
    def native_value(self):
        """Return the cumulative total."""
        return self._cumulative_total

    @property
    def available(self) -> bool:
        """Return if the sensor is available."""
        readings = self._coordinator.api.get_readings(self._service_id)
        return bool(readings)

    async def async_update_bulk(self):
        """Fetch and process data."""
        start_time = datetime.now()
        readings = await self._coordinator.api.get_bulk_readings(self._service_id, self._last_timestamp)
        if not readings:
            _LOGGER.debug(f"No new bulk readings for service {self._service_id}")
            return

        # Sort readings by timestamp to ensure correct order
        readings.sort(key=lambda x: x.timestamp)
        # Filter out readings already processed (using reading ID)
        if self._last_processed_reading_id is not None:
            readings = [r for r in readings if r.id > self._last_processed_reading_id]
        if not readings:
            _LOGGER.debug(f"No new readings after ID {self._last_processed_reading_id} for service {self._service_id}")
            return

        # Process readings
        for reading in readings:
            if reading.unit != self._unit:
                _LOGGER.warning(f"Skipping reading with unit {reading.unit} for service {self._service_id}")
                continue
            self._cumulative_total += reading.reading
            self._last_timestamp = reading.timestamp.isoformat()
            self._last_processed_reading_id = reading.id

        # Record only the latest state during regular updates
        if readings:
            latest_reading = readings[-1]
            self.hass.states.async_set(
                self.entity_id,
                self._cumulative_total,
                {"unit_of_measurement": self._unit, "last_timestamp": self._last_timestamp, "cumulative_total": self._cumulative_total},
                timestamp=latest_reading.timestamp.timestamp()
            )

        elapsed = (datetime.now() - start_time).total_seconds()
        _LOGGER.info(f"Processed {len(readings)} bulk readings for service {self._service_id}, total: {self._cumulative_total} in {elapsed:.2f} seconds")

    async def async_backfill_history(self):
        """Backfill historical data in the background."""
        if self._history_backfilled:
            _LOGGER.debug(f"History already backfilled for {self.entity_id}")
            return

        start_time = datetime.now()
        # Fetch all readings (initial load may have last_timestamp=None)
        readings = await self._coordinator.api.get_bulk_readings(self._service_id, None)
        if not readings:
            _LOGGER.debug(f"No readings to backfill for service {self._service_id}")
            self._history_backfilled = True
            return

        # Sort readings by timestamp
        readings.sort(key=lambda x: x.timestamp)
        # Process readings in batches (e.g., per day)
        current_day = None
        batch = []
        batch_total = self._cumulative_total
        for reading in readings:
            if reading.unit != self._unit:
                continue
            reading_day = reading.timestamp.date()
            if current_day is None:
                current_day = reading_day
            if reading_day != current_day:
                # Process batch for the previous day
                await self._process_history_batch(batch, batch_total)
                batch = []
                current_day = reading_day
            batch.append(reading)
            batch_total += reading.reading

        # Process the last batch
        if batch:
            await self._process_history_batch(batch, batch_total)

        self._history_backfilled = True
        elapsed = (datetime.now() - start_time).total_seconds()
        _LOGGER.info(f"Backfilled history for {self.entity_id} with {len(readings)} readings in {elapsed:.2f} seconds")

    async def _process_history_batch(self, batch, batch_total):
        """Process a batch of readings for history backfill."""
        if not batch:
            return
        # Record states for the batch (e.g., one state per hour to reduce writes)
        for i, reading in enumerate(batch):
            if i % 4 == 0:  # Write every 4th reading (once per hour)
                self.hass.states.async_set(
                    self.entity_id,
                    batch_total - sum(r.reading for r in batch[i+1:]) if i + 1 < len(batch) else batch_total,
                    {"unit_of_measurement": self._unit, "last_timestamp": reading.timestamp.isoformat(), "cumulative_total": batch_total},
                    timestamp=reading.timestamp.timestamp()
                )
        # Update cumulative total and last processed reading
        self._cumulative_total = batch_total
        self._last_timestamp = batch[-1].timestamp.isoformat()
        self._last_processed_reading_id = batch[-1].id

    async def async_added_to_hass(self):
        """Run when entity is added to Home Assistant."""
        await super().async_added_to_hass()
        # Restore last known state
        last_state = await self.async_get_last_state()
        if last_state:
            if last_state.attributes.get('last_timestamp'):
                self._last_timestamp = last_state.attributes.get('last_timestamp')
            if last_state.attributes.get('last_processed_reading_id'):
                self._last_processed_reading_id = last_state.attributes.get('last_processed_reading_id')
            if last_state.attributes.get('history_backfilled'):
                self._history_backfilled = last_state.attributes.get('history_backfilled') == 'true'
            if last_state.state and last_state.state != 'unknown':
                try:
                    restored_total = float(last_state.state)
                    # Only use restored total if it's higher (prevent decrease)
                    if restored_total > self._cumulative_total:
                        self._cumulative_total = restored_total
                except ValueError:
                    _LOGGER.warning(f"Invalid restored state for {self.entity_id}: {last_state.state}")
        # Trigger initial bulk update (minimal state updates)
        await self.async_update_bulk()
        # Start background history backfill
        self.hass.async_create_task(self.async_backfill_history())

    @property
    def extra_state_attributes(self):
        """Return additional state attributes."""
        return {
            'last_timestamp': self._last_timestamp,
            'cumulative_total': self._cumulative_total,
            'last_processed_reading_id': self._last_processed_reading_id,
            'history_backfilled': 'true' if self._history_backfilled else 'false'
        }
