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
from homeassistant.helpers.storage import Store

from .const import COORDINATOR, DOMAIN, NAME, PLATFORMS, SENSORS, CONF_USE_ENLIGHTEN, CONF_SERIAL, PHASE_SENSORS, DEFAULT_SCAN_INTERVAL

SCAN_INTERVAL = timedelta(seconds=60)
STORAGE_KEY = "envoy"
STORAGE_VERSION = 1
FETCH_RETRIES = 1
FETCH_TIMEOUT_SECONDS = 30
FETCH_HOLDOFF_SECONDS = 0
COLLECTION_TIMEOUT_SECONDS = 55

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Enphase Envoy from a config entry."""

    config = entry.data
    options = entry.options
    name = config[CONF_NAME]

    # Setup persistent storage, to save tokens between home assistant restarts
    store = Store(hass, STORAGE_VERSION, ".".join([STORAGE_KEY, entry.entry_id]))

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
        https_flag='s' if config.get(CONF_USE_ENLIGHTEN, False) else '',
        store=store,
        fetch_retries=options.get("data_fetch_retry_count", FETCH_RETRIES),
        fetch_timeout_seconds=options.get("data_fetch_timeout_seconds", FETCH_TIMEOUT_SECONDS),
        fetch_holdoff_seconds=options.get("data_fetch_holdoff_seconds", FETCH_HOLDOFF_SECONDS),
        do_not_use_production_json=options.get("do_not_use_production_json",False),
    )
    await envoy_reader._sync_store()

    async def async_update_data():
        """Fetch data from API endpoint."""
        data = {}
        async with async_timeout.timeout(options.get("data_collection_timeout_seconds", COLLECTION_TIMEOUT_SECONDS)):
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

            for description in PHASE_SENSORS:
                if description.key[:-2] in [
                    "none_known_at_this_time_"
                ]:
                    # call phase function for these
                    data[description.key] = await getattr(envoy_reader, description.key[:-3]+"_phase")( description.key[-2:].lower())

                else:
                
                    #catchall for non-specified phase sensors
                    #get attributes for phase sensors based on key name
                    #Removes _L1, _L2 or _L3 from key to call base non-phased function
                    #Pass l1, l2 or l3 as parameter to _phase function
                    data[description.key] = await getattr(envoy_reader, description.key[:-3])( description.key[-2:].lower())
 
                        
            data["grid_status"] = await envoy_reader.grid_status()
            data["envoy_info"] = await envoy_reader.envoy_info()

            _LOGGER.debug("Retrieved data from API: %s", data)

            await envoy_reader._sync_store()
            
            return data

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"envoy {name}",
        update_method=async_update_data,
        update_interval=timedelta(
            seconds=options.get("data_interval", DEFAULT_SCAN_INTERVAL)
        )
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
