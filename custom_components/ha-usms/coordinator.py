"""DataUpdateCoordinator for ha_usms."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.components import recorder
from homeassistant.components.recorder.statistics import statistics_during_period
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from usms import USMSAccount, USMSConsumptionHistoryNotFoundError, USMSMeter

from .const import DOMAIN, LOGGER

if TYPE_CHECKING:
    from homeassistant.components.recorder.models.statistics import StatisticData
    from homeassistant.core import HomeAssistant

    from .data import HaUsmsConfigEntry


class HaUsmsDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    data: list[dict[str, Any]]

    def __init__(
        self,
        hass: HomeAssistant,
        entry: HaUsmsConfigEntry,
    ) -> None:
        """Initialize coordinator."""
        username = entry.data[CONF_USERNAME]
        password = entry.data[CONF_PASSWORD]

        super().__init__(
            hass=hass,
            logger=LOGGER,
            name=DOMAIN,
        )

        self.account = USMSAccount(username, password)
        self.meter_consumptions = {}

    async def _async_update_data(self) -> dict:  # noqa: PLR0912, PLR0915
        """Update data via library."""
        LOGGER.debug(f"Retrieving updates for USMS account {self.account.reg_no}.")

        """Check for updates for every meter."""
        for meter in self.account.meters:
            LOGGER.debug(f"Retrieving updates for USMS meter {meter.no}.")
            success = await self.hass.async_add_executor_job(meter.update, True)  # noqa: FBT003

            if success:
                LOGGER.debug(f"Retrieved update for USMS meter {meter.no}.")
                LOGGER.debug(f"Last updated on {meter.get_last_updated()}.")
            else:
                self.update_interval = timedelta(minutes=5)
                error = f"Error retrieving update. Retry in {self.update_interval}"
                LOGGER.error(error)
                raise UpdateFailed(error)

        """
        Use the latest update time to estimate the next update time,
        i.e. 1 hour after the latest update time.
        """
        latest_update = self.account.get_latest_update()
        next_update = latest_update + timedelta(hours=1)
        now = datetime.now(tz=USMSMeter.TIMEZONE)
        self.update_interval = next_update - now

        """Check if the estimated next update time has been passed."""
        if next_update < now:
            """If so, check for new updates again in 5 minutes."""
            self.update_interval = timedelta(minutes=5)

            error = f"{now - latest_update} since last successful update. Retry in {self.update_interval}."  # noqa: E501
            LOGGER.error(error)

            """Raise error to flag update as unsuccessful, EXCEPT on first update!"""
            if self.data:  # this checks if this is the first update (after re-init)
                """
                This prevents listeners from being called,
                and making unnecessary writes to states everytime.
                """
                raise UpdateFailed(error)

        data = {}
        for meter in self.account.meters:
            LOGGER.debug(f"Retrieving consumptions for USMS meter {meter.no}.")

            today = now.replace(hour=0, minute=0, second=0, microsecond=0)
            yesterday = today - timedelta(days=1)

            """
            Sometimes the data on the USMS site can be stealthily corrected,
            so we always re-import all hourly consumptions for the day,
            not just the latest consumption.
            """
            try:
                LOGGER.debug(
                    f"Retrieving consumptions for USMS meter {meter.no} for today."
                )
                hourly_consumptions = await self.hass.async_add_executor_job(
                    meter.get_hourly_consumptions,
                    today,
                )
            except USMSConsumptionHistoryNotFoundError:
                hourly_consumptions = {}
                LOGGER.error(
                    f"Consumptions not found yet for USMS meter {meter.no} for today."
                )

            """
            Lets re-download yesterday's data as well to be safe.
            """
            try:
                LOGGER.debug(
                    f"Retrieving consumptions for USMS meter {meter.no} for yesterday."
                )
                yesterday_hourly_consumptions = await self.hass.async_add_executor_job(
                    meter.get_hourly_consumptions,
                    yesterday,
                )
                hourly_consumptions.update(yesterday_hourly_consumptions)
            except USMSConsumptionHistoryNotFoundError:
                LOGGER.error(
                    f"Consumptions not found yet for USMS meter {meter.no} for yesterday."  # noqa: E501
                )

            """
            Skip calculating statistics for this meter if no consumption history found.
            """
            if hourly_consumptions == {}:
                LOGGER.debug(
                    f"Skipping statistics calculation for USMS meter {meter.no}."
                )
                data[meter.no] = []
                continue

            statistics = []

            """
            We want to find the last known correct sum state,
            but for that we need the metadata from the meter's sensor entity.
            """
            sensor = self.meter_consumptions.get(meter.no)
            """So first check if the sensor entity for the meter has been added."""
            if sensor:
                statistic_id = sensor.metadata["statistic_id"]

                """
                Only query for data up until two days ago.
                """
                end_time = yesterday  # until 2 days ago, 11:59PM

                old_statistics_dict = await recorder.get_instance(
                    self.hass
                ).async_add_executor_job(
                    statistics_during_period,
                    self.hass,
                    datetime.fromtimestamp(0, tz=USMSMeter.TIMEZONE),
                    end_time,
                    [statistic_id],
                    "hour",
                    None,
                    ["sum"],
                )
                old_statistics = old_statistics_dict.get(statistic_id)
                """Make sure statistic data is present in the database."""
                if old_statistics:
                    total = old_statistics[-1]["sum"]
                else:
                    """If not, then this data is likely the first in the database."""
                    total = 0

                for hourly, consumption in sorted(hourly_consumptions.items()):
                    total += consumption
                    statistic: StatisticData = {
                        "start": hourly - timedelta(hours=1),
                        "state": consumption,
                        "sum": total,
                    }
                    statistics.append(statistic)
            else:
                """If sensor entity not yet added, then no need to calculate sum."""
                for hourly, consumption in hourly_consumptions.items():
                    statistic: StatisticData = {
                        "start": hourly - timedelta(hours=1),
                        "state": consumption,
                    }
                    statistics.append(statistic)

            """Store statistics in data, to be imported by listener."""
            data[meter.no] = statistics

        LOGGER.debug(f"Retrieved updates for USMS account {self.account.reg_no}.")
        LOGGER.debug(f"Next update is on {next_update}, in {self.update_interval}.")

        return data
