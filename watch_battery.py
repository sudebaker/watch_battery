#!/usr/bin/env python

import os
import sys
from io import UnsupportedOperation
from time import sleep
import logging
import dbus


class batState():
    """Controls battery percentage,state and daemon profiles """

    # Some ideas taken from :
    # https://github.com/wogscpar/upower-python

    # Notification if battery below:
    MIN_BAT_TRIGGER = 30
    # Notification if battery over:
    MAX_BAT_TRIGGER = 80

    # Brightness in battery mode
    BRIGHTNESS_BATTERY = 30  # 25% of max brightness
    # Brightnes on ac power
    BRIGHTNESS_AC = 80  # 80% of max brightness

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
        self.__BRIGHT_DEVICE = f"/sys/class/backlight/{
            self.__detect_backlight()}/brightness"
        self.__BRIGHTNESS_MAX = f"/sys/class/backlight/{
            self.__detect_backlight()}/max_brightness"
        self.__sys_bus = dbus.SystemBus()

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
        self._ps_profile = "power-saver"
        self._bc_profile = "balanced"
        self._pf_profile = "performance"
        self.__detect_battery()
        self.get_battery_percentage(self.battery)
        self.get_battery_state(self.battery)

    def __detect_battery(self) -> list:
        """
        Detects the battery device and stores it in the battery attribute
        """
        try:
            upower_proxy = self.__sys_bus.get_object(
                self.__UPOWER_NAME, self.__UPOWER_PATH)
            upower_interface = dbus.Interface(upower_proxy, self.__UPOWER_NAME)
        except dbus.exceptions.DBusException:
            logging.error(
                "Error connecting to UPower. Is UPower running? Exiting.")
            sys.exit(1)

        try:
            devices = upower_interface.EnumerateDevices()
            self.battery = [
                device for device in devices if "battery" in device][0]
        except IndexError:
            logging.error("No battery found. Exiting.")
            sys.exit(1)

    def __detect_backlight(self) -> str:
        """
        Detects the backlight device.
        """
        backlight = os.listdir("/sys/class/backlight")
        return backlight[0]

    # get max brightness
    def get_max_brightness(self) -> int:
        """
        Gets the maximum brightness value from the backlight device.

        Returns:
            int: The maximum brightness value.
        """
        try:
            with open(self.__BRIGHTNESS_MAX, 'r') as bm:
                return int(bm.read())
        except UnsupportedOperation as e:
            logging.error(f"Error opening device {self.__BRIGHTNESS_MAX}\n")
            logging.error(e)
            sys.exit(1)

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
        except dbus.exceptions.DBusException:
            logging.error(
                "Error connecting to UPower. Is UPower running? Exiting.")
            sys.exit(1)
        try:
            self.percentage = int(battery_proxy_interface.Get(
                self.__UPOWER_NAME + ".Device", "Percentage"))
        except dbus.exceptions.DBusException:
            logging.error("Error getting battery percentage. Exiting.")
            sys.exit(1)

    def get_battery_state(self, battery) -> None:
        """
        Gets the battery state from UPower.

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

        # state 5? could be on_ac?
        if state == 1 or state == 5:
            self.state = "on_ac"
        elif state == 2:
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
        except dbus.exceptions.DBusException as e:
            logging.error("Error getting active power profile")
            logging.error(e)
            sys.exit(1)

        self.active_profile = active_profile.split(",")[0]

    def notify(self, message: str) -> None:
        """
        Sends a notification using the org.freedesktop.Notifications interface.

        Args:
            message (str): The message to display in the notification.
        """
        self.__notfy_intf.Notify(
            "", 0, "battery", "Battery Notification", f"{message}",
            [], {"critical": 1}, 5000
        )

    def set_brightness(self, brightness: int) -> None:
        """
        Sets the brightness of the backlight device.

        Args:
            brightness (int): The brightness value to set.
        """
        try:
            with open(self.__BRIGHT_DEVICE, 'w') as bd:
                bd.write(str(int(brightness)))
        except UnsupportedOperation as e:
            logging.error(f"Error opening device {self.__BRIGHT_DEVICE}\n")
            logging.error(e)
            sys.exit(1)


def watch_battery(time_to_sleep: int = 5, profile: str = "balanced") -> None:
    """seconds to sleep and default power-profile"""

    bat_stat = batState()
    bat_stat.get_available_modes()
    # Main loop
    while True:

        # check for power status, adjusting powerprofiles and brightness in consecuence
        if bat_stat.state == "on_battery" and bat_stat.active_profile != bat_stat._ps_profile:
            bat_stat.set_powerprofile(profile=bat_stat._ps_profile)
            # bat_stat.set_brightness(bat_stat.BRIGHTNESS_BATTERY)
            bat_stat.set_brightness(
                (bat_stat.BRIGHTNESS_BATTERY / 100) * bat_stat.get_max_brightness())

        elif bat_stat.state == "on_ac" and bat_stat.active_profile == bat_stat._ps_profile:
            if bat_stat._pf_profile in bat_stat.available_modes:
                bat_stat.set_powerprofile(profile=bat_stat._pf_profile)
                # print(bat_stat.active_profile, bat_stat._pf_profile)
            else:
                bat_stat.set_powerprofile(profile=bat_stat._bc_profile)
            # bat_stat.set_brightness(bat_stat.BRIGHTNESS_AC)
            bat_stat.set_brightness(
                (bat_stat.BRIGHTNESS_AC / 100) * bat_stat.get_max_brightness())

        # check for level of battery to advice
        elif bat_stat.percentage < bat_stat.MIN_BAT_TRIGGER and bat_stat.state == "on_battery":
            bat_stat.notify(
                message=f"Plug the charger, battery below {bat_stat.MIN_BAT_TRIGGER}%"
            )

        elif bat_stat.percentage > bat_stat.MAX_BAT_TRIGGER and bat_stat.state == "on_ac":
            bat_stat.notify(
                message=f"Unplug the charger, battery over {bat_stat.MAX_BAT_TRIGGER}%"
            )

        sleep(time_to_sleep)
        # getting current state
        bat_stat.get_powerprofile()
        bat_stat.get_battery_percentage(bat_stat.battery)
        bat_stat.get_battery_state(bat_stat.battery)


if __name__ == "__main__":
    watch_battery(time_to_sleep=10)
