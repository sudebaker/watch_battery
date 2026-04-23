#!/usr/bin/env python

import os
import sys
import signal
from io import UnsupportedOperation
from time import sleep
import time
import logging
import dbus


# Global flag for graceful shutdown
_shutdown_requested = False


def _signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global _shutdown_requested
    logging.info(f"Received signal {signum}, shutting down gracefully...")
    _shutdown_requested = True


class BatteryMonitorError(Exception):
    """Custom exception for battery monitor initialization failures."""
    pass


class batState():
    """Controls battery percentage,state and daemon profiles """

    # Some ideas taken from :
    # https://github.com/wogscpar/upower-python

    # Notification if battery below:
    MIN_BAT_TRIGGER = 30
    # Notification if battery over:
    MAX_BAT_TRIGGER = 80

    # Brightness level as percentage of max brightness
    BRIGHTNESS_BATTERY = 30  # 30% on battery power
    # Brightness on AC power
    BRIGHTNESS_AC = 80  # 80% on AC power

    def __init__(self) -> None:
        """
        Initializes the batState class.

        Sets up the necessary DBus connections, detects the battery and backlight devices,
        and retrieves the initial battery percentage and state.
        """
        self.__UPOWER_NAME = "org.freedesktop.UPower"
        self.__UPOWER_PATH = "/org/freedesktop/UPower"
        self.__DBUS_PROPERTIES = "org.freedesktop.DBus.Properties"
        self.__PROFILES_NAME = "net.hadess.PowerProfiles"
        self.__PROFILES_PATH = "/net/hadess/PowerProfiles"
        self.__NOTIFICATIONS = "org.freedesktop.Notifications"
        backlight_device = self.__detect_backlight()
        self.__BRIGHT_DEVICE = f"/sys/class/backlight/{backlight_device}/brightness"
        self.__BRIGHTNESS_MAX = f"/sys/class/backlight/{backlight_device}/max_brightness"
        self.__sys_bus = dbus.SystemBus()

        # Cache max_brightness to avoid repeated disk reads
        self.__cached_max_brightness = self.__read_max_brightness()

        self.battery = None
        self.__notfy_intf = dbus.Interface(
            dbus.SessionBus().get_object(
                self.__NOTIFICATIONS, "/" + self.__NOTIFICATIONS.replace(".", "/")), self.__NOTIFICATIONS
        )
        self.pwd = self.__sys_bus.get_object(
            self.__PROFILES_NAME, self.__PROFILES_PATH)
        self.pwd_interface = dbus.Interface(self.pwd, self.__DBUS_PROPERTIES)
        #####
        self.active_profile = None
        # Profile name constants (matching power-profiles-daemon)
        self.PROFILE_POWER_SAVER = "power-saver"
        self.PROFILE_BALANCED = "balanced"
        self.PROFILE_PERFORMANCE = "performance"
        # Notification tracking to prevent spam
        self._last_low_notification = 0
        self._last_high_notification = 0
        self._notification_cooldown = 300  # 5 minutes between same notification
        self.__detect_battery()
        self.get_battery_percentage(self.battery)
        self.get_battery_state(self.battery)

    def __detect_battery(self) -> None:
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
            raise BatteryMonitorError(
                "Error connecting to UPower. Is UPower running?") from e

        try:
            devices = upower_interface.EnumerateDevices()
            self.battery = [
                device for device in devices if "battery" in device][0]
        except IndexError:
            raise BatteryMonitorError("No battery found on this system.")

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
            raise BatteryMonitorError(
                f"Backlight directory not found: {backlight_path}")

        if not backlight:
            raise BatteryMonitorError(
                f"No backlight devices found in {backlight_path}")

        return backlight[0]

    def __read_max_brightness(self) -> int:
        """Internal: read max brightness from hardware (once)."""
        try:
            with open(self.__BRIGHTNESS_MAX, 'r') as bm:
                return int(bm.read())
        except (UnsupportedOperation, OSError, IOError, ValueError) as e:
            logging.error(
                f"Error reading max brightness from {self.__BRIGHTNESS_MAX}")
            logging.error(e)
            sys.exit(1)

    def get_max_brightness(self) -> int:
        """
        Gets the cached maximum brightness value.

        Returns:
            int: The maximum brightness value.
        """
        return self.__cached_max_brightness

    def get_battery_percentage(self, battery) -> None:
        """
        Gets the battery percentage from UPower.

        Args:
            battery (str): The battery device path.
        """
        try:
            battery_proxy = self.__sys_bus.get_object(
                self.__UPOWER_NAME, battery)
            battery_proxy_interface = dbus.Interface(
                battery_proxy, self.__DBUS_PROPERTIES)
        except dbus.exceptions.DBusException as e:
            logging.warning(f"Error connecting to UPower: {e}")
            return
        try:
            self.percentage = int(battery_proxy_interface.Get(
                self.__UPOWER_NAME + ".Device", "Percentage"))
        except dbus.exceptions.DBusException as e:
            logging.warning(f"Error getting battery percentage: {e}")

    def get_battery_state(self, battery) -> None:
        """
        Gets the battery state from UPower.
        UPower states: 1=charging, 2=discharging, 3=empty, 4=full,
                      5=charge pending, 6=discharge pending, 7=unknown

        Args:
            battery (str): The battery device path.
        """
        try:
            battery_proxy = self.__sys_bus.get_object(
                self.__UPOWER_NAME, battery)
            battery_proxy_interface = dbus.Interface(
                battery_proxy, self.__DBUS_PROPERTIES)
            state = int(battery_proxy_interface.Get(
                self.__UPOWER_NAME + ".Device", "State"))
        except dbus.exceptions.DBusException as e:
            logging.warning(f"Error getting battery state: {e}")
            return
        except ValueError as e:
            logging.warning(f"Error parsing battery state: {e}")
            return

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
            logging.warning(
                f"Unknown battery state: {state}, assuming on_battery")
            self.state = "on_battery"

    def set_powerprofile(self, profile: str) -> None:
        """
        Sets the power profile using PowerProfiles daemon.

        Args:
            profile (str): The power profile to set.
        """
        try:
            self.pwd_interface.Set(
                "net.hadess.PowerProfiles", "ActiveProfile", profile
            )
        except dbus.exceptions.DBusException as e:
            logging.error(f"Error setting power profile to {profile}")
            logging.error(e)
            sys.exit(1)

    def get_available_modes(self) -> None:
        """
        Gets the available power profiles from PowerProfiles daemon.
        """
        try:
            available_modes = self.pwd_interface.Get(
                "net.hadess.PowerProfiles", "Profiles"
            )
        except dbus.exceptions.DBusException as e:
            logging.error("Error getting available power profiles")
            logging.error(e)
            sys.exit(1)

        # Extract profile names and store them in a set
        self.available_modes = {
            str(mode[dbus.String('Profile')]) for mode in available_modes
        }

    def get_powerprofile(self) -> None:
        """
        Gets the active power profile from PowerProfiles daemon.
        """
        try:
            active_profile = self.pwd_interface.Get(
                "net.hadess.PowerProfiles", "ActiveProfile"
            )
            self.active_profile = active_profile.split(",")[0]
        except dbus.exceptions.DBusException as e:
            logging.warning(f"Error getting active power profile: {e}")
        except Exception as e:
            logging.warning(f"Unexpected error getting power profile: {e}")

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

    def set_brightness(self, brightness: int) -> None:
        """
        Sets the brightness of the backlight device.

        Args:
            brightness (int): The brightness value to set (0-100 as percentage of max).

        Raises:
            ValueError: If brightness is outside valid range.
        """
        if not isinstance(brightness, (int, float)):
            raise ValueError(
                f"Brightness must be numeric, got {type(brightness)}")

        max_brightness = self.get_max_brightness()

        # Clamp to valid range
        brightness = max(0, min(int(brightness), max_brightness))

        logging.info(f"Writing brightness {brightness} to {self.__BRIGHT_DEVICE}")
        try:
            with open(self.__BRIGHT_DEVICE, 'w') as bd:
                bd.write(str(brightness))
            logging.info(f"Brightness successfully set to {brightness}")
        except (UnsupportedOperation, OSError, IOError, PermissionError) as e:
            logging.error(
                f"Error writing to brightness device {self.__BRIGHT_DEVICE}")
            logging.error(e)
            raise BatteryMonitorError(
                "Failed to set brightness - check permissions") from e


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

    bat_stat = batState()
    bat_stat.get_available_modes()

    # Register signal handlers
    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    # Get initial state before entering loop
    bat_stat.get_powerprofile()
    bat_stat.get_battery_percentage(bat_stat.battery)
    bat_stat.get_battery_state(bat_stat.battery)

    logging.info(f"Initial State: {bat_stat.state}, Profile: {bat_stat.active_profile}, Percentage: {bat_stat.percentage}, Available: {bat_stat.available_modes}")

    # Main loop
    while not _shutdown_requested:

        # Handle battery -> power-saver
        if bat_stat.state == "on_battery" and bat_stat.active_profile != bat_stat.PROFILE_POWER_SAVER:
            logging.info("Battery mode: setting power-saver profile and dim brightness")
            bat_stat.set_powerprofile(profile=bat_stat.PROFILE_POWER_SAVER)
            bat_stat.set_brightness(
                int((bat_stat.BRIGHTNESS_BATTERY / 100) * bat_stat.get_max_brightness()))

        # Handle AC -> performance/balanced (independent of previous state)
        if bat_stat.state == "on_ac":
            if bat_stat.active_profile != bat_stat.PROFILE_PERFORMANCE and bat_stat.PROFILE_PERFORMANCE in bat_stat.available_modes:
                logging.info("AC mode: setting performance profile")
                bat_stat.set_powerprofile(profile=bat_stat.PROFILE_PERFORMANCE)
            elif bat_stat.active_profile == bat_stat.PROFILE_POWER_SAVER:
                logging.info("AC mode: switching from power-saver to balanced")
                bat_stat.set_powerprofile(profile=bat_stat.PROFILE_BALANCED)

        # ALWAYS adjust brightness based on power source
        if bat_stat.state == "on_battery":
            new_brightness = int((bat_stat.BRIGHTNESS_BATTERY / 100) * bat_stat.get_max_brightness())
            logging.info(f"Setting battery brightness: {new_brightness}")
            bat_stat.set_brightness(new_brightness)
        elif bat_stat.state == "on_ac":
            new_brightness = int((bat_stat.BRIGHTNESS_AC / 100) * bat_stat.get_max_brightness())
            logging.info(f"Setting AC brightness: {new_brightness}")
            bat_stat.set_brightness(new_brightness)

        # Notification checks (only when on battery and low or on AC and high)
        if bat_stat.percentage < bat_stat.MIN_BAT_TRIGGER and bat_stat.state == "on_battery":
            bat_stat.notify(
                message=f"Plug the charger, battery below {bat_stat.MIN_BAT_TRIGGER}%",
                notification_type="low_battery"
            )

        if bat_stat.percentage > bat_stat.MAX_BAT_TRIGGER and bat_stat.state == "on_ac":
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
            try:
                bat_stat.get_powerprofile()
                bat_stat.get_battery_percentage(bat_stat.battery)
                bat_stat.get_battery_state(bat_stat.battery)
            except Exception as e:
                logging.error(f"Error getting state: {e}")
            logging.info(f"Loop State: {bat_stat.state}, Profile: {bat_stat.active_profile}, Percentage: {bat_stat.percentage}")

    logging.info("watch_battery daemon stopped.")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
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
