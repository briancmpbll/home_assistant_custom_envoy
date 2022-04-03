"""Config flow for Enphase Envoy integration."""
from __future__ import annotations

import contextlib
import logging
from typing import Any

from envoy_reader.envoy_reader import EnvoyReader, SwitchToHTTPS
import httpx
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components import zeroconf
from homeassistant.const import (
    CONF_EMAIL,
    CONF_HOST,
    CONF_ID,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.httpx_client import get_async_client

from .const import (
    COMMISSIONED,
    CONNECTION_TYPE,
    DOMAIN,
    ENLIGHTEN_PASSWORD,
    HTTPS_FLAG,
    UNCOMMISSIONED,
)

_LOGGER = logging.getLogger(__name__)

ENVOY = "Envoy"

CONF_SERIAL = "serial"


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> EnvoyReader:
    """Validate the user input allows us to connect."""
    envoy_reader = EnvoyReader(
        data[CONF_HOST],
        data[CONF_USERNAME],
        data[CONF_PASSWORD],
        inverters=False,
        async_client=get_async_client(hass),
    )

    try:
        await envoy_reader.check_connection()
    except SwitchToHTTPS as err:
        raise EnlightenAuthError from err

    try:
        await envoy_reader.getData()
    except httpx.HTTPStatusError as err:
        raise InvalidAuth from err
    except (RuntimeError, httpx.HTTPError) as err:
        raise CannotConnect from err

    return envoy_reader


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Enphase Envoy."""

    VERSION = 1

    def __init__(self):
        """Initialize an envoy flow."""
        self.ip_address = None
        self.username = None
        self._reauth_entry = None
        self.data = None

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
        serial = discovery_info.properties["serialnum"]
        await self.async_set_unique_id(serial)
        self.ip_address = discovery_info.host
        self._abort_if_unique_id_configured({CONF_HOST: self.ip_address})
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
            except EnlightenAuthError:
                self.data = user_input.copy()
                self.data[CONF_NAME] = self._async_envoy_name()
                _LOGGER.debug("DataA: %s", self.data)
                return await self.async_step_enlighten()
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                self.data = user_input.copy()
                self.data[CONF_NAME] = self._async_envoy_name()
                self.data[CONF_EMAIL] = None
                self.data[ENLIGHTEN_PASSWORD] = None
                self.data[CONNECTION_TYPE] = None
                self.data[CONF_ID] = None
                self.data[CONF_SERIAL] = None
                self.data[HTTPS_FLAG] = ""

                if self._reauth_entry:
                    self.hass.config_entries.async_update_entry(
                        self._reauth_entry,
                        data=self.data,
                    )
                    return self.async_abort(reason="reauth_successful")

                if not self.unique_id and await self._async_set_unique_id_from_envoy(
                    envoy_reader
                ):
                    self.data[CONF_NAME] = self._async_envoy_name()

                if self.unique_id:
                    self._abort_if_unique_id_configured(
                        {CONF_HOST: self.data[CONF_HOST]}
                    )

                return self.async_create_entry(
                    title=self.data[CONF_NAME], data=self.data
                )

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

    async def async_step_enlighten(self, user_input=None):
        """Handle the Enlighten step."""
        data_schema = vol.Schema(
            {
                vol.Required(CONF_EMAIL): str,
                vol.Required(ENLIGHTEN_PASSWORD): str,
                vol.Required(CONNECTION_TYPE, default=COMMISSIONED): vol.In(
                    (
                        COMMISSIONED,
                        UNCOMMISSIONED,
                    )
                ),
            }
        )
        _LOGGER.debug("Input: %s", user_input)
        if user_input is None:
            return self.async_show_form(
                step_id="enlighten",
                data_schema=data_schema,
            )

        self.data[CONF_EMAIL] = user_input[CONF_EMAIL]
        self.data[ENLIGHTEN_PASSWORD] = user_input[ENLIGHTEN_PASSWORD]
        self.data[CONNECTION_TYPE] = user_input[CONNECTION_TYPE]
        self.data[HTTPS_FLAG] = "s"

        if user_input[CONNECTION_TYPE] == COMMISSIONED:
            return await self.async_step_commissioned()

        self.data[CONF_ID] = None
        self.data[CONF_SERIAL] = None
        _LOGGER.debug("Uncommissioned data: %s", self.data)
        return self.async_create_entry(title=self.data[CONF_NAME], data=self.data)

    async def async_step_commissioned(self, user_input=None):
        """Handle the Commissioned step."""
        data_schema = vol.Schema(
            {
                vol.Required(CONF_ID): str,
                vol.Required(CONF_SERIAL): str,
            }
        )
        if user_input is None:
            return self.async_show_form(step_id="commissioned", data_schema=data_schema)

        self.data[CONF_ID] = user_input[CONF_ID]
        self.data[CONF_SERIAL] = user_input[CONF_SERIAL]
        _LOGGER.debug("Commissioned data: %s", self.data)
        return self.async_create_entry(title=self.data[CONF_NAME], data=self.data)


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


class EnlightenAuthError(HomeAssistantError):
    """Error to indicate additional user credentials are needed."""
