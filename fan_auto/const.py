"""Constants for Fan Auto Control."""

DOMAIN = "fan_auto"

CONF_TEMP = "temp_sensor"
CONF_FAN = "fan_entity"
CONF_HEAT = "heat_sensor"
CONF_HOT_OUT = "hot_out_entity"
CONF_ON_TEMP = "on_temp"
CONF_OFF_TEMP = "off_temp"
CONF_CIRC_MIN_TEMP = "circ_min_temp"
CONF_CIRC_ON_MIN = "circ_on_minutes"
CONF_CIRC_OFF_MIN = "circ_off_minutes"
CONF_OVERRIDE_MIN = "manual_override_minutes"

DEFAULT_ON_TEMP = 76
DEFAULT_OFF_TEMP = 74
DEFAULT_CIRC_MIN_TEMP = 72
DEFAULT_CIRC_ON_MIN = 5
DEFAULT_CIRC_OFF_MIN = 15
DEFAULT_OVERRIDE_MIN = 60

MODE_OFF = "off"
MODE_OVER_TEMP = "over_temp"
MODE_CIRCULATION = "air_circulation"
MODE_MANUAL = "manual"
MODE_DISABLED = "disabled"
MODES = [MODE_OFF, MODE_OVER_TEMP, MODE_CIRCULATION, MODE_MANUAL, MODE_DISABLED]
