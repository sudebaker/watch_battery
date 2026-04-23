# watch_battery Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix critical bugs, improve performance, and refactor the watch_battery daemon into a maintainable, production-ready Python application.

**Architecture:** Split the monolithic `batState` class into focused modules: configuration, battery service, notifications, and brightness control. Add proper error handling, rate limiting, and signal handling for graceful shutdown.

**Tech Stack:** Python 3.6+, dbus-python, standard library (signal, pathlib, dataclasses)

---

## Phase 1: Critical Bug Fixes

### Task 1.1: Fix Broken F-Strings (Syntax Error)

**Files:**
- Modify: `/home/amphora/Proyectos/watch_battery/watch_battery.py:40-43`

**Issue:** Lines 40-43 use broken multiline f-strings that will cause syntax errors.

- [ ] **Step 1: Fix f-string syntax in `__BRIGHT_DEVICE` and `__BRIGHTNESS_MAX`**

Replace:
```python
self.__BRIGHT_DEVICE = f"/sys/class/backlight/{
    self.__detect_backlight()}/brightness"
self.__BRIGHTNESS_MAX = f"/sys/class/backlight/{
    self.__detect_backlight()}/brightness"
```

With:
```python
backlight_device = self.__detect_backlight()
self.__BRIGHT_DEVICE = f"/sys/class/backlight/{backlight_device}/brightness"
self.__BRIGHTNESS_MAX = f"/sys/class/backlight/{backlight_device}/max_brightness"
```

- [ ] **Step 2: Verify syntax is valid**

Run: `python -m py_compile watch_battery.py`
Expected: No output (success)

- [ ] **Step 3: Commit**

```bash
git add watch_battery.py
git commit -m "fix: repair broken multiline f-strings in backlight path detection"
```

### Task 1.2: Fix Backlight Directory Empty Crash

**Files:**
- Modify: `/home/amphora/Proyectos/watch_battery/watch_battery.py:84-89`

**Issue:** `__detect_backlight()` will crash with IndexError if `/sys/class/backlight/` is empty.

- [ ] **Step 1: Add empty directory check**

Replace:
```python
def __detect_backlight(self) -> str:
    """
    Detects the backlight device.
    """
    backlight = os.listdir("/sys/class/backlight")
    return backlight[0]
```

With:
```python
def __detect_backlight(self) -> str:
    """
    Detects the backlight device.
    """
    backlight_path = "/sys/class/backlight"
    try:
        backlight = os.listdir(backlight_path)
    except FileNotFoundError:
        logging.error(f"Backlight directory not found: {backlight_path}")
        sys.exit(1)

    if not backlight:
        logging.error(f"No backlight devices found in {backlight_path}")
        sys.exit(1)

    return backlight[0]
```

- [ ] **Step 2: Verify with syntax check**

Run: `python -m py_compile watch_battery.py`

- [ ] **Step 3: Commit**

```bash
git add watch_battery.py
git commit -m "fix: handle empty backlight directory with proper error message"
```

### Task 1.3: Fix Notification Spam (Rate Limiting)

**Files:**
- Modify: `/home/amphora/Proyectos/watch_battery/watch_battery.py:11-26, 204-214, 232-276`

**Issue:** Notifications fire every 10 seconds continuously when battery is low/high, creating spam.

- [ ] **Step 1: Add notification tracking attributes to __init__**

Add to `__init__` after line 61:
```python
# Notification tracking to prevent spam
self._last_low_notification = 0
self._last_high_notification = 0
self._notification_cooldown = 300  # 5 minutes between same notification
```

- [ ] **Step 2: Add time import and import time at top**

Add at line 7 (after `import logging`):
```python
import time
```

- [ ] **Step 3: Modify notify method to support conditional notifications**

Replace the notify method (lines 204-214) with rate-limited version:
```python
def notify(self, message: str, notification_type: str = "generic") -> None:
    """
    Sends a notification using the org.freedesktop.Notifications interface.
    Rate-limited to prevent notification spam.

    Args:
        message (str): The message to display in the notification.
        notification_type (str): Type of notification for cooldown tracking.
    """
    current_time = time.time()

    if notification_type == "low_battery":
        if current_time - self._last_low_notification < self._notification_cooldown:
            return
        self._last_low_notification = current_time
    elif notification_type == "high_battery":
        if current_time - self._last_high_notification < self._notification_cooldown:
            return
        self._last_high_notification = current_time

    self.__notfy_intf.Notify(
        "", 0, "battery", "Battery Notification", f"{message}",
        [], {"urgency": 1}, 5000
    )
```

- [ ] **Step 4: Update notification calls in watch_battery function**

