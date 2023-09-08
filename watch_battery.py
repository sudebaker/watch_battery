#!/usr/bin/env python

import os
from time import sleep

import dbus


class batState():
    """Controls battery percentage,state and daemon profiles """

    # sudo su -c 'echo 12 > /sys/class/backlight/acpi_video0/brightness'

    MIN_BAT_TRIGGER = 30
    MAX_BAT_TRIGGER = 80

    def __init__(self) -> None:
        self.sys_bus = dbus.SystemBus()
        self.bat0_object = self.sys_bus.get_object(
            'org.freedesktop.UPower', '/org/freedesktop/UPower/devices/battery_BAT0'
        )
        self.bat0 = dbus.Interface(
            self.bat0_object, 'org.freedesktop.DBus.Properties'
        )
        item = "org.freedesktop.Notifications"
        self.notfy_intf = dbus.Interface(
            dbus.SessionBus().get_object(item, "/"+item.replace(".", "/")), item
        )
        self.pwd = self.sys_bus.get_object("net.hadess.PowerProfiles", "/net/hadess/PowerProfiles")
        self.pwd_interface = dbus.Interface(self.pwd, "org.freedesktop.DBus.Properties")
        #####
        self.active_profile = None
        self.ps_profile = "power-saver"
        self.bc_profile = "balanced"
        self.get_percentage()
        self.get_state()

    def get_percentage(self) -> None:
        self.percentage = float(self.bat0.Get("org.freedesktop.UPower.Device", "Percentage"))

    def get_state(self) -> None:
        state = self.bat0.Get("org.freedesktop.UPower.Device", "State")
        if state == 1:  # power ac
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


def watch_battery(time_to_sleep: int = 5, profile: str = "balanced") -> None:
    """seconds to sleep and default power-profile"""

    bat_stat = batState()
    # Main loop
    while True:
        # getting current state
        bat_stat.get_powerprofile()
        # check for power status and adjust powerprofiles
        if bat_stat.state == "on_battery" and bat_stat.active_profile == bat_stat.bc_profile:
            bat_stat.set_powerprofile(profile=bat_stat.ps_profile)

        elif bat_stat.state == "on_ac" and bat_stat.active_profile == bat_stat.ps_profile:
            bat_stat.set_powerprofile(profile=bat_stat.bc_profile)

        # check for level of battery to advice
        elif bat_stat.percentage < bat_stat.MIN_BAT_TRIGGER and bat_stat.state == "on_battery":
            bat_stat.notify(
                message=f"Plug the power, battery below {bat_stat.MIN_BAT_TRIGGER}%"
            )

        elif bat_stat.percentage > bat_stat.MAX_BAT_TRIGGER and bat_stat.state == "on_ac":
            bat_stat.notify(
                message=f"Unplug the power battery over {bat_stat.MAX_BAT_TRIGGER}%"
            )

        sleep(time_to_sleep)
        bat_stat.get_percentage()
        bat_stat.get_state()


if __name__ == "__main__":
    watch_battery(time_to_sleep=10)
