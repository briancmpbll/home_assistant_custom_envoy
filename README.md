This is a HACS custom integration for enphase envoys with firmware version 7.X. This integration is based off work done by @DanBeard, with some changes to report individual battery status.

# Installation

1. Install [HACS](https://hacs.xyz/) if you haven't already
2. Add this repository as a [custom integration repository](https://hacs.xyz/docs/faq/custom_repositories) in HACS
4. Restart home assistant
5. Add the integration through the home assistant configuration flow

# Notes

* It may still require a few logon attempts when enabling the integration to get a valid token - there is an issue with the Enphase authentication services
* Systems that have an Enpower Smart Switch (ATS), the grid up\down status is not yet presented to HA; there is a bug in the current mass-distributed Envoy firmwares that cause the envoy to reboot when there is a grid transition event
* There is a good bit more battery data available, but it will take some work to figure out what the data we get from Envoy means (for example, the different led_status values) as this information is not publicly available from Enphase
* If you have Encharge battery storage, **the values reported for home consumption will include battery charge\discharge power due to the location of the consumption CTs, not home loads by themselves** - Envoy reads data from the IQ8X-BAT micros to gather actual battery charge\discharge information, we are not yet able to access this data via local API. A workaround for this would be to put a separate set of CTs on your Main Load Panel (zwave HEM for example) to gather actual load values and calculate the difference for battery charge\discharge

[<img width="545" alt="bmc-button" src="https://user-images.githubusercontent.com/1570176/180045360-d3f479c5-ad84-4483-b2b0-83820b1a8c63.png">](https://buymeacoffee.com/briancmpblL)
