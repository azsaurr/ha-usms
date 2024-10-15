"""Custom types for ha_usms."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.loader import Integration

    from .coordinator import HaUsmsDataUpdateCoordinator


type HaUsmsConfigEntry = ConfigEntry[HaUsmsData]


@dataclass
class HaUsmsData:
    """Data for the HA-USMS integration."""

    coordinator: HaUsmsDataUpdateCoordinator
    integration: Integration
