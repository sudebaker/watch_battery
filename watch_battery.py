#!/usr/bin/env python

import os
import sys
from io import UnsupportedOperation
from time import sleep

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
            dbus.SessionBus().get_object(self.__NOTIFICATIONS, "/" +
                                         self.__NOTIFICATIONS.replace(".", "/")), self.__NOTIFICATIONS
        )
        self.pwd = self.__sys_bus.get_object(
            self.__PROFILES_NAME, self.__PROFILES_PATH)
        self.pwd_interface = dbus.Interface(self.pwd, self.__DBUS_PROPERTIES)
        #####
        self.active_profile = None
        self._ps_profile = "power-saver"
        self._bc_profile = "balanced"
        self.__detect_battery()
        self.get_battery_percentage(self.battery)
        self.get_battery_state(self.battery)

    def __detect_battery(self) -> list:
        upower_proxy = self.__sys_bus.get_object(
            self.__UPOWER_NAME, self.__UPOWER_PATH)
        upower_interface = dbus.Interface(upower_proxy, self.__UPOWER_NAME)

        devices = upower_interface.EnumerateDevices()
        self.battery = [device for device in devices if "battery" in device][0]

    def __detect_backlight(self) -> str:
        backlight = os.listdir("/sys/class/backlight")
        return backlight[0]

    # get max brightness
    def get_max_brightness(self) -> int:
        try:
            with open(self.__BRIGHTNESS_MAX, 'r') as bm:
                return int(bm.read())
        except UnsupportedOperation as e:
            print(f"Error opening device {self.__BRIGHTNESS_MAX}\n")
            print(e)
            sys.exit(1)

    def get_battery_percentage(self, battery) -> None:
        battery_proxy = self.__sys_bus.get_object(self.__UPOWER_NAME, battery)
        battery_proxy_interface = dbus.Interface(
            battery_proxy, self.__DBUS_PROPERTIES)

        self.percentage = int(battery_proxy_interface.Get(
            self.__UPOWER_NAME + ".Device", "Percentage"))

    def get_battery_state(self, battery) -> None:
        battery_proxy = self.__sys_bus.get_object(self.__UPOWER_NAME, battery)
        battery_proxy_interface = dbus.Interface(
            battery_proxy, self.__DBUS_PROPERTIES)

        state = int(battery_proxy_interface.Get(
            self.__UPOWER_NAME + ".Device", "State"))

        # state 5? could be on_ac?
        if state == 1 or state == 5:
            self.state = "on_ac"
        elif state == 2:
            self.state = "on_battery"

    def set_powerprofile(self, profile: str) -> None:
        self.pwd_interface.Set("net.hadess.PowerProfiles",
                               "ActiveProfile", profile)

    def get_powerprofile(self) -> None:
        active_profile = self.pwd_interface.Get(
            "net.hadess.PowerProfiles", "ActiveProfile")
        self.active_profile = active_profile.split(",")[0]

    def notify(self, message: str) -> None:
        self.__notfy_intf.Notify(
            "", 0, "battery", "Battery Notification", f"{message}",
            [], {"critical": 1}, 5000
        )

    def set_brightness(self, brightness: int) -> None:
        try:
            with open(self.__BRIGHT_DEVICE, 'w') as bd:
                bd.write(str(int(brightness)))
        except UnsupportedOperation as e:
            print(f"Error opening device {self.__BRIGHT_DEVICE}\n")
            print(e)
            sys.exit(1)


def watch_battery(time_to_sleep: int = 5, profile: str = "balanced") -> None:
    """seconds to sleep and default power-profile"""

    bat_stat = batState()
    # Main loop
    while True:

        # check for power status, adjusting powerprofiles and brightness in consecuence
        if bat_stat.state == "on_battery" and bat_stat.active_profile != bat_stat._ps_profile:
            bat_stat.set_powerprofile(profile=bat_stat._ps_profile)
            # bat_stat.set_brightness(bat_stat.BRIGHTNESS_BATTERY)
            bat_stat.set_brightness(
                (bat_stat.BRIGHTNESS_BATTERY / 100) * bat_stat.get_max_brightness())

        elif bat_stat.state == "on_ac" and bat_stat.active_profile == bat_stat._ps_profile:
            bat_stat.set_powerprofile(profile=bat_stat._bc_profile)
            # bat_stat.set_brightness(bat_stat.BRIGHTNESS_AC)
            bat_stat.set_brightness(
                (bat_stat.BRIGHTNESS_AC / 100) * bat_stat.get_max_brightness())

        # check for level of battery to advice
        elif bat_stat.percentage < bat_stat.MIN_BAT_TRIGGER and bat_stat.state == "on_battery":
            bat_stat.notify(
                message=f"Plug the charger, battery below {
                    bat_stat.MIN_BAT_TRIGGER}%"
            )

        elif bat_stat.percentage > bat_stat.MAX_BAT_TRIGGER and bat_stat.state == "on_ac":
            bat_stat.notify(
                message=f"Unplug the charger, battery over {
                    bat_stat.MAX_BAT_TRIGGER}%"
            )

        sleep(time_to_sleep)
        # getting current state
        bat_stat.get_powerprofile()
        bat_stat.get_battery_percentage(bat_stat.battery)
        bat_stat.get_battery_state(bat_stat.battery)


if __name__ == "__main__":
    watch_battery(time_to_sleep=10)
