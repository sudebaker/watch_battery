#!/usr/bin/env python

import sys
from io import UnsupportedOperation
from time import sleep

import dbus


class batState():
    """Controls battery percentage,state and daemon profiles """

    # Some ideas taken from :
    # https://github.com/wogscpar/upower-python

    #Notification if battery below:
    MIN_BAT_TRIGGER = 30
    # Notification if battery over:
    MAX_BAT_TRIGGER = 80
    # Adjust to your needs, device can be diferent in your case
    BRIGHT_DEVICE = "/sys/class/backlight/amdgpu_bl0/brightness"
    # Brightness in battery mode
    BRIGHTNESS_BATTERY = "40"
    # Brightnes on ac power
    BRIGHTNESS_AC = "80"

    def __init__(self) -> None:

        self.UPOWER_NAME = "org.freedesktop.UPower"
        self.UPOWER_PATH = "/org/freedesktop/UPower"
        self.DBUS_PROPERTIES = "org.freedesktop.DBus.Properties"
        self.PROFILES_NAME = "net.hadess.PowerProfiles"
        self.PROFILES_PATH = "/net/hadess/PowerProfiles"
        self.NOTIFICATIONS = "org.freedesktop.Notifications"
        self.sys_bus = dbus.SystemBus()

        self.battery = None
        self.notfy_intf = dbus.Interface(
            dbus.SessionBus().get_object(self.NOTIFICATIONS, "/"+self.NOTIFICATIONS.replace(".", "/")), self.NOTIFICATIONS
        )
        self.pwd = self.sys_bus.get_object(self.PROFILES_NAME, self.PROFILES_PATH)
        self.pwd_interface = dbus.Interface(self.pwd, self.DBUS_PROPERTIES)
        #####
        self.active_profile = None
        self.ps_profile = "power-saver"
        self.bc_profile = "balanced"
        self.detect_battery()
        self.get_battery_percentage(self.battery)
        self.get_battery_state(self.battery)

    def detect_battery(self) -> list:
        upower_proxy = self.sys_bus.get_object(self.UPOWER_NAME, self.UPOWER_PATH)
        upower_interface = dbus.Interface(upower_proxy, self.UPOWER_NAME)

        devices:list = upower_interface.EnumerateDevices()
        self.battery = [device for device in devices if "battery" in device][0]

    def get_battery_percentage(self, battery) -> None:
        battery_proxy = self.sys_bus.get_object(self.UPOWER_NAME, battery)
        battery_proxy_interface = dbus.Interface(battery_proxy, self.DBUS_PROPERTIES)

        self.percentage = int(battery_proxy_interface.Get(self.UPOWER_NAME + ".Device", "Percentage"))

    def get_battery_state(self, battery) -> None:
        battery_proxy = self.sys_bus.get_object(self.UPOWER_NAME, battery)
        battery_proxy_interface = dbus.Interface(battery_proxy, self.DBUS_PROPERTIES)

        state = int(battery_proxy_interface.Get(self.UPOWER_NAME + ".Device", "State"))

        if state == 1:
            self.state = "on_ac"
        elif state == 2:
            self.state = "on_battery"

    def set_powerprofile(self, profile: str) -> None:
        self.pwd_interface.Set("net.hadess.PowerProfiles", "ActiveProfile", profile)

    def get_powerprofile(self):
        active_profile = self.pwd_interface.Get("net.hadess.PowerProfiles", "ActiveProfile")
        self.active_profile = active_profile.split(",")[0]

    def notify(self, message: str) -> None:
        self.notfy_intf.Notify(
            "", 0, "battery", "Battery Notification", f"{message}",
            [], {"critical": 1}, 5000
        )

    def set_brightness(self, brightness: int) -> None:
        try:
            with open(self.BRIGHT_DEVICE, 'w') as bd:
                bd.write(brightness)
        except UnsupportedOperation as e:
            print(f"Error opening device {self.BRIGHT_DEVICE}\n")
            print(e)
            sys.exit(1)


def watch_battery(time_to_sleep: int = 5, profile: str = "balanced") -> None:
    """seconds to sleep and default power-profile"""

    bat_stat = batState()
    # Main loop
    while True:

        # check for power status, adjusting powerprofiles and brightness in consecuence
        if bat_stat.state == "on_battery" and bat_stat.active_profile == bat_stat.bc_profile:
            bat_stat.set_powerprofile(profile=bat_stat.ps_profile)
            bat_stat.set_brightness(bat_stat.BRIGHTNESS_BATTERY)

        elif bat_stat.state == "on_ac" and bat_stat.active_profile == bat_stat.ps_profile:
            bat_stat.set_powerprofile(profile=bat_stat.bc_profile)
            bat_stat.set_brightness(bat_stat.BRIGHTNESS_AC)

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
