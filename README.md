This is a HACS custom integration for enphase envoys with firmware version 7.X. This integration is based off work done by @DanBeard, with some changes to report individual battery status.

# Installation

1. Install [HACS](https://hacs.xyz/) if you haven't already
2. Add this repository as a [custom integration repository](https://hacs.xyz/docs/faq/custom_repositories) in HACS
4. Restart home assistant
5. Add the integration through the home assistant configuration flow. Look for "Enphase Envoy (DEV)" .
6. Click "Use Englighten" and use your enlighten username and password in the fields
6. Add integral sensors if you want to use the energy dashboard. This is nessesary because Homeassistant wants the dashboard import/export sensors to *not* count energy you instantly produced and used yourself. Therefore, we need to integrate the power sensor Envoy provides. I wish they changed this! XXXXXX is your serial number:
```
sensor:
  - platform: integration
    source: sensor.envoy_XXXXXX_current_grid_export_power
    name: envoy_XXXXXX_grid_export_energy
    unit_prefix: k
    round: 2
  - platform: integration
    source: sensor.envoy_XXXXXX_current_grid_import_power
    name: envoy_XXXXXX_grid_import_energy
    unit_prefix: k
    round: 2
```


[<img width="545" alt="bmc-button" src="https://user-images.githubusercontent.com/1570176/180045360-d3f479c5-ad84-4483-b2b0-83820b1a8c63.png">](https://buymeacoffee.com/briancmpblL)
