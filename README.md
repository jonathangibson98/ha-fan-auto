# Fan Auto Control

A lightweight Home Assistant custom integration that automatically runs a fan based on temperature, with timed **air circulation** at in-between temperatures and a **manual override that is simply the fan itself**.

No helpers, no `input_select`, no YAML automations. Set it up from the UI.

## Features

- **Over-temp mode:** fan runs continuously above your ON temperature.
- **Hysteresis:** once on, the fan stays on until the temperature drops below your OFF temperature, so it doesn't flap around the threshold.
- **Air circulation mode:** between the circulation temperature and the ON temperature, the fan runs for X minutes, rests for Y minutes, and repeats.
- **Manual override = the fan:** turn the fan on or off yourself (dashboard, physical switch, voice assistant) and auto control backs off for a configurable time.
- **Optional gates:**
  - A heat sensor (`binary_sensor`) that must be on for circulation to run.
  - An "it's hot out" toggle (`input_boolean` or `binary_sensor`) that must be on for the fan to run at all.
- **Auto control switch** to pause the whole thing.
- **Mode sensor** so you can see what it's doing at a glance.
- Fully configurable from the UI, and editable later through the integration's options.

## How it decides

| Condition | Mode | Fan |
|---|---|---|
| "Hot out" toggle configured and off | `off` | Off |
| Temp above **ON temp**, or already in `over_temp` and still above **OFF temp** | `over_temp` | On (continuous) |
| Temp at or above **circulation temp** (and heat sensor on, if configured) | `air_circulation` | On X min / off Y min, repeating |
| Anything else | `off` | Off |
| Fan changed by someone/something else | `manual` | Left alone until override ends |
| Auto control switch off | `disabled` | Left alone |

Example defaults (Fahrenheit): circulate from 72, run continuously above 76, shut off below 74. Circulation runs 5 minutes on, 15 minutes off.

> Thresholds are plain numbers in whatever unit your temperature sensor reports.

## Installation

### HACS (custom repository)

1. HACS → three-dot menu → **Custom repositories**.
2. Add `https://github.com/YOUR_USERNAME/YOUR_REPO` with category **Integration**.
3. Install **Fan Auto Control** and restart Home Assistant.

### Manual

1. Copy the `custom_components/fan_auto` folder into your Home Assistant config directory:

   ```
   /config/custom_components/fan_auto/
   ```

2. Restart Home Assistant.

## Setup

1. **Settings → Devices & services → Add integration → Fan Auto Control**.
2. Fill in the form:

| Option | Required | Default | Description |
|---|---|---|---|
| Temperature sensor | Yes |  | Any `sensor` reporting a number |
| Fan | Yes |  | The real fan entity (`fan.*` or `switch.*`) |
| Heat sensor | No |  | `binary_sensor` that must be on for circulation |
| "It's hot out" toggle | No |  | `input_boolean` or `binary_sensor` that must be on for any fan activity |
| Fan ON above | Yes | 76 | Continuous run above this |
| Fan OFF below | Yes | 74 | Must be lower than ON temp |
| Start circulation at or above | Yes | 72 | Circulation begins here |
| Circulation minutes ON | Yes | 5 | Run time per cycle |
| Circulation minutes OFF | Yes | 15 | Rest time between runs |
| Manual override minutes | Yes | 60 | `0` = stay in manual until the Auto control switch is toggled off and on |

To change anything later: Devices & services → Fan Auto Control → **Configure**. The integration reloads automatically when you save.

## Entities

| Entity | Description |
|---|---|
| `sensor.<name>_mode` | `off`, `over_temp`, `air_circulation`, `manual`, or `disabled`. Has a `cycle_phase` attribute (`running` or `resting`) during circulation |
| `switch.<name>_auto_control` | Turn auto control on or off. State is remembered across restarts |

## Manual override

Auto control watches the fan. If the fan changes state and the change didn't come from this integration, it's treated as a manual action:

- Auto control stops touching the fan.
- The mode sensor shows `manual`.
- After the override time, auto control resumes and puts the fan where it should be.

Changes the fan reports back within a few seconds of a command from this integration are ignored, so a slow device echoing the command won't trigger a false override.

To end an override early, toggle **Auto control** off, then on.

## Replacing an older automation setup

If you previously used an `input_select` fan mode, a manual override `input_boolean`, and a pair of automations, this integration replaces all of it. Disable or delete the old automations so they don't fight the integration.

## Troubleshooting

- **Fan never runs:** if you set an "it's hot out" toggle, it must be on. Leave it blank if nothing in your setup turns it on.
- **Circulation never starts:** if you set a heat sensor, it must be `on`, and the temperature must be at or above the circulation temp.
- **Integration doesn't show up:** confirm `manifest.json` is at `/config/custom_components/fan_auto/manifest.json`, then restart Home Assistant.
- **Setup error:** check **Settings → System → Logs** and open an issue with the log lines.
- **Fan keeps dropping into manual:** some devices report state changes as brand-new events with no link to the command. Try raising the manual override time, or open an issue with the device type.

## Notes

- If the temperature sensor is `unknown`, `unavailable`, or non-numeric, the integration does nothing and leaves the fan where it is.
- Stopping or removing the integration does not change the fan's current state.

## License

MIT
