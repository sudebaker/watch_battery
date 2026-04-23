# AGENTS.md - watch_battery

Python daemon for laptop power management. Monitors battery, switches power profiles, adjusts brightness, sends notifications.

## Quick Start

```bash
# Install dependencies
pip install -r requirements  # Note: no .txt extension

# Run (must be from active desktop session)
python watch_battery.py
```

## System Requirements

These are **not** optional - the script exits hard if unavailable:

- **power-profiles-daemon** running (D-Bus service)
- **UPower** running (D-Bus service)
- Active desktop session (for `org.freedesktop.Notifications`)
- User in `video` group (or have backlight write permissions)
- udev rule at `/etc/udev/rules.d/90-backlight.rules`:
  ```
  SUBSYSTEM=="backlight", ACTION=="add", \
    RUN+="/bin/chgrp video /sys/class/backlight/%k/brightness", \
    RUN+="/bin/chmod g+w /sys/class/backlight/%k/brightness"
  ```

## Key Implementation Details

- **Auto-detects backlight device** from `/sys/class/backlight/` at runtime
- **Auto-detects battery** from UPower device enumeration
- **Backlight paths** are computed dynamically - do not hardcode device names
- Thresholds and brightness levels are class constants in `batState`

## Development

- Single file: `watch_battery.py`
- No tests, no build, no lint config
- Python 3.6+ (uses f-strings)
- Main loop sleeps 10 seconds between checks (configurable via `time_to_sleep`)

## Troubleshooting

Script exits with error messages on:
- UPower not running
- No battery found
- PowerProfiles daemon unavailable
- Backlight device permission denied

Run from terminal to see `logging.error()` output.
