# watch battery

A python script to control power state with power-profiles-daemon and
screen brightness. Morehover sends notifications when battery stands below and over fixed
values.
### Python requirements
python-dbus

### System requirements
1. User must be in video group (or what you want group) in order to write in special file
2. Write a /etc/udev/rules.d/90-backlight.rules with:
> SUBSYSTEM=="backlight", ACTION=="add", \
  RUN+="/bin/chgrp video /sys/class/backlight/%k/brightness", \
  RUN+="/bin/chmod g+w /sys/class/backlight/%k/brightness"

3. Change the line in the script:
3.1. BRIGHT_DEVICE = "/sys/class/backlight/amdgpu_bl0/brightness" with your own device
4. power-profiles-daemon installed and configured
5. Run it from your desktop session launcher.