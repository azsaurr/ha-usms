"""Global services for HA-USMS."""

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

import voluptuous as vol
from homeassistant.components import recorder
from homeassistant.components.recorder.statistics import (
    async_import_statistics,
    statistics_during_period,
)
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import HomeAssistantError
from usms import USMSConsumptionHistoryNotFoundError, USMSMeter

from .const import DOMAIN, LOGGER
from .data import HaUsmsConfigEntry

if TYPE_CHECKING:
    from homeassistant.components.recorder.models.statistics import StatisticData

    from .coordinator import HaUsmsDataUpdateCoordinator

DOWNLOAD_METER_CONSUMPTION_HISTORY_SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required("meter_no"): str,
        vol.Optional("start"): str,
        vol.Optional("end"): str,
    }
)

RECALCULATE_METER_SUM_STATISTICS_SCHEMA = vol.Schema(
    {
        vol.Required("meter_no"): str,
    }
)

CALCULATE_COST_RESPONSE_SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required("consumption"): float,
        vol.Required("type"): str,
    }
)


class HaUsmsServicesSetup:
    """Class to handle Integration Services."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: HaUsmsConfigEntry,
    ) -> None:
        """Initialize services."""
        self.hass = hass
        self.entry = entry
        self.coordinator: HaUsmsDataUpdateCoordinator = hass.data[DOMAIN][
            entry.entry_id
        ].coordinator

        self.setup_services()

    def setup_services(self) -> None:
        """Register services."""
        self.hass.services.async_register(
            DOMAIN,
            "download_meter_consumption_history_service",
            self.download_meter_consumption_history,
            schema=DOWNLOAD_METER_CONSUMPTION_HISTORY_SERVICE_SCHEMA,
        )
        self.hass.services.async_register(
            DOMAIN,
            "recalculate_meter_sum_statistics_service",
            self.recalculate_meter_sum_statistics,
            schema=RECALCULATE_METER_SUM_STATISTICS_SCHEMA,
        )
        self.hass.services.async_register(
            DOMAIN,
            "update_meters_service",
            self.update_meters,
        )

        """Response service."""
        self.hass.services.async_register(
            DOMAIN,
            "calculate_utility_cost_response_service",
            self.calculate_utility_cost_response_service,
            schema=CALCULATE_COST_RESPONSE_SERVICE_SCHEMA,
            supports_response=SupportsResponse.ONLY,
        )

    async def download_meter_consumption_history(
        self, service_call: ServiceCall
    ) -> None:
        """Download historical data for a given meter."""
        meter_no = service_call.data["meter_no"]
        sensor = self.coordinator.meter_consumptions.get(meter_no)

        """Makes sure the given meter number exists."""
        try:
            assert sensor is not None  # noqa: S101
        except AssertionError as error:
            error_message = "Meter number does not exist."
            raise HomeAssistantError(error_message) from error

        """Sets the start date as 0001-01-01 if not given."""
        start_date = service_call.data.get("start")
        if start_date:
            start_date = datetime.strptime(start_date, "%Y-%m-%d").replace(
                tzinfo=USMSMeter.TIMEZONE,
            )
        else:
            start_date = datetime.min.replace(
                tzinfo=USMSMeter.TIMEZONE,
            )

        """Sets the end date as today if not given."""
        end_date = service_call.data.get("end")
        if end_date:
            end_date = datetime.strptime(end_date, "%Y-%m-%d").replace(
                tzinfo=USMSMeter.TIMEZONE,
            )
        else:
            end_date = datetime.now(tz=USMSMeter.TIMEZONE)

        iter_date = end_date
        historical_states = []
        """Iterates descendingly from the end date to the start date."""
        while iter_date >= start_date:
            try:
                LOGGER.debug(
                    f"Retrieving {sensor.name} historical data for {iter_date}"
                )

                hourly_consumptions = await self.hass.async_add_executor_job(
                    sensor.meter.get_hourly_consumptions, iter_date
                )

                for hourly, consumption in reversed(hourly_consumptions.items()):
                    historical_state: StatisticData = {
                        "start": hourly - timedelta(hours=1),
                        "state": consumption,
                    }
                    historical_states.insert(0, historical_state)

                LOGGER.debug(f"Retrieved {sensor.name} historical data for {iter_date}")
                iter_date -= timedelta(days=1)

            except USMSConsumptionHistoryNotFoundError:
                LOGGER.debug(
                    f"Retrieved {sensor.name} historical data until {iter_date + timedelta(days=1)}"  # noqa: E501
                )
                """Stops iterating once no more historical data can be obtained."""
                break

        """Imports the downloaded data to the statistics table."""
        async_import_statistics(self.hass, sensor.metadata, historical_states)
        """Then recalculate the sum column."""
        await self.recalculate_meter_sum_statistics(service_call)

    async def recalculate_meter_sum_statistics(self, service_call: ServiceCall) -> None:
        """Recalculates the sum statistical data for a given meter."""
        meter_no = service_call.data["meter_no"]
        sensor = self.coordinator.meter_consumptions.get(meter_no)

        """Makes sure the given meter number exists."""
        try:
            assert sensor is not None  # noqa: S101
        except AssertionError as error:
            error_message = "Meter number does not exist."
            raise HomeAssistantError(error_message) from error

        statistic_id = sensor.metadata["statistic_id"]

        """First, get all state data from the database."""
        old_statistics_dict = await recorder.get_instance(
            self.hass
        ).async_add_executor_job(
            statistics_during_period,
            self.hass,
            datetime.fromtimestamp(0, tz=USMSMeter.TIMEZONE),
            None,
            [statistic_id],
            "hour",
            None,
            ["state"],
        )
        old_statistics = old_statistics_dict.get(statistic_id)

        """But check if the data already exists in the database."""
        try:
            assert old_statistics is not None  # noqa: S101
        except AssertionError as error:
            """Otherwise there is nothing to recalculate."""
            error_message = f"No statistical data found for {statistic_id}."
            raise HomeAssistantError(error_message) from error

        """Then, calculate the accumulative sum for the states incrementally."""
        new_statistics = []
        total = 0
        for old_statistic in old_statistics:
            total += old_statistic["state"]
            start_time = datetime.fromtimestamp(
                old_statistic["start"],
                tz=USMSMeter.TIMEZONE,
            )
            new_statistic: StatisticData = {
                "start": start_time,
                "state": old_statistic["state"],
                "sum": total,
            }
            new_statistics.append(new_statistic)

        """Re-import the new data into the database."""
        async_import_statistics(self.hass, sensor.metadata, new_statistics)
        LOGGER.debug(f"Recalculated sum statistics for {sensor.unique_id}")

    async def update_meters(self, service_call: ServiceCall) -> None:  # noqa: ARG002
        """Force update all meters."""
        LOGGER.debug("Manually updating all meters.")

        await self.coordinator.async_request_refresh()

    async def calculate_utility_cost_response_service(
        self,
        service_call: ServiceCall,
    ) -> None:
        """
        Calculate total cost of utility usage.

        Calculates and returns the total cost
        for a given utility consumption
        according to the utility type's tariff.
        """
        consumption = service_call.data["consumption"]
        meter_type = service_call.data["meter_type"]

        if "electric" in meter_type.lower():
            meter_type = "Electricity"
        elif "water" in meter_type.lower():
            meter_type = "Water"
        else:
            error = "Meter type not valid."
            raise HomeAssistantError(error)

        cost = USMSMeter.calculate_cost(consumption, "Electricity")

        return {"cost": cost}
