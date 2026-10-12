"""Mode sensor."""
from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, MODES


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([FanAutoModeSensor(entry.runtime_data, entry)])


class FanAutoModeSensor(SensorEntity):
    _attr_has_entity_name = True
    _attr_name = "Mode"
    _attr_should_poll = False
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = MODES

    def __init__(self, controller, entry: ConfigEntry) -> None:
        self._c = controller
        self._attr_unique_id = f"{entry.entry_id}_mode"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)}, name=entry.title
        )

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(self.hass, self._c.signal, self.async_write_ha_state)
        )

    @property
    def native_value(self) -> str:
        return self._c.mode

    @property
    def extra_state_attributes(self) -> dict:
        return {"cycle_phase": self._c.phase}
