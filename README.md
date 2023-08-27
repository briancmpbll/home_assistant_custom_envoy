[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration#readme)

This is a HACS custom integration for [enphase envoys/IQ Gateways](https://enphase.com/en-us/products-and-services/envoy-and-combiner) with firmware version 7.X. This integration is based off work done by @jesserizzo, @gtdiehl and @DanBeard, with some changes to report individual battery status. 

It still supports Envoys with firmware versions before 7.x including R3 versions for legacy models.

Works with older models that only have (some) production metrics (ie. Envoy-C R or LCD), newer models with only production metrics (IQ Gateway / ENVOY-S Standard) and models that offer both production and consumption metrics (ie. Envoy-S metered).

# Installation

1. Install [HACS](https://hacs.xyz/) if you haven't already
2. Add this repository as a [custom integration repository](https://hacs.xyz/docs/faq/custom_repositories) in HACS
4. Restart home assistant
5. Add the integration through the home assistant configuration flow

# Usage

## Initial Configuration details

The initial configuration window requires you to enter the details how to access the Envoy. Following fields have to be filled.

### Host

Enter the IP address of the Envoy. If the Envoy is auto-discovered it will be pre-filled. The IP address may be an ipv4 or ipv6 address.

### Username and Password

Specify the username and password to access the envoy data. What username and password to use depends on the ENVOY type and/or it's firmware version:

- If your IQ Gateway / Envoy-S is on Firmware 7.x or later, use your Enphase Enlighten username and password. Make sure to enable the 'Use Enlighten' option at the bottom of the form.

- For older models and ENVOY-S with firmware before 7.x use `envoy` without a password, `installer` without a password or a valid username and password for the type.

- For older models that require username `installer` with a password, this can be obtained with this: [tool](https://thecomputerperson.wordpress.com/2016/08/28/reverse-engineering-the-enphase-installer-toolkit/).
- In some cases, you need to use the username `envoy` with the last 6 digits of the unit's serial number as password.

See [the Enphase documentation](https://support.enphase.com/s/article/What-is-the-Username-and-Password-for-the-Administration-page-of-the-Envoy-local-interface) for more details on various units.

**Note** This integration does not provide the additional data accessible by Enphase Installer or DIY accounts, only data accessible by Home owner accounts is provided. Using an Installer or DIY account may or may not work work, but currently just the Home owner data is retrieved.

## Serial number

Specify the Envoy serial number. If the Envoy is auto-discovered it will be pre-filled.

### Use Enlighten

Enable this option with IQ Gateway/ENVOY-S Firmware 7.x or later that require Enphase tokens for authentication. It will use the username and password to retrieve the authentication token from the Enphase website, cache it and use it to access the Envoy.

## Runtime configuration

Once the Envoy has been running and is operational, the following configuration items are available:

### Scan Interval - Time between Entity updates

By default the Envoy data is collected every 60 seconds. One can change the setting to what is desired with a minimum of every 5 seconds. Upon changing the value, reload the integration (or restart Home Assistant).

What the optimal scan frequency is depends on the Envoy model. Models without meters typically update the inverter data every 5 minutes. Models using meters update measurements way more frequent, probably every second or so. Hence the default of 60 seconds as starting point. Some models may have capacity issues running at high refresh rates, so no single recipe is available.

**Note** Envoy Metered has a data streaming option to bring in data as it comes available which is not currently supported by this integration.

### Timeout for single Envoy Page
Specifies the timeout for each single data get to the Envoy. Defaults to 30 seconds. Shortening this time does not make the Envoy response faster, lengthening it will allow a slow Envoy more time to respond before time-out occurs.

### How many retries in getting an Envoy response
Specifies how many times a retry should be attempted after the first one failed. Must be at least 1 to allow for automatic token updates. Typically do not change this setting. Increasing may help in  poor network conditions.

### Time between 2 retries
Optionally a wait time can be inserted between 2 retries. Only change this in special circumstances.

### Overall Timeout
When getting data from the Envoy, an overall timer is started. If not all data is returned when the timer expires, the data collection is considered timed-out and all data is set to unavailable. Intent is catch all if data collection is never returning. Do not change this setting, unless Timeout for single envoy page or number of retries needs to be increased. In that case increase this overall timer value as well to prevent it to timeout the data collection. To get a feel for needed time, enable the debug mode on the envoy and inspect timing of a full collection cycle.

# Firmware and it's impact

Enphase model offering differs in various countries as does firmware versions and releases. Not all firmware is released in all countries and as a result firmware versions may differ largely in time. Enphase does push new firmware to the IQ Gateway / Envoy, 'not necessarily letting the home owner know'. In the past this has broken this integration as API details and change information is limited available. See the [Enphase documentation website](https://enphase.com/installers/resources/documentation/communication) for information available.

# Different models have different features

This integration supports various models but as models have different features they will not all provide the same data. Brief list of reported data below.

## ENVOY C / R / LCD

- Current power production, today's, last 7 days and lifetime energy production.

## IQ Gateway / ENVOY S standard (non metered)

- Current power production, today's, last 7 days and lifetime energy production.
- Current power production for each connected inverter.

## IQ Gateway / ENVOY S standard metered

What data is available depends on how many current transformer clamps (CT) are installed and what currents they measure. Both production and consumption clamps can be installed, each for up to 3 phases or multiple circuits on their own breaker in single phase setup.

### with connected current transformer clamps

- Current power production and consumption, today's, last 7 days and lifetime energy production and consumption over all phases.
- Current power production and consumption, today's, last 7 days and lifetime energy production and consumption for each individual phase named L1, L2 and L3.
- Current power production for each connected inverter.

**Note** If you have CT clamps on a single phase / breaker circuit only, the L1 production and consumption phase sensors will show same data as the over all phases sensors.

### without connected current transformer clamps

The current firmware (D7.6.175 and probably some other right before and after it) without CT clamps connected and configured does obviously not report these measurements. But for some reason it is only reporting:

- Current power production and lifetime energy production. Today's and last 7 day energy production reportedly are both solid 0.
- Lifetime Energy production reportedly resets to zero roughly every 1.19 MWh.
- Current power production for each connected inverter.

# Device and Entities

The naming scheme used is based on the Envoy and inverter Serial numbers.

## Device

A device `Envoy <serialnumber>` is created with sensor entities for accessible data.

## Envoy Sensors

|Sensor name|Sensor ID|Units|remarks|
|-----|-----|----|----|
|Envoy \<sn\> Current Power Production|sensor.Envoy_\<sn\>_current_power_production|W||
|Envoy \<sn\> Today's Energy production|sensor.Envoy_\<sn\>_todays_energy_production|Wh|1|
|Envoy \<sn\> Last Seven Days Energy Production|sensor.Envoy_\<sn\>_last_seven_days_energy_production|Wh|1|
|Envoy \<sn\> Lifetime Energy Production|sensor.Envoy_\<sn\>_lifetime_energy_production|Wh|2|
|Envoy \<sn\> Current Power Consumption|sensor.Envoy_\<sn\>_current_power_consumption|W||
|Envoy \<sn\> Today's Energy Consumption|sensor.Envoy_\<sn\>_todays_energy_consumption|Wh|4,5|
|Envoy \<sn\> Last Seven Days Energy Consumption|sensor.Envoy_\<sn\>_last_seven_days_energy_consumption|Wh|4,5|
|Envoy \<sn\> Lifetime Energy Consumption|sensor.Envoy_\<sn\>_lifetime_energy_consumption|Wh|4,5|
|Grid Status |binary_sensor.grid_status|On/Off|3|
Envoy \<sn\> Current Power Production L\<n\>|sensor.Envoy_\<sn\>_current_power_production_L\<n\>|W|4,5|
|Envoy \<sn\> Today's Energy production L\<n\>|sensor.Envoy_\<sn\>_todays_energy_production_L\<n\>|Wh|4,5|
|Envoy \<sn\> Last Seven Days Energy Production L\<n\>|sensor.Envoy_\<sn\>_last_seven_days_energy_production L\<n\>|Wh|4,5|
|Envoy \<sn\> Lifetime Energy Production L\<n\>|sensor.Envoy_\<sn\>_lifetime_energy_consumption_L\<n\>|Wh|4,5|
|Envoy \<sn\> Current Power Consumption L\<n\>|sensor.Envoy_\<sn\>_current_power_consumption_L\<n\>|W|4,5|
|Envoy \<sn\> Today's Energy Consumption L\<n\>|sensor.Envoy_\<sn\>_todays_energy_consumption_L\<n\>|Wh|4,5,6|
|Envoy \<sn\> Last Seven Days Energy Consumption L\<n\>|sensor.Envoy_\<sn\>_last_seven_days_energy_consumption L\<n\>|Wh|4,5,6|
|Envoy \<sn\> Lifetime Energy Consumption L\<n\>|sensor.Envoy_\<sn\>_lifetime_energy_consumption_L\<n\>|Wh|4,5,6|

1 Always zero for Envoy Metered without meters.  
2 Reportedly resets to zero when reaching ~1.92MWh for Envoy Metered without meters.  
3 Not available on Legacy models and ENVOY Standard with recent firmware.  
4 Only on Envoy metered with configured and connected meters.  
5 L\<n\> L1,L2,L3, availability depends on which and how many meters are connected and configured.  
6 Reportedly always zero on Envoy metered with Firmware D8.

## Inverter Sensors

For each inverter a sensor for current power production is created.

|Sensor name|Sensor ID|UNits|remarks|
|-----|-----|----|----|
|Envoy \<sn\> Inverter \<sn\>|sensor.Envoy_\<sn\>\_Inverter_\<sn\>|W|1|

1: Not available on Legacy models

**Note** the entity 'Last Updated' for each inverter is currently not provided. 

**Note** As can be noted the Envoy serial number is part of the inverter sensor id and name. Internally the unique_id for it is the inverter serial number. When changing your setup by moving inverters to a new/different Envoy it will require some preparation/research how this will work out. (Statistics (history) is stored by sensor id)

## Battery Sensors

For each battery a sensor for percent full is created as well as sensors for overall battery percentage, overall battery capacity, overall energy charged and discharged are created.

|Sensor name|Sensor ID|Units|remarks|
|-----|-----|----|----|
|Envoy \<sn\> Battery \<sn\>|sensor.Envoy_\<sn\>\_Battery_\<sn\>|%|1|
|Envoy \<sn\> Total Battery Percentage|sensor.Envoy_\<sn\>\_total_battery_percentage|%|1|
|Envoy \<sn\> Current Battery Capacity|sensor.Envoy_\<sn\>\_current_battery_capacity|Wh|1|
|Envoy \<sn\> Battery Energy Charged|sensor.Envoy_\<sn\>\_battery_energy_charged|Wh|1|
|Envoy \<sn\> Battery Energy Discharged|sensor.Envoy_\<sn\>\_battery_energy_charged|Wh|1|

1: Not available on Legacy models and ENVOYS-S Standard

# How to switch to Enphase token authorization

Once the envoy received the new firmware that requires token authorization, data collection will fail. To switch to the token usage execute next steps:

- [Install](#installation) the Custom integration using HACS
- In Home Assistant go to the Enphase Envoy integration and delete it.
- Restart Home Assistant
- The envoy will be auto-discovered again. If not add an Envoy Integration manually.
- In the configuration screen now use your Enphase Enlighten username and password and enable the 'Use Enlighten' option.
- Once it's configured it will continue reporting data in the same entities.
- Optionally change the default time interval from 60 to what is preferred.

# Troubleshooting

When issues occur with this integration some items to check are:

- Use the `Download Diagnostics` button in the Envoy Device page or the Enphase Integration page menu. It will download settings and recent data of the Envoy and provide some key information.
- What model are you using. This will drive what can be expected.
- What firmware is your model using, Was a firmware update recently pushed to the device?
- Enable debug logging and let it run for a couple of minutes, disable it again and the log file will download. Check for obvious errors and be prepared to share it as needed for troubleshooting. Any tokens, usernames or passwords for the Envoy integration are not visible, but there may be sensitive information of other integrations that are being used.
  - All data collected is logged in lines like `Fetched from https://192.168.01.10/some_url: <Response [200 OK]>:`. Inspecting these provides insight in what and how successful data is collected.
  - The Envoy model it thinks its dealing with is reported in a line containing: `Using Model: P (HTTPs, Metering enabled: False, Get Inverters: True)`. (Model PC is envoy metered, P is Standard and R/LCD with FW >= R3.9 and P0 is Legacy/C/R/LCD with FW < R3.9>)
- When configuring the Envoy for token use it will reach out to the Enphase Enlighten website to obtain a token. Reportedly the Enphase website is not equally responsive every moment of the day, week, moth, year and the setup will fail. At this moment the only answer to that is your perseverance or just try at another moment.
- The token lifetime for Home Owner accounts is currently 1 year. The token is cached, eliminating the need to connect to Enphase each reload or restart. When the token is expired or some other authorization hiccup occurs a new token will be obtained. If that is needed at a moment it can't connect to Enphase it will try until success but in the mean time no data is collected from the Envoy. When using an Installer or DIY account this may work as well but the lifetime is 12 hours and refresh is way more frequent.
- The Envoy integration supports zeroconf for auto detection and changes of IP addresses for the Envoy. It will not switch to an IPV6 address if the default network interface is running ipv4 or the other way around.It supports both IPV4 and IPV6. To change between these when default interface change IP type, remove and re-add the Envoy.
- When an error is reported during the initial configuration, inspect the home-assistant.log file in the /config folder. It will reveal what happened:
  - Validate input, getdata returned RuntimeError: Could not Authenticate with Enlighten, status: 401, <Response [401 Unauthorized]> : Check if Enphase username and/or password are correct
  - Validate input, getdata returned RuntimeError: Could not get enlighten token, status: 403, <Response [403 Forbidden]>  : Make sure envoy serialnumber is correct and connected to your Enphase account
  - Validate input, getdata returned HTTPError: All connection attempts failed  : failure to connect to envoy.  : Validate if correct IP address of the Envoy is used
  - Fetched (1 of 2) in 0.0 sec from http://x.x.x.x/production.json?details=1: <Response [301 Moved Permanently]>: <html>  : Was 'use Enlighten' checked when using tokens or validate username/pw used for legacy devices.