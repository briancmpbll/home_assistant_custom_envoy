"""The Enphase Envoy integration."""
from __future__ import annotations

from datetime import timedelta
import logging

import async_timeout
from .envoy_reader import EnvoyReader
import httpx
from numpy import isin

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import COORDINATOR, DOMAIN, NAME, PLATFORMS, SENSORS, CONF_USE_ENLIGHTEN, CONF_SERIAL

SCAN_INTERVAL = timedelta(seconds=60)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Enphase Envoy from a config entry."""

    config = entry.data
    name = config[CONF_NAME]

    envoy_reader = EnvoyReader(
        config[CONF_HOST],
        username=config[CONF_USERNAME],
        password=config[CONF_PASSWORD],
        enlighten_user=config[CONF_USERNAME],
        enlighten_pass=config[CONF_PASSWORD],
        inverters=True,
#        async_client=get_async_client(hass),
        use_enlighten_owner_token=config.get(CONF_USE_ENLIGHTEN, False),
        enlighten_serial_num=config[CONF_SERIAL],
        https_flag='s' if config.get(CONF_USE_ENLIGHTEN, False) else ''
    )

    async def async_update_data():
        """Fetch data from API endpoint."""
        data = {}
        async with async_timeout.timeout(30):
            try:
                await envoy_reader.getData()
            except httpx.HTTPStatusError as err:
                raise ConfigEntryAuthFailed from err
            except httpx.HTTPError as err:
                raise UpdateFailed(f"Error communicating with API: {err}") from err

            for description in SENSORS:
                if description.key == "inverters":
                    data[
                        "inverters_production"
                    ] = await envoy_reader.inverters_production()

                elif description.key == "batteries":
                    battery_data = await envoy_reader.battery_storage()
                    if isinstance(battery_data, list) and len(battery_data) > 0:
                        battery_dict = {}
                        for item in battery_data:
                            battery_dict[item["serial_num"]] = item

                        data[description.key] = battery_dict

                elif (description.key not in ["current_battery_capacity", "total_battery_percentage"]):
                    data[description.key] = await getattr(
                        envoy_reader, description.key
                    )()

            data["grid_status"] = await envoy_reader.grid_status()
            data["charge"] = await envoy_reader.charge()
            data["discharge"] = await envoy_reader.discharge()

            _LOGGER.debug("Retrieved data from API: %s", data)

            return data

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"envoy {name}",
        update_method=async_update_data,
        update_interval=SCAN_INTERVAL,
    )

    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryAuthFailed:
        envoy_reader.get_inverters = False
        await coordinator.async_config_entry_first_refresh()

    if not entry.unique_id:
        try:
            serial = await envoy_reader.get_full_serial_number()
        except httpx.HTTPError:
            pass
        else:
            hass.config_entries.async_update_entry(entry, unique_id=serial)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        COORDINATOR: coordinator,
        NAME: name,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
