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
