# AGENTS.md - watch_battery

Python daemon (single file, `watch_battery.py`) for laptop power management.
Monitors battery, switches power profiles, adjusts backlight brightness, sends
notifications.

## Quick Start

```bash
pip install -r requirements   # no .txt extension
python watch_battery.py       # run from an active desktop session
```

`requirements` (no `.txt`): `dbus-python==1.3.2`, `pydbus==0.6.0`.
Only `dbus-python` is actually imported — `pydbus` is unused.

## System Requirements (hard exit if missing)

- **power-profiles-daemon** running (`net.hadess.PowerProfiles` on system bus)
- **UPower** running (`org.freedesktop.UPower` on system bus)
- Active desktop session (`org.freedesktop.Notifications`, e.g. mako/swaync)
- User in `video` group (or backlight write permission)
- udev rule at `/etc/udev/rules.d/90-backlight.rules`:
  ```
  SUBSYSTEM=="backlight", ACTION=="add", \
    RUN+="/bin/chgrp video /sys/class/backlight/%k/brightness", \
    RUN+="/bin/chmod g+w /sys/class/backlight/%k/brightness"
  ```

## Key Implementation Details

- Backlight device auto-detected from `/sys/class/backlight/` at runtime —
  never hardcode a device name (README is stale on this).
- Battery auto-detected from UPower `EnumerateDevices`; the UPower device path
  is dynamic (`/org/freedesktop/UPower/devices/battery_*`).
- Thresholds/brightness levels are class constants on `batState`.
- Main loop sleeps `time_to_sleep` seconds between sweeps.

## Development

- Single file: `watch_battery.py` — no tests, no build, no lint config.
- Python 3.6+ (uses f-strings, including multiline-brace form which is valid).
- Do NOT modularize into a package — the daemon is intentionally a single
  file.

## Verification

```bash
python -m py_compile watch_battery.py          # syntax
powerprofilesctl get                            # baseline profile
timeout 15 python watch_battery.py              # runs without error
```

## Known Bugs (fixed here, do not reintroduce)

The earlier refactor plan (docs/superpowers/plans/2026-04-23-watch-battery-refactor.md)
targeted *non-existent* "syntax errors" in the multiline f-strings — those are
valid on Python 3.6+. The real bugs it missed, now fixed:

1. Main loop used `elif` chains that made profile/brightness and notification
   branches mutually exclusive. The AC branch also required
   `active_profile == "power-saver"`, so the AC→performance transition never
   fired when already on `balanced`/`performance`. Fixed: two independent
   `if` blocks; brightness always reapplied per state; current state read at
   loop start (was `None` on first iteration).
2. `notify()` sent a non-standard `{"critical": 1}` hint — the freedesktop
   spec key is `urgency` (0=low,1=normal,2=critical). Switched to
   `{"urgency": dbus.Byte(2)}` + per-type 5-min rate limiting.
3. `get_battery_state` only handled UPower states 1/2/5, leaving
   `self.state` unset on states 3/4/6/7 → `AttributeError`. Now maps all.
4. `__detect_backlight` raised `IndexError` on an empty/missing
   `/sys/class/backlight`. Now exits with a clear error.

## Troubleshooting

Script exits with error messages on:
- UPower not running
- No battery found
- PowerProfiles daemon unavailable
- Backlight directory missing/empty
- Backlight write permission denied

Run from a terminal to see `logging.error()` output.
