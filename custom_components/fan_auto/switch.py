"""Auto control on/off switch."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_OFF
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([FanAutoSwitch(entry.runtime_data, entry)])


class FanAutoSwitch(SwitchEntity, RestoreEntity):
    _attr_has_entity_name = True
    _attr_name = "Auto control"
    _attr_should_poll = False

    def __init__(self, controller, entry: ConfigEntry) -> None:
        self._c = controller
        self._attr_unique_id = f"{entry.entry_id}_auto"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)}, name=entry.title
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is not None and last.state == STATE_OFF:
            self._c.auto_enabled = False
        self.async_on_remove(
            async_dispatcher_connect(self.hass, self._c.signal, self.async_write_ha_state)
        )

    @property
    def is_on(self) -> bool:
        return self._c.auto_enabled

    async def async_turn_on(self, **kwargs) -> None:
        self._c.set_auto(True)

    async def async_turn_off(self, **kwargs) -> None:
        self._c.set_auto(False)
