#!/usr/bin/env python

import sys
from io import UnsupportedOperation
from time import sleep

import dbus


class UPowerManager():

    def __init__(self):
        self.UPOWER_NAME = "org.freedesktop.UPower"
        self.UPOWER_PATH = "/org/freedesktop/UPower"

        self.DBUS_PROPERTIES = "org.freedesktop.DBus.Properties"
        self.bus = dbus.SystemBus()

    def detect_devices(self):
        upower_proxy = self.bus.get_object(self.UPOWER_NAME, self.UPOWER_PATH) 
        upower_interface = dbus.Interface(upower_proxy, self.UPOWER_NAME)

        devices = upower_interface.EnumerateDevices()
        return devices

    def get_display_device(self):
        upower_proxy = self.bus.get_object(self.UPOWER_NAME, self.UPOWER_PATH) 
        upower_interface = dbus.Interface(upower_proxy, self.UPOWER_NAME)

        dispdev = upower_interface.GetDisplayDevice()
        return dispdev

    def get_critical_action(self):
        upower_proxy = self.bus.get_object(self.UPOWER_NAME, self.UPOWER_PATH) 
        upower_interface = dbus.Interface(upower_proxy, self.UPOWER_NAME)
        
        critical_action = upower_interface.GetCriticalAction()
        return critical_action

    def get_device_percentage(self, battery):
        battery_proxy = self.bus.get_object(self.UPOWER_NAME, battery)
        battery_proxy_interface = dbus.Interface(battery_proxy, self.DBUS_PROPERTIES)

        return battery_proxy_interface.Get(self.UPOWER_NAME + ".Device", "Percentage")
   
    def get_full_device_information(self, battery):
        battery_proxy = self.bus.get_object(self.UPOWER_NAME, battery)
        battery_proxy_interface = dbus.Interface(battery_proxy, self.DBUS_PROPERTIES)

        hasHistory = battery_proxy_interface.Get(self.UPOWER_NAME + ".Device", "HasHistory")
        hasStatistics = battery_proxy_interface.Get(self.UPOWER_NAME + ".Device", "HasStatistics")
        isPresent = battery_proxy_interface.Get(self.UPOWER_NAME + ".Device", "IsPresent")
        isRechargable = battery_proxy_interface.Get(self.UPOWER_NAME + ".Device", "IsRechargeable")
        online = battery_proxy_interface.Get(self.UPOWER_NAME + ".Device", "Online")
        powersupply = battery_proxy_interface.Get(self.UPOWER_NAME + ".Device", "PowerSupply")
        capacity = battery_proxy_interface.Get(self.UPOWER_NAME + ".Device", "Capacity")
        energy = battery_proxy_interface.Get(self.UPOWER_NAME + ".Device", "Energy")
        energyempty = battery_proxy_interface.Get(self.UPOWER_NAME + ".Device", "EnergyEmpty")
        energyfull = battery_proxy_interface.Get(self.UPOWER_NAME + ".Device", "EnergyFull")
        energyfulldesign = battery_proxy_interface.Get(self.UPOWER_NAME + ".Device", "EnergyFullDesign")
        energyrate = battery_proxy_interface.Get(self.UPOWER_NAME + ".Device", "EnergyRate")
        luminosity = battery_proxy_interface.Get(self.UPOWER_NAME + ".Device", "Luminosity")
        percentage = battery_proxy_interface.Get(self.UPOWER_NAME + ".Device", "Percentage")
        temperature = battery_proxy_interface.Get(self.UPOWER_NAME + ".Device", "Temperature")
        voltage = battery_proxy_interface.Get(self.UPOWER_NAME + ".Device", "Voltage")
        timetoempty = battery_proxy_interface.Get(self.UPOWER_NAME + ".Device", "TimeToEmpty")
        timetofull = battery_proxy_interface.Get(self.UPOWER_NAME + ".Device", "TimeToFull")
        iconname = battery_proxy_interface.Get(self.UPOWER_NAME + ".Device", "IconName")
        model = battery_proxy_interface.Get(self.UPOWER_NAME + ".Device", "Model")
        nativepath = battery_proxy_interface.Get(self.UPOWER_NAME + ".Device", "NativePath")
        serial = battery_proxy_interface.Get(self.UPOWER_NAME + ".Device", "Serial")
        vendor = battery_proxy_interface.Get(self.UPOWER_NAME + ".Device", "Vendor")
        state = battery_proxy_interface.Get(self.UPOWER_NAME + ".Device", "State")
        technology = battery_proxy_interface.Get(self.UPOWER_NAME + ".Device", "Technology")
        battype = battery_proxy_interface.Get(self.UPOWER_NAME + ".Device", "Type")
        warninglevel = battery_proxy_interface.Get(self.UPOWER_NAME + ".Device", "WarningLevel")
        updatetime = battery_proxy_interface.Get(self.UPOWER_NAME + ".Device", "UpdateTime")


        information_table = {
                'HasHistory': hasHistory,
                'HasStatistics': hasStatistics,
                'IsPresent': isPresent,
                'IsRechargeable': isRechargable,
                'Online': online,
                'PowerSupply': powersupply,
                'Capacity': capacity,
                'Energy': energy,
                'EnergyEmpty': energyempty,
                'EnergyFull': energyfull,
                'EnergyFullDesign': energyfulldesign,
                'EnergyRate': energyrate,
                'Luminosity': luminosity,
                'Percentage': percentage,
                'Temperature': temperature,
                'Voltage': voltage,
                'TimeToEmpty': timetoempty,
                'TimeToFull': timetofull,
                'IconName': iconname,
                'Model': model,
                'NativePath': nativepath,
                'Serial': serial,
                'Vendor': vendor,
                'State': state,
                'Technology': technology,
                'Type': battype,
                'WarningLevel': warninglevel,
                'UpdateTime': updatetime
                }

        return information_table

    def is_lid_present(self):
        upower_proxy = self.bus.get_object(self.UPOWER_NAME, self.UPOWER_PATH) 
        upower_interface = dbus.Interface(upower_proxy, self.DBUS_PROPERTIES)

        is_lid_present = bool(upower_interface.Get(self.UPOWER_NAME, 'LidIsPresent'))
        return is_lid_present

    def is_lid_closed(self):
        upower_proxy = self.bus.get_object(self.UPOWER_NAME, self.UPOWER_PATH) 
        upower_interface = dbus.Interface(upower_proxy, self.DBUS_PROPERTIES)

        is_lid_closed = bool(upower_interface.Get(self.UPOWER_NAME, 'LidIsClosed'))
        return is_lid_closed

    def on_battery(self):
        upower_proxy = self.bus.get_object(self.UPOWER_NAME, self.UPOWER_PATH) 
        upower_interface = dbus.Interface(upower_proxy, self.DBUS_PROPERTIES)

        on_battery = bool(upower_interface.Get(self.UPOWER_NAME, 'OnBattery'))
        return on_battery

    def has_wakeup_capabilities(self):
        upower_proxy = self.bus.get_object(self.UPOWER_NAME, self.UPOWER_PATH + "/Wakeups") 
        upower_interface = dbus.Interface(upower_proxy, self.DBUS_PROPERTIES)

        has_wakeup_capabilities = bool(upower_interface.Get(self.UPOWER_NAME+ '.Wakeups', 'HasCapability'))
        return has_wakeup_capabilities

    def get_wakeups_data(self):
        upower_proxy = self.bus.get_object(self.UPOWER_NAME, self.UPOWER_PATH + "/Wakeups") 
        upower_interface = dbus.Interface(upower_proxy, self.UPOWER_NAME + '.Wakeups')

        data = upower_interface.GetData()
        return data
    
    def get_wakeups_total(self):
        upower_proxy = self.bus.get_object(self.UPOWER_NAME, self.UPOWER_PATH + "/Wakeups") 
        upower_interface = dbus.Interface(upower_proxy, self.UPOWER_NAME + '.Wakeups')

        data = upower_interface.GetTotal()
        return data

    def is_loading(self, battery):
        battery_proxy = self.bus.get_object(self.UPOWER_NAME, battery)
        battery_proxy_interface = dbus.Interface(battery_proxy, self.DBUS_PROPERTIES)
        
        state = int(battery_proxy_interface.Get(self.UPOWER_NAME + ".Device", "State"))

        if (state == 1):
            return True
        else:
            return False

    def get_state(self, battery):
        battery_proxy = self.bus.get_object(self.UPOWER_NAME, battery)
        battery_proxy_interface = dbus.Interface(battery_proxy, self.DBUS_PROPERTIES)
        
        state = int(battery_proxy_interface.Get(self.UPOWER_NAME + ".Device", "State"))

        if (state == 0):
            return "Unknown"
        elif (state == 1):
            return "Loading"
        elif (state == 2):
            return "Discharging"
        elif (state == 3):
            return "Empty"
        elif (state == 4):
            return "Fully charged"
        elif (state == 5):
            return "Pending charge"
        elif (state == 6):
            return "Pending discharge"
        
class batState():
    """Controls battery percentage,state and daemon profiles """


    MIN_BAT_TRIGGER = 30
    MAX_BAT_TRIGGER = 80
    BRIGHT_DEVICE = "/sys/class/backlight/amdgpu_bl0/brightness"
    BRIGHTNESS_BATTERY = "40"
    BRIGHTNESS_AC = "80"

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

    def detect_battery(self):
        upower_proxy = self.bus.get_object(self.UPOWER_NAME, self.UPOWER_PATH) 
        upower_interface = dbus.Interface(upower_proxy, self.UPOWER_NAME)

        devices = upower_interface.EnumerateDevices()
        return devices

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

    def set_brightness(self, brightness: int) -> None:
        try:
            with open(self.BRIGHT_DEVICE,'w') as bd:
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
        # getting current state
        bat_stat.get_powerprofile()
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
        bat_stat.get_percentage()
        bat_stat.get_state()


if __name__ == "__main__":
    watch_battery(time_to_sleep=10)
