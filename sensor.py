"""Platform for sensor integration."""

from __future__ import annotations

import homeassistant.helpers.config_validation as cv
import logging
import voluptuous as vol


from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    PLATFORM_SCHEMA,
)
from homeassistant.components.datetime import DateTimeEntity
from homeassistant.components.number import NumberEntity
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_USERNAME,
    UnitOfEnergy,
)
from homeassistant.core import HomeAssistant

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
            # add_entities([EnergyConsumption(meter)]) # TODO

        if meter.type == "Water":
            # TODO
            continue


class EnergyUnit(SensorEntity):
    """Representation of an Energy Unit reading from a Meter."""

    _attr_has_entity_name = True

    _attr_suggested_display_precision = 3
    _attr_device_class = SensorDeviceClass.ENERGY_STORAGE
    _attr_state_class = "measurement"

    _attr_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_suggested_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR

    _attr_extra_state_attributes = {
        "credit": None,
        "last_update": None,
    }

    def __init__(self, meter) -> None:
        """Initialize an Energy Unit Meter."""
        self._meter = meter
        self._attr_name = "usms_electricity_" + meter.no + "_unit"
        self._attr_state = meter.is_active()

        self._attr_native_value = meter.get_remaining_unit()

        self._attr_extra_state_attributes["credit"] = meter.get_remaining_credit()
        self._attr_extra_state_attributes["last_update"] = meter.get_last_updated()

    def update(self) -> None:
        """Fetch new state data for the meter.

        This is the only method that should fetch new data for Home Assistant.
        """
        if self._meter.update():
            self._attr_native_value = self._meter.get_remaining_unit()

            self._attr_extra_state_attributes["credit"] = (
                self._meter.get_remaining_credit()
            )
            self._attr_extra_state_attributes["last_update"] = (
                self._meter.get_last_updated()
            )
