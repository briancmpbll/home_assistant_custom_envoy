This is a HACS custom integration for enphase envoys with firmware version 7.X. This integration is based off work done by @DanBeard, with some changes to report individual battery status.

# Installation

1. Install [HACS](https://hacs.xyz/) if you haven't already
2. Add this repository as a [custom integration repository](https://hacs.xyz/docs/faq/custom_repositories) in HACS
4. Restart home assistant
5. Add the integration through the home assistant configuration flow

[<img width="545" alt="bmc-button" src="https://user-images.githubusercontent.com/1570176/180045360-d3f479c5-ad84-4483-b2b0-83820b1a8c63.png">](https://buymeacoffee.com/briancmpblL)



# Usage
  - Username / Password / Use Enlighten [#73](https://github.com/briancmpbll/home_assistant_custom_envoy/issues/73)\
      When configuring the Envoy with firmware 7 or higher specify your Enphase Enlighten username and password, the envoy serial number and check the 'Use Enlighten' box at the bottom. This will allow the integration to collect a token from the enphase website and use it to access the Envoy locally. It does this at first configuration, at each HA startup or at reload of the integration. The Enphase web-site is known to be slow or satured at times. When an *Unknown Error* is reported during configuration try again until success. [#81](https://github.com/briancmpbll/home_assistant_custom_envoy/issues/81) \
      \
      Upon changing your password on the Enphase web site you will have to update the password information in HA. To update it, delete the envoy integration from the Settings / Integrations window. Restart HA and then in Integrations window configure it again. All data is kept and will show again once it's configured.