Replace lines 258-266:
```python
# check for level of battery to advice
elif bat_stat.percentage < bat_stat.MIN_BAT_TRIGGER and bat_stat.state == "on_battery":
    bat_stat.notify(
        message=f"Plug the charger, battery below {bat_stat.MIN_BAT_TRIGGER}%",
        notification_type="low_battery"
    )

elif bat_stat.percentage > bat_stat.MAX_BAT_TRIGGER and bat_stat.state == "on_ac":
    bat_stat.notify(
        message=f"Unplug the charger, battery over {bat_stat.MAX_BAT_TRIGGER}%",
        notification_type="high_battery"
    )
```

- [ ] **Step 5: Verify syntax**

Run: `python -m py_compile watch_battery.py`

- [ ] **Step 6: Commit**

```bash
git add watch_battery.py
git commit -m "fix: add rate limiting to prevent notification spam (5min cooldown)"
```

### Task 1.4: Fix Unused Profile Parameter

**Files:**
- Modify: `/home/amphora/Proyectos/watch_battery/watch_battery.py:232-276`

**Issue:** The `profile` parameter in `watch_battery()` is never used - the function always uses hardcoded profiles.

- [ ] **Step 1: Document the parameter or remove it**

Since the function chooses profiles based on AC/battery state, the parameter is misleading. Either:

Option A - Remove it (cleaner):
```python
def watch_battery(time_to_sleep: int = 5) -> None:
```

Option B - Use it as fallback (if chosen, update the logic to use it). Given the behavior, Option A is better.

Replace line 232:
```python
def watch_battery(time_to_sleep: int = 5) -> None:
    """Main daemon loop - seconds to sleep between checks."""
```

- [ ] **Step 2: Update docstring**

Add docstring explaining automatic profile selection:
```python
def watch_battery(time_to_sleep: int = 5) -> None:
    """
    Main daemon loop for battery monitoring.

    Automatically manages:
    - Power profiles (power-saver on battery, performance on AC)
    - Screen brightness based on power source
    - Battery level notifications with rate limiting

    Args:
        time_to_sleep: Seconds between battery state checks (default: 5)
    """
```

- [ ] **Step 3: Verify**

Run: `python -m py_compile watch_battery.py`

- [ ] **Step 4: Commit**

```bash
git add watch_battery.py
git commit -m "fix: remove unused profile parameter from watch_battery function"
```

### Task 1.5: Fix Unhandled Battery States

**Files:**
- Modify: `/home/amphora/Proyectos/watch_battery/watch_battery.py:130-153`

**Issue:** States 3, 4, 6, 7 from UPower are not handled, leaving `self.state` undefined.

- [ ] **Step 1: Add state constants and handle all cases**

Replace `get_battery_state` method (lines 130-153):
```python
def get_battery_state(self, battery) -> None:
    """
    Gets the battery state from UPower.
    UPower states: 1=charging, 2=discharging, 3=empty, 4=full,
                  5=charge pending, 6=discharge pending, 7=unknown

    Args:
        battery (str): The battery device path.
    """
    try:
        battery_proxy = self.__sys_bus.get_object(self.__UPOWER_NAME, battery)
        battery_proxy_interface = dbus.Interface(
            battery_proxy, self.__DBUS_PROPERTIES)
    except dbus.exceptions.DBusException:
        logging.error(
            "Error connecting to UPower. Is UPower running? Exiting.")
        sys.exit(1)

    state = int(battery_proxy_interface.Get(
        self.__UPOWER_NAME + ".Device", "State"))

    # Map UPower states to internal state
    if state in [1, 5]:  # Charging or Charge Pending
        self.state = "on_ac"
    elif state in [2, 6]:  # Discharging or Discharge Pending
        self.state = "on_battery"
    elif state == 4:  # Fully charged (treat as on AC)
        self.state = "on_ac"
    elif state == 3:  # Empty
        logging.warning("Battery is empty!")
        self.state = "on_battery"
    else:  # Unknown (7) or any other
        logging.warning(f"Unknown battery state: {state}, assuming on_battery")
        self.state = "on_battery"
```

- [ ] **Step 2: Verify syntax**

Run: `python -m py_compile watch_battery.py`

- [ ] **Step 3: Commit**

```bash
git add watch_battery.py
git commit -m "fix: handle all UPower battery states including edge cases"
```

---

## Phase 2: Performance Improvements

### Task 2.1: Cache max_brightness Value

**Files:**
- Modify: `/home/amphora/Proyectos/watch_battery/watch_battery.py:27-61, 91-105`

**Issue:** `get_max_brightness()` reads from disk every time brightness is set (twice per cycle).

