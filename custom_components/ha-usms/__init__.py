"""The HA-USMS integration for Home Assistant."""  # noqa: N999

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.const import Platform
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.loader import async_get_loaded_integration

from .const import DOMAIN
from .coordinator import HaUsmsDataUpdateCoordinator
from .data import HaUsmsData
from .services import HaUsmsServicesSetup

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import HaUsmsConfigEntry

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HaUsmsConfigEntry,
) -> bool:
    """Set up this integration using UI."""
    hass.data.setdefault(DOMAIN, {})

    coordinator = await hass.async_add_executor_job(
        HaUsmsDataUpdateCoordinator,
        hass,
        entry,
    )
    await coordinator.async_config_entry_first_refresh()

    if not coordinator.data:
        raise ConfigEntryNotReady

    hass.data[DOMAIN][entry.entry_id] = HaUsmsData(
        integration=async_get_loaded_integration(hass, entry.domain),
        coordinator=coordinator,
    )

    # setup entities
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    # setup services
    HaUsmsServicesSetup(hass, entry)

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: HaUsmsConfigEntry,
) -> bool:
    """Handle removal of an entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(
    hass: HomeAssistant,
    entry: HaUsmsConfigEntry,
) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
