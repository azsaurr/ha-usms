"""HA-USMS class."""

from __future__ import annotations

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import HaUsmsDataUpdateCoordinator


class HaUsmsEntity(CoordinatorEntity[HaUsmsDataUpdateCoordinator]):
    """HaUsmsEntity class."""

    coordinator: HaUsmsDataUpdateCoordinator
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: HaUsmsDataUpdateCoordinator,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)

    @property
    def unique_id(self) -> str:
        """Return unique id."""
        return f"{self.name}".lower().replace(" ", "_")