- [ ] **Step 1: Cache max_brightness in __init__**

Add after line 43 (after setting brightness paths):
```python
# Cache max_brightness to avoid repeated disk reads
self.__cached_max_brightness = self.__read_max_brightness()
```

- [ ] **Step 2: Create private method to read max brightness**

Replace `get_max_brightness` (lines 91-105) with internal reader and public getter:
```python
def __read_max_brightness(self) -> int:
    """Internal: read max brightness from hardware (once)."""
    try:
        with open(self.__BRIGHTNESS_MAX, 'r') as bm:
            return int(bm.read())
    except (UnsupportedOperation, OSError, IOError, ValueError) as e:
        logging.error(f"Error reading max brightness from {self.__BRIGHTNESS_MAX}")
        logging.error(e)
        sys.exit(1)

def get_max_brightness(self) -> int:
    """
    Gets the cached maximum brightness value.

    Returns:
        int: The maximum brightness value.
    """
    return self.__cached_max_brightness
```

- [ ] **Step 3: Commit**

```bash
git add watch_battery.py
git commit -m "perf: cache max_brightness to avoid repeated disk reads"
```

### Task 2.2: Add Graceful Shutdown with Signal Handling

**Files:**
- Modify: `/home/amphora/Proyectos/watch_battery/watch_battery.py:1-9, 232-276`

**Issue:** Daemon cannot be gracefully shut down with Ctrl+C or system signals.

- [ ] **Step 1: Add signal handling imports**

Add at top of file (after line 8):
```python
import signal
```

- [ ] **Step 2: Create global flag for shutdown**

Add after imports (line 10):
```python
# Global flag for graceful shutdown
_shutdown_requested = False

def _signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global _shutdown_requested
    logging.info(f"Received signal {signum}, shutting down gracefully...")
    _shutdown_requested = True
```

- [ ] **Step 3: Modify main loop to check for shutdown**

Replace the `while True` loop (lines 238-272):
```python
# Register signal handlers
signal.signal(signal.SIGTERM, _signal_handler)
signal.signal(signal.SIGINT, _signal_handler)

# Main loop
while not _shutdown_requested:
    # check for power status, adjusting powerprofiles and brightness in consequence
    if bat_stat.state == "on_battery" and bat_stat.active_profile != bat_stat._ps_profile:
        bat_stat.set_powerprofile(profile=bat_stat._ps_profile)
        bat_stat.set_brightness(
            (bat_stat.BRIGHTNESS_BATTERY / 100) * bat_stat.get_max_brightness())

    elif bat_stat.state == "on_ac" and bat_stat.active_profile == bat_stat._ps_profile:
        if bat_stat._pf_profile in bat_stat.available_modes:
            bat_stat.set_powerprofile(profile=bat_stat._pf_profile)
        else:
            bat_stat.set_powerprofile(profile=bat_stat._bc_profile)
        bat_stat.set_brightness(
            (bat_stat.BRIGHTNESS_AC / 100) * bat_stat.get_max_brightness())

    # check for level of battery to advise
    elif bat_stat.percentage < bat_stat.MIN_BAT_TRIGGER and bat_stat.state == "on_battery":
        bat_stat.notify(
            message=f"Plug the charger, battery below {bat_stat.MIN_BAT_TRIGGER}%",
            notification_type="low_battery"
        )

    elif bat_stat.percentage > bat_stat.MAX_BAT_TRIGGER and bat_stat.state == "on_ac":
        bat_stat.notify(
            message=f"Unplug the charger, battery over {bat_stat.MAX_BAT_TRIGGER}%",
            notification_type="high_battery"
        )

    # Sleep with interruptible intervals
    for _ in range(time_to_sleep):
        if _shutdown_requested:
            break
        sleep(1)

    if not _shutdown_requested:
        # getting current state
        bat_stat.get_powerprofile()
        bat_stat.get_battery_percentage(bat_stat.battery)
        bat_stat.get_battery_state(bat_stat.battery)

logging.info("watch_battery daemon stopped.")
```

- [ ] **Step 4: Verify syntax**

Run: `python -m py_compile watch_battery.py`

- [ ] **Step 5: Commit**

```bash
git add watch_battery.py
git commit -m "feat: add graceful shutdown with SIGTERM/SIGINT handling"
```

---

## Phase 3: Code Quality Improvements

### Task 3.1: Fix Constructor sys.exit() Anti-pattern

**Files:**
- Modify: `/home/amphora/Proyectos/watch_battery/watch_battery.py:27-61`

**Issue:** `__init__` calls `sys.exit()` which is an anti-pattern for class constructors.

