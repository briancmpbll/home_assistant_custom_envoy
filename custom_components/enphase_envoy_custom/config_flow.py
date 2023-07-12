"""Config flow for Enphase Envoy integration."""
from __future__ import annotations

import contextlib
import logging
from typing import Any

from .envoy_reader import EnvoyReader
import httpx
import ipaddress
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components import zeroconf
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN, CONF_SERIAL, CONF_USE_ENLIGHTEN

_LOGGER = logging.getLogger(__name__)

ENVOY = "Envoy"


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> EnvoyReader:
    """Validate the user input allows us to connect."""
    envoy_reader = EnvoyReader(
        data[CONF_HOST],
        username=data[CONF_USERNAME],
        password=data[CONF_PASSWORD],
        enlighten_user=data[CONF_USERNAME],
        enlighten_pass=data[CONF_PASSWORD],
        inverters=False,
#        async_client=get_async_client(hass),
        use_enlighten_owner_token=data.get(CONF_USE_ENLIGHTEN, False),
        enlighten_serial_num=data[CONF_SERIAL],
        https_flag='s' if data.get(CONF_USE_ENLIGHTEN,False) else ''
    )

    try:
        await envoy_reader.getData()
    except httpx.HTTPStatusError as err:
        raise InvalidAuth from err
    except (RuntimeError, httpx.HTTPError) as err:
        raise CannotConnect from err

    return envoy_reader

def _is_ipv4(address):
    try:
        ip = ipaddress.ip_address(address)
        return isinstance(ip, ipaddress.IPv4Address)
    except ValueError:
        _LOGGER.error("%s is an invalid IP address", address)
        return False

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Enphase Envoy."""

    VERSION = 1

    def __init__(self):
        """Initialize an envoy flow."""
        self.ip_address = None
        self.username = None
        self._reauth_entry = None

    @callback
    def _async_generate_schema(self):
        """Generate schema."""
        schema = {}

        if self.ip_address:
            schema[vol.Required(CONF_HOST, default=self.ip_address)] = vol.In(
                [self.ip_address]
            )
        else:
            schema[vol.Required(CONF_HOST)] = str

        schema[vol.Optional(CONF_USERNAME, default=self.username or "envoy")] = str
        schema[vol.Optional(CONF_PASSWORD, default="")] = str
        schema[vol.Optional(CONF_SERIAL, default=self.unique_id)] = str
        schema[vol.Optional(CONF_USE_ENLIGHTEN)] = bool
        return vol.Schema(schema)

    @callback
    def _async_current_hosts(self):
        """Return a set of hosts."""
        return {
            entry.data[CONF_HOST]
            for entry in self._async_current_entries(include_ignore=False)
            if CONF_HOST in entry.data
        }

    async def async_step_zeroconf(
        self, discovery_info: zeroconf.ZeroconfServiceInfo
    ) -> FlowResult:
        """Handle a flow initialized by zeroconf discovery."""
        self.ip_address = discovery_info.host
        if not _is_ipv4(self.ip_address):
            return self.async_abort(reason="ipv6_not_supported")
        
        serial = discovery_info.properties["serialnum"]
        await self.async_set_unique_id(serial)

        # autodiscovery is updating the ip address of an existing envoy with matching serial to new detected ip adress
        self._abort_if_unique_id_configured()
        for entry in self._async_current_entries(include_ignore=False):
            if (
                entry.unique_id is None
                and CONF_HOST in entry.data
                and entry.data[CONF_HOST] == self.ip_address
            ):
                title = f"{ENVOY} {serial}" if entry.title == ENVOY else ENVOY
                self.hass.config_entries.async_update_entry(
                    entry, title=title, unique_id=serial
                )
                self.hass.async_create_task(
                    self.hass.config_entries.async_reload(entry.entry_id)
                )
                return self.async_abort(reason="already_configured")

        return await self.async_step_user()

    async def async_step_reauth(self, user_input):
        """Handle configuration by re-auth."""
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        return await self.async_step_user()

    def _async_envoy_name(self) -> str:
        """Return the name of the envoy."""
        if self.unique_id:
            return f"{ENVOY} {self.unique_id}"
        return ENVOY

    async def _async_set_unique_id_from_envoy(self, envoy_reader: EnvoyReader) -> bool:
        """Set the unique id by fetching it from the envoy."""
        serial = None
        with contextlib.suppress(httpx.HTTPError):
            serial = await envoy_reader.get_full_serial_number()
        if serial:
            await self.async_set_unique_id(serial)
            return True
        return False

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            if (
                not self._reauth_entry
                and user_input[CONF_HOST] in self._async_current_hosts()
            ):
                return self.async_abort(reason="already_configured")
            try:
                envoy_reader = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                data = user_input.copy()
                data[CONF_NAME] = self._async_envoy_name()

                if self._reauth_entry:
                    self.hass.config_entries.async_update_entry(
                        self._reauth_entry,
                        data=data,
                    )
                    return self.async_abort(reason="reauth_successful")

                if not self.unique_id and await self._async_set_unique_id_from_envoy(
                    envoy_reader
                ):
                    data[CONF_NAME] = self._async_envoy_name()

                if self.unique_id:
                    self._abort_if_unique_id_configured({CONF_HOST: data[CONF_HOST]})

                return self.async_create_entry(title=data[CONF_NAME], data=data)

        if self.unique_id:
            self.context["title_placeholders"] = {
                CONF_SERIAL: self.unique_id,
                CONF_HOST: self.ip_address,
            }
        return self.async_show_form(
            step_id="user",
            data_schema=self._async_generate_schema(),
            errors=errors,
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
