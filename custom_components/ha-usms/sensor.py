"""Sensor platform for ha_usms."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from homeassistant.components.recorder.statistics import async_import_statistics
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.core import callback
from usms import USMSMeter

from .const import DOMAIN, LOGGER
from .entity import HaUsmsEntity

if TYPE_CHECKING:
    from homeassistant.components.recorder.models.statistics import StatisticMetaData
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import HaUsmsDataUpdateCoordinator
    from .data import HaUsmsConfigEntry


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HaUsmsConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id].coordinator

    account = coordinator.account
    meters = account.meters

    sensors = []
    for meter in meters:
        sensors.append(HaUsmsUtilityMeterRemainingUnit(coordinator, meter))
        sensors.append(HaUsmsUtilityMeterRemainingCredit(coordinator, meter))
        sensors.append(HaUsmsUtilityMeterLastUpdated(coordinator, meter))

        utility_meter_consumption = HaUsmsUtilityMeterConsumption(coordinator, meter)
        sensors.append(utility_meter_consumption)
        coordinator.meter_consumptions[meter.no] = utility_meter_consumption

    async_add_entities(sensors)


class HaUsmsUtilityMeterRemainingUnit(HaUsmsEntity, SensorEntity):
    """HaUsmsUtilityMeterRemainingUnit Sensor class."""

    _attr_native_value: float = 0.0

    def __init__(
        self,
        coordinator: HaUsmsDataUpdateCoordinator,
        meter: USMSMeter,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(coordinator)

        self.meter = meter

        self._attr_native_value = self.meter.get_remaining_unit()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Update sensor with latest data from coordinator."""
        if self.available:
            self._attr_native_value = self.meter.get_remaining_unit()

            self.async_write_ha_state()
            LOGGER.debug(f"Updated {self.unique_id}")

    @property
    def device_class(self) -> str | None:
        """Return device class."""
        if self.meter.get_type() == "Electricity":
            return SensorDeviceClass.ENERGY_STORAGE
        if self.meter.get_type() == "Water":
            return SensorDeviceClass.WATER
        return None

    @property
    def name(self) -> str:
        """Return the name of the meter."""
        return f"{self.meter.get_type()} Meter {self.meter.get_no()}"

    @property
    def native_unit_of_measurement(self) -> str:
        """Return unit of meter."""
        return self.meter.get_unit()

    @property
    def state_class(self) -> str:
        """Return state class."""
        return SensorStateClass.MEASUREMENT


class HaUsmsUtilityMeterRemainingCredit(HaUsmsEntity, SensorEntity):
    """HaUsmsUtilityMeterRemainingCredit Sensor class."""

    _attr_native_value: float = 0.0

    def __init__(
        self,
        coordinator: HaUsmsDataUpdateCoordinator,
        meter: USMSMeter,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(coordinator)

        self.meter = meter

        self._attr_native_value = self.meter.get_remaining_credit()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Update sensor with latest data from coordinator."""
        if self.available:
            self._attr_native_value = self.meter.get_remaining_credit()

            self.async_write_ha_state()
            LOGGER.debug(f"Updated {self.unique_id}")

    @property
    def device_class(self) -> str | None:
        """Return device class."""
        return SensorDeviceClass.MONETARY

    @property
    def name(self) -> str:
        """Return the name of the meter."""
        return f"{self.meter.get_type()} Meter {self.meter.get_no()} Remaining Credit"

    @property
    def native_unit_of_measurement(self) -> str:
        """Return unit of meter."""
        return "BND"

    @property
    def state_class(self) -> str:
        """Return state class."""
        return None


class HaUsmsUtilityMeterLastUpdated(HaUsmsEntity, SensorEntity):
    """HaUsmsUtilityMeterLastUpdated Sensor class."""

    _attr_native_value: datetime = datetime.min.replace(tzinfo=USMSMeter.TIMEZONE)

    def __init__(
        self,
        coordinator: HaUsmsDataUpdateCoordinator,
        meter: USMSMeter,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(coordinator)

        self.meter = meter

        self._attr_native_value = self.meter.get_last_updated()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Update sensor with latest data from coordinator."""
        if self.available:
            self._attr_native_value = self.meter.get_last_updated()

            self.async_write_ha_state()
            LOGGER.debug(f"Updated {self.unique_id}")

    @property
    def device_class(self) -> str | None:
        """Return device class."""
        return SensorDeviceClass.TIMESTAMP

    @property
    def name(self) -> str:
        """Return the name of the meter."""
        return f"{self.meter.get_type()} Meter {self.meter.get_no()} Last Updated"

    @property
    def native_unit_of_measurement(self) -> str:
        """Return unit of meter."""
        return None

    @property
    def state_class(self) -> str:
        """Return state class."""
        return None


class HaUsmsUtilityMeterConsumption(HaUsmsEntity, SensorEntity):
    """HaUsmsUtilityMeterConsumption Sensor class."""

    def __init__(
        self,
        coordinator: HaUsmsDataUpdateCoordinator,
        meter: USMSMeter,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(coordinator)

        self.meter = meter

        self._attr_native_value = None

    @callback
    def _handle_coordinator_update(self) -> None:
        """Update sensor with latest data from coordinator."""
        if self.available and not self.coordinator.data.get(self.meter.no):
            async_import_statistics(
                self.coordinator.hass,
                self.metadata,
                self.coordinator.data[self.meter.no],
            )
            LOGGER.debug(f"Updated {self.unique_id}")

    @property
    def device_class(self) -> str | None:
        """Return device class."""
        if self.meter.get_type() == "Electricity":
            return SensorDeviceClass.ENERGY
        if self.meter.get_type() == "Water":
            return SensorDeviceClass.WATER
        return None

    @property
    def metadata(self) -> StatisticMetaData:
        """Return device class."""
        return {
            "has_mean": False,
            "has_sum": True,
            "name": self.name,
            "source": "recorder",
            "statistic_id": f"sensor.{self.unique_id}",
            "unit_of_measurement": self.native_unit_of_measurement,
        }

    @property
    def name(self) -> str:
        """Return the name of the meter."""
        return f"{self.meter.get_type()} Meter {self.meter.get_no()} Consumption"

    @property
    def native_unit_of_measurement(self) -> str:
        """Return unit of meter."""
        return self.meter.get_unit()

    @property
    def state_class(self) -> str:
        """Return state class."""
        return SensorStateClass.TOTAL_INCREASING