- [ ] **Step 1: Create custom exception class**

Add after imports (before class definition):
```python
class BatteryMonitorError(Exception):
    """Custom exception for battery monitor initialization failures."""
    pass
```

- [ ] **Step 2: Replace sys.exit with exceptions in __init__ and __detect_battery**

Replace `__detect_battery` (lines 63-82):
```python
def __detect_battery(self) -> list:
    """
    Detects the battery device and stores it in the battery attribute.

    Raises:
        BatteryMonitorError: If UPower is not running or no battery found.
    """
    try:
        upower_proxy = self.__sys_bus.get_object(
            self.__UPOWER_NAME, self.__UPOWER_PATH)
        upower_interface = dbus.Interface(upower_proxy, self.__UPOWER_NAME)
    except dbus.exceptions.DBusException as e:
        raise BatteryMonitorError("Error connecting to UPower. Is UPower running?") from e

    try:
        devices = upower_interface.EnumerateDevices()
        self.battery = [
            device for device in devices if "battery" in device][0]
    except IndexError:
        raise BatteryMonitorError("No battery found on this system.")
```

- [ ] **Step 3: Replace sys.exit with exceptions in __detect_backlight**

Replace `__detect_backlight`:
```python
def __detect_backlight(self) -> str:
    """
    Detects the backlight device.

    Raises:
        BatteryMonitorError: If no backlight devices found.
    """
    backlight_path = "/sys/class/backlight"
    try:
        backlight = os.listdir(backlight_path)
    except FileNotFoundError:
        raise BatteryMonitorError(f"Backlight directory not found: {backlight_path}")

    if not backlight:
        raise BatteryMonitorError(f"No backlight devices found in {backlight_path}")

    return backlight[0]
```

- [ ] **Step 4: Update main function to catch exceptions**

Replace the `if __name__` block (lines 275-276):
```python
if __name__ == "__main__":
    try:
        watch_battery(time_to_sleep=10)
    except BatteryMonitorError as e:
        logging.error(f"Failed to start battery monitor: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logging.info("Interrupted by user.")
        sys.exit(0)
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        sys.exit(1)
```

- [ ] **Step 5: Add logging configuration**

Add at the start of `if __name__` block:
```python
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    try:
        watch_battery(time_to_sleep=10)
    # ... rest of exception handling
```

- [ ] **Step 6: Commit**

```bash
git add watch_battery.py
git commit -m "refactor: replace sys.exit in constructor with proper exception handling"
```

### Task 3.2: Add Brightness Value Validation

**Files:**
- Modify: `/home/amphora/Proyectos/watch_battery/watch_battery.py:216-229`

**Issue:** `set_brightness` accepts any integer without validation.

- [ ] **Step 1: Add validation to set_brightness**

Replace `set_brightness` method:
```python
def set_brightness(self, brightness: int) -> None:
    """
    Sets the brightness of the backlight device.

    Args:
        brightness (int): The brightness value to set (0-100 as percentage of max).

    Raises:
        ValueError: If brightness is outside valid range.
    """
    if not isinstance(brightness, (int, float)):
        raise ValueError(f"Brightness must be numeric, got {type(brightness)}")

    max_brightness = self.get_max_brightness()

    # Clamp to valid range
    brightness = max(0, min(int(brightness), max_brightness))

    try:
        with open(self.__BRIGHT_DEVICE, 'w') as bd:
            bd.write(str(brightness))
        logging.debug(f"Brightness set to {brightness}")
    except (UnsupportedOperation, OSError, IOError, PermissionError) as e:
        logging.error(f"Error writing to brightness device {self.__BRIGHT_DEVICE}")
        logging.error(e)
        raise BatteryMonitorError("Failed to set brightness - check permissions") from e
```

- [ ] **Step 2: Commit**

```bash
git add watch_battery.py
git commit -m "feat: add brightness validation with bounds checking and better error handling"
```

### Task 3.3: Improve Code Documentation

**Files:**
- Modify: `/home/amphora/Proyectos/watch_battery/watch_battery.py:11-26, 56-58`

**Issue:** Constant names are cryptic and comment on line 23 is wrong.

- [ ] **Step 1: Rename profile constants to be descriptive**

Replace lines 56-58:
```python
# Profile name constants
self.PROFILE_POWER_SAVER = "power-saver"
self.PROFILE_BALANCED = "balanced"
self.PROFILE_PERFORMANCE = "performance"
```

