"""UI setup for Fan Auto Control."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
)

from .const import (
    CONF_CIRC_MIN_TEMP,
    CONF_CIRC_OFF_MIN,
    CONF_CIRC_ON_MIN,
    CONF_FAN,
    CONF_HEAT,
    CONF_HOT_OUT,
    CONF_OFF_TEMP,
    CONF_ON_TEMP,
    CONF_OVERRIDE_MIN,
    CONF_TEMP,
    DEFAULT_CIRC_MIN_TEMP,
    DEFAULT_CIRC_OFF_MIN,
    DEFAULT_CIRC_ON_MIN,
    DEFAULT_OFF_TEMP,
    DEFAULT_ON_TEMP,
    DEFAULT_OVERRIDE_MIN,
    DOMAIN,
)


def _num(min_v: float, max_v: float, step: float = 1, unit: str | None = None):
    return NumberSelector(
        NumberSelectorConfig(
            min=min_v,
            max=max_v,
            step=step,
            mode=NumberSelectorMode.BOX,
            unit_of_measurement=unit,
        )
    )


def _schema(d: dict[str, Any], include_fan: bool) -> vol.Schema:
    fields: dict = {
        vol.Required(
            CONF_TEMP, description={"suggested_value": d.get(CONF_TEMP)}
        ): EntitySelector(EntitySelectorConfig(domain="sensor")),
    }
    if include_fan:
        fields[
            vol.Required(CONF_FAN, description={"suggested_value": d.get(CONF_FAN)})
        ] = EntitySelector(EntitySelectorConfig(domain=["fan", "switch"]))
    fields.update(
        {
            vol.Optional(
                CONF_HEAT, description={"suggested_value": d.get(CONF_HEAT)}
            ): EntitySelector(EntitySelectorConfig(domain="binary_sensor")),
            vol.Optional(
                CONF_HOT_OUT, description={"suggested_value": d.get(CONF_HOT_OUT)}
            ): EntitySelector(
                EntitySelectorConfig(domain=["input_boolean", "binary_sensor"])
            ),
            vol.Required(
                CONF_ON_TEMP, default=d.get(CONF_ON_TEMP, DEFAULT_ON_TEMP)
            ): _num(30, 150, 0.5),
            vol.Required(
                CONF_OFF_TEMP, default=d.get(CONF_OFF_TEMP, DEFAULT_OFF_TEMP)
            ): _num(30, 150, 0.5),
            vol.Required(
                CONF_CIRC_MIN_TEMP,
                default=d.get(CONF_CIRC_MIN_TEMP, DEFAULT_CIRC_MIN_TEMP),
            ): _num(30, 150, 0.5),
            vol.Required(
                CONF_CIRC_ON_MIN, default=d.get(CONF_CIRC_ON_MIN, DEFAULT_CIRC_ON_MIN)
            ): _num(1, 120, 1, "min"),
            vol.Required(
                CONF_CIRC_OFF_MIN,
                default=d.get(CONF_CIRC_OFF_MIN, DEFAULT_CIRC_OFF_MIN),
            ): _num(1, 480, 1, "min"),
            vol.Required(
                CONF_OVERRIDE_MIN, default=d.get(CONF_OVERRIDE_MIN, DEFAULT_OVERRIDE_MIN)
            ): _num(0, 1440, 1, "min"),
        }
    )
    return vol.Schema(fields)


class FanAutoConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            if user_input[CONF_OFF_TEMP] >= user_input[CONF_ON_TEMP]:
                errors["base"] = "off_below_on"
            else:
                await self.async_set_unique_id(user_input[CONF_FAN])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"Fan Auto ({user_input[CONF_FAN]})", data=user_input
                )
        return self.async_show_form(
            step_id="user",
            data_schema=_schema(user_input or {}, include_fan=True),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return FanAutoOptionsFlow()


class FanAutoOptionsFlow(OptionsFlow):
    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            if user_input[CONF_OFF_TEMP] >= user_input[CONF_ON_TEMP]:
                errors["base"] = "off_below_on"
            else:
                # None clears optional entities the user removed
                return self.async_create_entry(
                    data={CONF_HEAT: None, CONF_HOT_OUT: None, **user_input}
                )
        current = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(
            step_id="init",
            data_schema=_schema(user_input or current, include_fan=False),
            errors=errors,
        )
