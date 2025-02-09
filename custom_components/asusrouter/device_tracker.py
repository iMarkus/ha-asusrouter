"""AsusRouter device trackers."""

from __future__ import annotations

from typing import Any

from homeassistant.components.device_tracker import SourceType
from homeassistant.components.device_tracker.config_entry import ScannerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ASUSROUTER,
    CONF_TRACK_DEVICES,
    DEFAULT_DEVICE_NAME,
    DEFAULT_TRACK_DEVICES,
    DOMAIN,
)
from .router import ARConnectedDevice, ARDevice


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up device tracker for AsusRouter component."""

    # If device tracking is disabled
    if entry.options.get(CONF_TRACK_DEVICES, DEFAULT_TRACK_DEVICES) == False:
        return

    router = hass.data[DOMAIN][entry.entry_id][ASUSROUTER]
    tracked: set = set()

    @callback
    def update_router():
        """Update the values of the router."""

        add_entities(router, async_add_entities, tracked)

    router.async_on_close(
        async_dispatcher_connect(hass, router.signal_device_new, update_router)
    )

    update_router()


@callback
def add_entities(
    router: ARDevice,
    async_add_entities: AddEntitiesCallback,
    tracked: set[str],
) -> None:
    """Add new tracker entities from the router."""

    new_tracked = []

    for mac, device in router.devices.items():
        if mac in tracked:
            continue

        new_tracked.append(ARDeviceEntity(router, device))
        tracked.add(mac)

    if new_tracked:
        async_add_entities(new_tracked)


class ARDeviceEntity(ScannerEntity):
    """Connected device class."""

    _attr_should_poll = False

    def __init__(
        self,
        router: ARDevice,
        device: ARConnectedDevice,
    ) -> None:
        """Initialize connected device."""

        self._router = router
        self._device = device
        self._attr_unique_id = f"{router.mac}_{device.mac}"
        self._attr_name = device.name or DEFAULT_DEVICE_NAME
        self._attr_capability_attributes = {
            "mac": device.mac,
            "name": self._attr_name,
        }

    @property
    def source_type(self) -> SourceType:
        """Source type."""

        return SourceType.ROUTER

    @property
    def is_connected(self) -> bool:
        """Device status."""

        return self._device.is_connected

    @property
    def ip_address(self) -> str:
        """Device IP address."""

        return self._device.ip

    @property
    def mac_address(self) -> str:
        """Device MAC address."""

        return self._device.mac

    @property
    def hostname(self) -> str:
        """Device hostname."""

        return self._device.name

    @property
    def icon(self) -> str:
        """Device icon."""

        return "mdi:lan-connect" if self._device.is_connected else "mdi:lan-disconnect"

    @property
    def unique_id(self) -> str:
        """Unique ID of the entity."""

        return self._attr_unique_id

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""

        return dict(sorted(self._device.extra_state_attributes.items())) or {}

    @callback
    def async_on_demand_update(self) -> None:
        """Update the state."""

        if self._device.mac in self._router.devices:
            self._device = self._router.devices[self._device.mac]
            self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Register state update callback."""

        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                self._router.signal_device_update,
                self.async_on_demand_update,
            )
        )