Update all references:
- Line 241: `bat_stat._ps_profile` → `bat_stat.PROFILE_POWER_SAVER`
- Line 242: `bat_stat._ps_profile` → `bat_stat.PROFILE_POWER_SAVER`
- Line 247: `bat_stat._ps_profile` → `bat_stat.PROFILE_POWER_SAVER`
- Line 248: `bat_stat._pf_profile` → `bat_stat.PROFILE_PERFORMANCE`
- Line 250: `bat_stat._pf_profile` → `bat_stat.PROFILE_PERFORMANCE`
- Line 252: `bat_stat._bc_profile` → `bat_stat.PROFILE_BALANCED`

- [ ] **Step 2: Fix incorrect comment**

Line 23 says "25% of max brightness" but value is 30. Update comment to match or use actual percentages.

Option: Change to actual percentages and calculate dynamically:
```python
# Brightness as percentage of max (0-100)
BRIGHTNESS_BATTERY_PERCENT = 25  # 25% on battery
BRIGHTNESS_AC_PERCENT = 80       # 80% on AC
```

Or keep current approach and fix comment:
```python
# Brightness level as percentage of max brightness
BRIGHTNESS_BATTERY = 30  # 30% on battery power
BRIGHTNESS_AC = 80       # 80% on AC power
```

- [ ] **Step 3: Commit**

```bash
git add watch_battery.py
git commit -m "docs: rename cryptic profile constants and fix brightness comments"
```

---

## Phase 4: Architecture Improvements (Optional)

### Task 4.1: Create Configuration Module

**Files:**
- Create: `/home/amphora/Proyectos/watch_battery/config.py`
- Modify: `/home/amphora/Proyectos/watch_battery/watch_battery.py`

**Goal:** Extract hardcoded constants to a configuration module.

- [ ] **Step 1: Create config.py with all constants**

```python
"""Configuration for watch_battery daemon."""

# Battery thresholds for notifications (percentage)
MIN_BATTERY_THRESHOLD = 30  # Notify when below this
MAX_BATTERY_THRESHOLD = 80  # Notify when above this

# Brightness settings (percentage of max)
BRIGHTNESS_ON_BATTERY = 30
BRIGHTNESS_ON_AC = 80

# Timing settings
CHECK_INTERVAL_SECONDS = 10
NOTIFICATION_COOLDOWN_SECONDS = 300  # 5 minutes

# Power profile names (match your system's power-profiles-daemon)
PROFILE_POWER_SAVER = "power-saver"
PROFILE_BALANCED = "balanced"
PROFILE_PERFORMANCE = "performance"
```

- [ ] **Step 2: Import and use config in watch_battery.py**

Remove class constants and import from config instead.

- [ ] **Step 3: Commit**

```bash
git add config.py watch_battery.py
git commit -m "refactor: extract configuration to separate module"
```

### Task 4.2: Add Type Hints Throughout

**Files:**
- Modify: `/home/amphora/Proyectos/watch_battery/watch_battery.py`

**Goal:** Add complete type annotations for better IDE support and documentation.

- [ ] **Step 1: Add types to all methods**

Example improvements:
- `battery` parameter: `str` → `dbus.ObjectPath` or keep `str`
- Return types where missing
- Class attributes with proper types

- [ ] **Step 2: Commit**

```bash
git add watch_battery.py
git commit -m "style: add comprehensive type hints"
```

---

## Summary of Changes

### Critical Bugs Fixed:
1. ✅ Broken multiline f-strings (syntax error)
2. ✅ Empty backlight directory crash
3. ✅ Notification spam (rate limiting)
4. ✅ Unused profile parameter
5. ✅ Unhandled battery states (3, 4, 6, 7)

### Performance Improvements:
1. ✅ Cached max_brightness value
2. ✅ Graceful shutdown with signals

### Code Quality:
1. ✅ Removed sys.exit from constructor
2. ✅ Added brightness validation
3. ✅ Better error messages and logging
4. ✅ Descriptive constant names

### Optional Architecture:
1. ⬜ Configuration module
2. ⬜ Complete type hints
3. ⬜ Unit tests (out of scope)

---

## Testing Checklist

After implementing all tasks:

- [ ] Syntax validation passes: `python -m py_compile watch_battery.py`
- [ ] Can start daemon: `python watch_battery.py` (will fail if no desktop session - expected)
- [ ] Ctrl+C stops gracefully
- [ ] All commits are atomic and descriptive
- [ ] AGENTS.md updated if behavior changes significantly

---

**Plan saved to:** `docs/superpowers/plans/2026-04-23-watch-battery-refactor.md`

**Estimated effort:** 2-3 hours for all phases

**Ready for execution?** Choose:
1. **Subagent-Driven Development** - Dispatch tasks to fresh subagents
2. **Inline Execution** - Execute tasks in this session