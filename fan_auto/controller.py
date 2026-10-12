"""Brain of Fan Auto Control."""
from __future__ import annotations

import logging
import time

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import Context, Event, HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import (
    async_call_later,
    async_track_state_change_event,
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
    MODE_CIRCULATION,
    MODE_DISABLED,
    MODE_MANUAL,
    MODE_OFF,
    MODE_OVER_TEMP,
)

_LOGGER = logging.getLogger(__name__)
ECHO_WINDOW = 15  # seconds: ignore fan state echoes of our own commands


class FanController:
    """Decides when the fan runs and notices manual use of the fan."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.cfg = {**entry.data, **entry.options}
        self.auto_enabled = True
        self.manual = False
        self.mode = MODE_OFF
        self.phase: str | None = None
        self._cycle_unsub = None
        self._manual_unsub = None
        self._unsubs: list = []
        self._ctx_ids: set[str] = set()
        self._expected: tuple[str, float] | None = None

    # ---------- plumbing ----------
    @property
    def signal(self) -> str:
        return f"{DOMAIN}_update_{self.entry.entry_id}"

    def _notify(self) -> None:
        async_dispatcher_send(self.hass, self.signal)

    def _num(self, key: str, default: float) -> float:
        try:
            return float(self.cfg.get(key, default))
        except (TypeError, ValueError):
            return default

    @callback
    def async_start(self) -> None:
        inputs = [
            e
            for e in (
                self.cfg.get(CONF_TEMP),
                self.cfg.get(CONF_HEAT),
                self.cfg.get(CONF_HOT_OUT),
            )
            if e
        ]
        self._unsubs.append(
            async_track_state_change_event(self.hass, inputs, self._on_input)
        )
        self._unsubs.append(
            async_track_state_change_event(
                self.hass, [self.cfg[CONF_FAN]], self._on_fan_change
            )
        )
        self._evaluate()

    @callback
    def async_stop(self) -> None:
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()
        self._cancel_cycle()
        self._cancel_manual_timer()

    # ---------- public controls ----------
    @callback
    def set_auto(self, enabled: bool) -> None:
        self.auto_enabled = enabled
        self.manual = False
        self._cancel_manual_timer()
        if not enabled:
            self._cancel_cycle()
        self._evaluate()

    # ---------- event handlers ----------
    @callback
    def _on_input(self, event: Event) -> None:
        self._evaluate()

    @callback
    def _on_fan_change(self, event: Event) -> None:
        new = event.data.get("new_state")
        old = event.data.get("old_state")
        if new is None or old is None:
            return
        valid = (STATE_ON, STATE_OFF)
        if new.state not in valid or old.state not in valid or new.state == old.state:
            return
        if new.context.id in self._ctx_ids:
            return  # our own command
        if (
            self._expected
            and self._expected[0] == new.state
            and time.monotonic() - self._expected[1] < ECHO_WINDOW
        ):
            return  # device echoing our own command
        if not self.auto_enabled:
            return
        _LOGGER.debug("Fan changed by someone else -> manual override")
        self._start_manual()

    # ---------- manual override ----------
    @callback
    def _start_manual(self) -> None:
        self.manual = True
        self._cancel_cycle()
        self._cancel_manual_timer()
        minutes = self._num(CONF_OVERRIDE_MIN, DEFAULT_OVERRIDE_MIN)
        if minutes > 0:
            self._manual_unsub = async_call_later(
                self.hass, minutes * 60, self._manual_expired
            )
        self._set_mode(MODE_MANUAL)

    @callback
    def _manual_expired(self, _now=None) -> None:
        self._manual_unsub = None
        self.manual = False
        self._evaluate()

    def _cancel_manual_timer(self) -> None:
        if self._manual_unsub:
            self._manual_unsub()
            self._manual_unsub = None

    # ---------- decision logic ----------
    def _temperature(self) -> float | None:
        st = self.hass.states.get(self.cfg[CONF_TEMP])
        if st is None:
            return None
        try:
            return float(st.state)
        except (TypeError, ValueError):
            return None

    def _is_on(self, entity_id: str | None) -> bool:
        if not entity_id:
            return True
        st = self.hass.states.get(entity_id)
        return st is not None and st.state == STATE_ON

    def _decide(self, temp: float) -> str:
        if not self._is_on(self.cfg.get(CONF_HOT_OUT)):
            return MODE_OFF
        on_t = self._num(CONF_ON_TEMP, DEFAULT_ON_TEMP)
        off_t = self._num(CONF_OFF_TEMP, DEFAULT_OFF_TEMP)
        circ_t = self._num(CONF_CIRC_MIN_TEMP, DEFAULT_CIRC_MIN_TEMP)
        if temp > on_t or (self.mode == MODE_OVER_TEMP and temp > off_t):
            return MODE_OVER_TEMP
        if temp >= circ_t and self._is_on(self.cfg.get(CONF_HEAT)):
            return MODE_CIRCULATION
        return MODE_OFF

    @callback
    def _evaluate(self, *_) -> None:
        if not self.auto_enabled:
            self._cancel_cycle()
            self._set_mode(MODE_DISABLED)
            return
        if self.manual:
            self._set_mode(MODE_MANUAL)
            return
        temp = self._temperature()
        if temp is None:
            return
        want = self._decide(temp)
        if want == MODE_OVER_TEMP:
            self._cancel_cycle()
            self._set_mode(want)
            self._fan(True)
        elif want == MODE_CIRCULATION:
            if self.mode != MODE_CIRCULATION:
                self._set_mode(want)
                self._cycle_on()
        else:
            self._cancel_cycle()
            self._set_mode(MODE_OFF)
            self._fan(False)

    # ---------- circulation cycle ----------
    @callback
    def _cycle_on(self, _now=None) -> None:
        self.phase = "running"
        self._fan(True)
        minutes = self._num(CONF_CIRC_ON_MIN, DEFAULT_CIRC_ON_MIN)
        self._cycle_unsub = async_call_later(self.hass, minutes * 60, self._cycle_off)
        self._notify()

    @callback
    def _cycle_off(self, _now=None) -> None:
        self.phase = "resting"
        self._fan(False)
        minutes = self._num(CONF_CIRC_OFF_MIN, DEFAULT_CIRC_OFF_MIN)
        self._cycle_unsub = async_call_later(self.hass, minutes * 60, self._cycle_on)
        self._notify()

    def _cancel_cycle(self) -> None:
        if self._cycle_unsub:
            self._cycle_unsub()
            self._cycle_unsub = None
        self.phase = None

    # ---------- helpers ----------
    def _set_mode(self, mode: str) -> None:
        if mode != self.mode:
            self.mode = mode
        self._notify()

    def _fan(self, on: bool) -> None:
        fan = self.cfg[CONF_FAN]
        want = STATE_ON if on else STATE_OFF
        st = self.hass.states.get(fan)
        if st is not None and st.state == want:
            return
        if len(self._ctx_ids) > 20:
            self._ctx_ids.clear()
        ctx = Context()
        self._ctx_ids.add(ctx.id)
        self._expected = (want, time.monotonic())
        self.hass.async_create_task(
            self.hass.services.async_call(
                "homeassistant",
                "turn_on" if on else "turn_off",
                {"entity_id": fan},
                context=ctx,
            )
        )
