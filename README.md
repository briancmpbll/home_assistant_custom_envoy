This is a HACS custom integration for enphase envoys with firmware version 7.X. All credit for the actual code fixes goes to [@gtdiehl](https://github.com/gtdiehl), I just packaged it up to work with HACS so that HASS OS users can install it. His code is located [here](https://github.com/gtdiehl/core/tree/envoy_new_fw/homeassistant/components/enphase_envoy). See the discussion on [this issue](https://github.com/jesserizzo/envoy_reader/issues/78) for more context.

# Installation

1. Install [HACS](https://hacs.xyz/) if you haven't already
2. Add this repository as a [custom repository](https://hacs.xyz/docs/faq/custom_repositories) in HACS
3. Add an entry in your configuration.yml:
   ```yml
   enphase_envoy_custom:
     host: your_envoy_ip_here
   ```
4. Restart home assistant
5. Home assistant should automatically discover the integration and you can follow the [documentation](https://www.home-assistant.io/integrations/enphase_envoy/) for the official integration
