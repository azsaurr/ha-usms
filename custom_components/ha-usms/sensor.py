"""Platform for sensor integration."""

from __future__ import annotations

from datetime import timedelta, datetime
import itertools
import logging
import statistics
import voluptuous as vol
from zoneinfo import ZoneInfo

import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
    PLATFORM_SCHEMA,
)
from homeassistant.components.datetime import DateTimeEntity
from homeassistant.components.number import NumberEntity
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_USERNAME,
    UnitOfEnergy,
)
from homeassistant.components.recorder.models.statistics import (
    StatisticData,
    StatisticMetaData,
)
from homeassistant.util import dt as dtutil

from homeassistant_historical_sensor import (
    HistoricalSensor,
    HistoricalState,
    PollUpdateMixin,
)

from usms import USMSAccount

_LOGGER = logging.getLogger(__name__)

# Validation of the user's configuration
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
    }
)


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the USMS platform."""
    # Assign configuration variables.
    # The configuration check takes care they are present.
    username = config[CONF_USERNAME]
    password = config.get(CONF_PASSWORD)

    # Setup connection with devices/cloud
    try:
        account = USMSAccount(username, password)
    except Exception:
        _LOGGER.error("Could not login with the given credentials")
        return

    # Add meters as entities
    for meter in account.meters:
        if not meter.is_active():
            continue

        if meter.type == "Electricity":
            add_entities([EnergyUnit(meter)])
            add_entities([EnergyConsumption(meter)])

        if meter.type == "Water":
            # TODO
            continue


class EnergyUnit(SensorEntity):
    """Representation of an Energy Unit reading from a Meter."""

    _attr_has_entity_name = True

    _attr_suggested_display_precision = 3
    _attr_device_class = SensorDeviceClass.ENERGY_STORAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    _attr_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR

    _attr_extra_state_attributes = {
        "credit": None,
        "last_update": None,
    }

    def __init__(self, meter) -> None:
        """Initialize an Energy Unit Meter."""
        super().__init__()

        self._attr_name = "usms_electricity_meter_" + meter.no + "_unit"
        self._attr_unique_id = "usms_electricity_meter_" + meter.no + "_unit"
        self._attr_entity_id = "usms_electricity_meter_" + meter.no + "_unit"

        self._attr_state = meter.is_active()

        self._attr_native_value = meter.get_remaining_unit()

        self._attr_extra_state_attributes["credit"] = meter.get_remaining_credit()
        self._attr_extra_state_attributes["last_update"] = meter.get_last_updated()

        self._meter = meter

    def update(self) -> None:
        """Fetch new state data for the meter.

        This is the only method that should fetch new data for Home Assistant.
        """

        now = datetime.now(tz=self._meter.TIMEZONE)
        if (
            now - self._attr_extra_state_attributes["last_update"]
        ).total_seconds() <= 3600:
            return

        if self._meter.update():
            self._attr_native_value = self._meter.get_remaining_unit()

            self._attr_extra_state_attributes["credit"] = (
                self._meter.get_remaining_credit()
            )
            self._attr_extra_state_attributes["last_update"] = (
                self._meter.get_last_updated()
            )

        _LOGGER.debug(f"{self._attr_name} updated")


class EnergyConsumption(PollUpdateMixin, HistoricalSensor, SensorEntity):
    """Representation of an Energy Consumption reading from a Meter."""

    _attr_has_entity_name = True

    _attr_suggested_display_precision = 3
    _attr_device_class = SensorDeviceClass.ENERGY

    _attr_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR

    _attr_extra_state_attributes = {
        "last_update": None,
    }

    def __init__(self, meter) -> None:
        """Initialize an Energy Consumption Meter."""
        super().__init__()

        self._attr_name = "usms_electricity_meter_" + meter.no + "_consumption"
        self._attr_unique_id = "usms_electricity_meter_" + meter.no + "_consumption"
        self._attr_entity_id = "usms_electricity_meter_" + meter.no + "_consumption"

        self._attr_state_class = None

        self._attr_entity_registry_enabled_default = True
        self._attr_state = None

        self._meter = meter
        self._attr_extra_state_attributes["last_update"] = meter.get_last_updated()

        self._initial = True

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

    async def async_update_historical(self):
        # Fill `HistoricalSensor._attr_historical_states` with HistoricalState's
        # This functions is equivaled to the `Sensor.async_update` from
        # HomeAssistant core
        #
        # Important: You must provide datetime with tzinfo

        # only run this once during first boot
        if self._initial:
            historical_states = await self.get_historical_states()
            self._attr_historical_states = historical_states
            self._initial = False

            _LOGGER.debug(f"{self._attr_name} initialized")
        else:
            now = datetime.now(tz=self._meter.TIMEZONE)
            if (
                now - self._attr_extra_state_attributes["last_update"]
            ).total_seconds() > 3600:
                start_date = now - timedelta(days=1)
                historical_states = await self.get_historical_states(
                    start_date=start_date
                )
                self._attr_historical_states = historical_states
                self._attr_extra_state_attributes["last_update"] = (
                    self._meter.get_last_updated()
                )

                _LOGGER.debug(f"{self._attr_name} updated")

    async def get_historical_states(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[HistoricalState]:
        """
        Returns a chronologically ascending
        list of historical states
        according to range of dates passed
        """

        # if start date is not given, just get from forever ago
        if not start_date:
            start_date = datetime.min.replace(tzinfo=self._meter.TIMEZONE)

        if end_date:
            iter_date = end_date
        # if end date is not given, just get until today
        else:
            iter_date = datetime.now(tz=self._meter.TIMEZONE)

        historical_states = []
        while iter_date >= start_date:
            try:
                hourly_consumptions = self._meter.get_hourly_consumptions(
                    datetime(iter_date.year, iter_date.month, iter_date.day)
                )

                for hour, consumption in reversed(hourly_consumptions.items()):
                    if hour == 24:
                        temp_date = iter_date + timedelta(days=1)
                        historical_state = HistoricalState(
                            state=consumption,
                            dt=dtutil.as_local(
                                datetime(
                                    temp_date.year,
                                    temp_date.month,
                                    temp_date.day,
                                    0,
                                    tzinfo=self._meter.TIMEZONE,
                                )
                            ),
                        )
                    else:
                        historical_state = HistoricalState(
                            state=consumption,
                            dt=dtutil.as_local(
                                datetime(
                                    iter_date.year,
                                    iter_date.month,
                                    iter_date.day,
                                    hour,
                                    tzinfo=self._meter.TIMEZONE,
                                )
                            ),
                        )
                    historical_states.insert(0, historical_state)
                _LOGGER.debug(
                    f"Retrieved {self._attr_name} historical data for {iter_date}"
                )
                iter_date -= timedelta(days=1)
            except Exception:
                # stops iterating once no more historical data can be obtained
                break

        return historical_states

    @property
    def statistic_id(self) -> str:
        return self.entity_id

    def get_statistic_metadata(self) -> StatisticMetaData:
        #
        # Add sum and mean to base statistics metadata
        # Important: HistoricalSensor.get_statistic_metadata returns an
        # internal source by default.
        #
        meta = super().get_statistic_metadata()
        meta["has_sum"] = True
        meta["has_mean"] = True

        return meta

    async def async_calculate_statistic_data(
        self,
        hist_states: list[HistoricalState],
        *,
        latest: dict | None = None,
    ) -> list[StatisticData]:
        #
        # Group historical states by hour
        # Calculate sum, mean, etc...
        #

        accumulated = latest["sum"] if latest else 0

        def hour_block_for_hist_state(hist_state: HistoricalState) -> datetime:
            # XX:00:00 states belongs to previous hour block
            if hist_state.dt.minute == 0 and hist_state.dt.second == 0:
                dt = hist_state.dt - timedelta(hours=1)
                return dt.replace(minute=0, second=0, microsecond=0)

            else:
                return hist_state.dt.replace(minute=0, second=0, microsecond=0)

        ret = []
        for dt, collection_it in itertools.groupby(
            hist_states,
            key=hour_block_for_hist_state,
        ):
            collection = list(collection_it)
            mean = statistics.mean([x.state for x in collection])
            partial_sum = sum([x.state for x in collection])
            accumulated = accumulated + partial_sum

            ret.append(
                StatisticData(
                    start=dt,
                    state=partial_sum,
                    mean=mean,
                    sum=accumulated,
                )
            )

        return ret
