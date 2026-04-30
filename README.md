# klipper-search-probe-plugin
A plugin in klipper to attach zeroclick or klicky without homing, this is very useful for a bed slinger like Ender 3.

Put it under `~/klipper/klippy/extra`, and update your printer.cfg like this
```
[gcode_macro ATTACH_PROBE]
description: Grab probe and IMMEDIATELY home Z to reset status
gcode:
    # 1. Homing/Clearance
    {% if "xy" not in printer.toolhead.homed_axes %}
        G28 X Y
    {% else %}
        FORCE_MOVE STEPPER=stepper_z DISTANCE=25 VELOCITY=5
    {% endif %}
    # 2. Run the Plugin
    ATTACH_PROBE_SEARCH
    # 3. THE RESET: Move to bed center and Home Z
    # This "overwrites" the fake Z with real data
    # Nozzle X138 Y95 = Probe at bed center
    G90
    G1 X138 Y95 F6000
    G28.1 Z             # Use the raw G28 to avoid macro loops
    G1 Z30 F900         # Safe lift
    M117 Probe Attached
```

Then restart klipper
```
sudo service klipper restart
```
