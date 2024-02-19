"""Module to read production and consumption values from an Enphase Envoy on the local network."""
import argparse
import datetime
import logging
import time
from json.decoder import JSONDecodeError
import json
from ipaddress import IPv4Address, IPv6Address
import sys
import getpass

#Modules not in standard Python Library - add to manifest requirements
import re
import jwt
import asyncio
import httpx
import xmltodict
from envoy_utils.envoy_utils import EnvoyUtils

#
# Legacy parser is only used on ancient firmwares
#
PRODUCTION_REGEX = r"<td>Currentl.*</td>\s+<td>\s*(\d+|\d+\.\d+)\s*(W|kW|MW)</td>"
DAY_PRODUCTION_REGEX = r"<td>Today</td>\s+<td>\s*(\d+|\d+\.\d+)\s*(Wh|kWh|MWh)</td>"
WEEK_PRODUCTION_REGEX = (
    r"<td>Past Week</td>\s+<td>\s*(\d+|\d+\.\d+)\s*(Wh|kWh|MWh)</td>"
)
LIFE_PRODUCTION_REGEX = (
    r"<td>Since Installation</td>\s+<td>\s*(\d+|\d+\.\d+)\s*(Wh|kWh|MWh)</td>"
)
SERIAL_REGEX = re.compile(r"Envoy\s*Serial\s*Number:\s*([0-9]+)")
ACTIVE_INVERTER_COUNT_REGEX = r"<td>Number of Microinverters Online</td>\s*<td>\s*(\d*)\s*</td>"

ENDPOINT_URL_PRODUCTION_JSON = "http{}://{}/production.json?details=1"
ENDPOINT_URL_PRODUCTION_V1 = "http{}://{}/api/v1/production"
ENDPOINT_URL_PRODUCTION_INVERTERS = "http{}://{}/api/v1/production/inverters"
ENDPOINT_URL_PRODUCTION = "http{}://{}/production"
ENDPOINT_URL_CHECK_JWT = "https://{}/auth/check_jwt"
ENDPOINT_URL_ENSEMBLE_INVENTORY = "http{}://{}/ivp/ensemble/inventory"
ENDPOINT_URL_HOME_JSON = "http{}://{}/home.json"
ENDPOINT_URL_HOME = "http{}://{}/home"
ENDPOINT_URL_INFO_XML = "http{}://{}/info"
ENDPOINT_URL_METERS = "http{}://{}/ivp/meters"
ENDPOINT_URL_METERS_REPORTS = "http{}://{}/ivp/meters/reports"
ENDPOINT_URL_METERS_READINGS = "http{}://{}/ivp/meters/readings"

# pylint: disable=pointless-string-statement

ENVOY_MODEL_S = "PC"
ENVOY_MODEL_C = "P"
ENVOY_MODEL_LEGACY = "P0"

LOGIN_URL = "https://entrez.enphaseenergy.com/login_main_page"
TOKEN_URL = "https://entrez.enphaseenergy.com/entrez_tokens"

# paths for the enlighten 1 year owner token
ENLIGHTEN_AUTH_URL = "https://enlighten.enphaseenergy.com/login/login.json"
ENLIGHTEN_TOKEN_URL = "https://entrez.enphaseenergy.com/tokens"

_LOGGER = logging.getLogger(__name__)


def has_production_and_consumption(json):
    """Check if json has keys for both production and consumption."""
    return "production" in json and "consumption" in json


def has_metering_setup(json):
    """Check if Active Count of Production CTs (eim) installed is greater than one."""
    return json["production"][1]["activeCount"] > 0


def has_production_metering_setup(json):
    """Check if Production CTs (eim) are installed."""
    return json[0]["state"] == "enabled"


def has_consumption_metering_setup(json):
    """Check if Consumption CTs (eim) are installed."""
    return json[1]["state"] == "enabled"


def has_net_consumption_meters_type(json):
    """Check if Consumption measurement type is net-consumption."""
    return json[1]["measurementType"] == "net-consumption"


def get_production_meters_phase_count(json):
    """Get Count of Production CTs (eim) installed."""
    return json[0]["phaseCount"]


def get_consumption_meters_phase_count(json):
    """Get Count of Consumption CTs (eim) installed."""
    return json[1]["phaseCount"]

    
def is_ipv6_address(address: str) -> bool:
    """Check if a given string is an IPv6 address."""
    try:
        IPv6Address(address)
    except ValueError:
        return False
    return True

class SwitchToHTTPS(Exception):
    pass


class EnvoyReader:  # pylint: disable=too-many-instance-attributes
    """Instance of EnvoyReader"""

    # P0 for older Envoy model C, s/w < R3.9 no json pages
    # P for production data only (ie. Envoy model C, s/w >= R3.9)
    # PC for production and consumption data (ie. Envoy model S)

    message_battery_not_available = (
        "Battery storage data not available for your Envoy device."
    )

    message_production_not_available = (
        "CTs production data not available for your Envoy device."
    )

    message_consumption_not_available = (
        "CTs consumption data not available for your Envoy device."
    )

    message_grid_status_not_available = (
        "Grid status not available for your Envoy device."
    )

    message_frequency_not_available = (
        "Frequency data not available for your Envoy device."
    )

    message_voltage_not_available = (
        "Voltage data not available for your Envoy device."
    )
    message_pf_not_available = (
        "Power Factor data not available for your Envoy device."
    )
    message_current_consumption_not_available = (
        "Amps consumption data not available for your Envoy device."
    )
    message_current_production_not_available = (
        "Amps production data not available for your Envoy device."
    )

    message_active_inverters_not_available = (
        "Active Inverter count not available for your Envoy device."
    )


    def __init__(  # pylint: disable=too-many-arguments
        self,
        host,
        username="envoy",
        password="",
        inverters=False,
        async_client=None,
        enlighten_user=None,
        enlighten_pass=None,
        commissioned=False,
        enlighten_site_id=None,
        enlighten_serial_num=None,
        https_flag="",
        use_enlighten_owner_token=False,
        token_refresh_buffer_seconds=0,
        store=None,
        info_refresh_buffer_seconds=3600,
        fetch_timeout_seconds=30,
        fetch_holdoff_seconds=0,
        fetch_retries=1,
        do_not_use_production_json=False,
    ):
        """Init the EnvoyReader."""
        self.host = host.lower().replace('[','').replace(']','')
        # IPv6 addresses need to be enclosed in brackets
        if is_ipv6_address(self.host):
            self.host = f"[{self.host}]"
        self.username = username
        self.password = password
        self.get_inverters = inverters
        self.endpoint_type = None
        self.has_grid_status = True
        self.serial_number_last_six = None
        self.endpoint_meters_reports_json_results = None
        self.endpoint_meters_readings_json_results = None
        self.endpoint_production_json_results = None
        self.endpoint_production_v1_results = None
        self.endpoint_production_inverters = None
        self.endpoint_production_results = None
        self.endpoint_ensemble_json_results = None
        self.endpoint_home_json_results = None
        self.endpoint_home_results = None
        self.isProductionMeteringEnabled = False  # pylint: disable=invalid-name
        self.isConsumptionMeteringEnabled = False  # pylint: disable=invalid-name
        self.net_consumption_meters_type = False
        self.production_meters_phase_count = 0
        self.consumption_meters_phase_count = 0
        self._async_client = async_client
        self._authorization_header = None
        self._cookies = None
        self.enlighten_user = enlighten_user
        self.enlighten_pass = enlighten_pass
        self.commissioned = commissioned
        self.enlighten_site_id = enlighten_site_id
        self.enlighten_serial_num = enlighten_serial_num
        self.https_flag = https_flag
        self.use_enlighten_owner_token = use_enlighten_owner_token
        self.token_refresh_buffer_seconds = token_refresh_buffer_seconds
        self.endpoint_info_results = None
        self.endpoint_meters_json_results = None
        self.info_refresh_buffer_seconds = info_refresh_buffer_seconds
        self.info_next_refresh_time = datetime.datetime.now()
        self.meters_next_refresh_time = datetime.datetime.now()
        self._store = store
        self._store_data = {}
        self._store_update_pending = False
        self._fetch_timeout_seconds = fetch_timeout_seconds
        self._fetch_holdoff_seconds = fetch_holdoff_seconds
        self._fetch_retries = max(fetch_retries,1)
        self._do_not_use_production_json=do_not_use_production_json

    @property
    def _token(self):
        return self._store_data.get("token", "")

    @_token.setter
    def _token(self, token_value):
        self._store_data["token"] = token_value
        self._store_update_pending = True

    async def _sync_store(self):
        if self._store and not self._store_data:
            self._store_data = await self._store.async_load() or {}

        if self._store and self._store_update_pending:
            self._store_update_pending = False
            await self._store.async_save(self._store_data)

    @property
    def async_client(self):
        """Return the httpx client."""
        return self._async_client or httpx.AsyncClient(verify=False,
                                                       headers=self._authorization_header,
                                                       cookies=self._cookies)

    @property
    def non_local_async_client(self):
        """Return the httpx client for non-local usage."""
        return self._async_client or httpx.AsyncClient(verify=True,
                                                       headers=self._authorization_header,
                                                       cookies=self._cookies)

    async def _update(self):
        """Update the data."""
        _LOGGER.debug("_update running")
        if self.endpoint_type == ENVOY_MODEL_S:
            await self._update_meters_endpoint()
            await self._update_from_pc_endpoint()
        if self.endpoint_type == ENVOY_MODEL_C or (
            self.endpoint_type == ENVOY_MODEL_S and not self.isProductionMeteringEnabled
        ):
            await self._update_from_p_endpoint()
        if self.endpoint_type == ENVOY_MODEL_LEGACY:
            await self._update_from_p0_endpoint()
            
        await self._update_info_endpoint()

    async def _update_from_meters_reports_endpoint(self):
        """Update from ivp/meters endpoint."""
        if self.endpoint_type == ENVOY_MODEL_S:
            #only touch meters reports if confirmed envoy model S, other type choke up on this request
            await self._update_endpoint(
                "endpoint_meters_reports_json_results", ENDPOINT_URL_METERS_REPORTS
            )

    async def _update_from_meters_readings_endpoint(self):
        """Update from ivp/meters/readings endpoint."""
        if self.endpoint_type == ENVOY_MODEL_S:
            #only touch meters reports if confirmed envoy model S, other type choke up on this request
            await self._update_endpoint(
                "endpoint_meters_readings_json_results", ENDPOINT_URL_METERS_READINGS
            )

    async def _update_from_pc_endpoint(self,detectmode=False):
        """Update from PC endpoint."""
        if not self._do_not_use_production_json or detectmode:
            await self._update_endpoint(
                "endpoint_production_json_results", ENDPOINT_URL_PRODUCTION_JSON
            )
        await self._update_endpoint(
            "endpoint_ensemble_json_results", ENDPOINT_URL_ENSEMBLE_INVENTORY
        )
        if self.has_grid_status:
            await self._update_endpoint(
                "endpoint_home_json_results", ENDPOINT_URL_HOME_JSON
            )

    async def _update_from_p_endpoint(self):
        """Update from P endpoint."""
        await self._update_endpoint(
            "endpoint_production_v1_results", ENDPOINT_URL_PRODUCTION_V1
        )

    async def _update_from_p0_endpoint(self):
        """Update from P0 endpoint."""
        await self._update_endpoint(
            "endpoint_production_results", ENDPOINT_URL_PRODUCTION
        )
        await self._update_endpoint(
            "endpoint_home_results", ENDPOINT_URL_HOME
        )

    async def _update_info_endpoint(self):
        """Update from info endpoint if next time expired."""
        if self.info_next_refresh_time <= datetime.datetime.now():
            await self._update_endpoint("endpoint_info_results", ENDPOINT_URL_INFO_XML)
            self.info_next_refresh_time = datetime.datetime.now() + datetime.timedelta(
                seconds=self.info_refresh_buffer_seconds
            )
            _LOGGER.debug(
                "Info endpoint updated, set next update time: %s using interval: %s",
                self.info_next_refresh_time,
                self.info_refresh_buffer_seconds,
            )
        else:
            _LOGGER.debug(
                "Info endpoint next update time is: %s using interval: %s",
                self.info_next_refresh_time,
                self.info_refresh_buffer_seconds,
            )

    async def _update_meters_endpoint(self):
        """Update from meters endpoint if next time expried."""
        if self.meters_next_refresh_time <= datetime.datetime.now():
            await self._update_endpoint("endpoint_meters_json_results", ENDPOINT_URL_METERS)

            #some devices return [] for ivp/meters
            if self.endpoint_meters_json_results and self.endpoint_meters_json_results.text != "[]":

                self.isProductionMeteringEnabled = has_production_metering_setup(
                    self.endpoint_meters_json_results.json()
                )
                self.isConsumptionMeteringEnabled = has_consumption_metering_setup(
                    self.endpoint_meters_json_results.json()
                )
                self.net_consumption_meters_type = has_net_consumption_meters_type(
                    self.endpoint_meters_json_results.json()
                )
                self.production_meters_phase_count = get_production_meters_phase_count(
                    self.endpoint_meters_json_results.json()
                )
                self.consumption_meters_phase_count = get_consumption_meters_phase_count(
                    self.endpoint_meters_json_results.json()
                )
                self.meters_next_refresh_time = datetime.datetime.now() + datetime.timedelta(
                    seconds=self.info_refresh_buffer_seconds
                )

            _LOGGER.debug(
                "Meters endpoint updated, set next update time: %s using interval: %s",
                self.meters_next_refresh_time,
                self.info_refresh_buffer_seconds,
            )
        else:
            _LOGGER.debug(
                "Meters endpoint next update time is: %s using interval: %s",
                self.meters_next_refresh_time,
                self.info_refresh_buffer_seconds,
            )
        await self._update_from_meters_reports_endpoint()
        await self._update_from_meters_readings_endpoint()

    async def _update_endpoint(self, attr, url):
        """Update a property from an endpoint."""
        formatted_url = url.format(self.https_flag, self.host)
        response = await self._async_fetch_with_retry(
            formatted_url, follow_redirects=False
        )
        setattr(self, attr, response)

    async def _async_fetch_with_retry(self, url, **kwargs):
        """Retry 3 times to fetch the url if there is a transport error."""
        for attempt in range(self._fetch_retries + 1):
            header = " <Blank Header> "
            if self._authorization_header:
                header = " <Token hidden> "
            _LOGGER.debug(
                "HTTP GET Attempt #%s of %s: %s: use token: %s: Header:%s Timeout: %s Holdoff: %s",
                attempt + 1,
                self._fetch_retries + 1,
                url,
                self.use_enlighten_owner_token,
                header,
                self._fetch_timeout_seconds,
                self._fetch_holdoff_seconds,
            )
            async with self.async_client as client:
                try:
                    getstart = time.time()
                    resp = await client.get(
                        url, headers=self._authorization_header, timeout=self._fetch_timeout_seconds, **kwargs
                    )
                    getend = time.time()
                    if resp.status_code == 401 and attempt < self._fetch_retries:
                        if self.use_enlighten_owner_token:
                            _LOGGER.debug(
                                "Received 401 from Envoy; refreshing cookies, in attempt %s of %s:",
                                attempt+1,
                                self._fetch_retries + 1
                             )
                            could_refresh_cookies = await self._refresh_token_cookies()
                            if not could_refresh_cookies:
                                _LOGGER.debug(
                                    "cookie refresh failed, getting token, in attempt %s of %s:",
                                    attempt+1,
                                    self._fetch_retries + 1
                                )
                                await self._getEnphaseToken()
                            continue
                        # don't try token and cookies refresh for legacy envoy
                        else:
                            _LOGGER.debug(
                                "Received 401 from Envoy; retrying, attempt %s of %s",
                                attempt+1,
                                self._fetch_retries + 1
                            )
                            continue
                    _LOGGER.debug("Fetched (%s of %s) in %s sec from %s: %s: %s",
                        attempt + 1,
                        self._fetch_retries + 1,
                        round(getend - getstart,1),
                        url, 
                        resp, 
                        resp.text
                    )
                    if resp.status_code == 404:
                        return None
                    return resp
                
                except httpx.TimeoutException as exc:
                    if attempt == self._fetch_retries:
                        _LOGGER.warning("HTTP Timeout in fetch_with_retry, raising: %s",exc)
                        raise
                    # Sleep a bit and try once more
                    _LOGGER.warning("HTTP Timeout in fetch_with_retry, waiting %s sec: %s",self._fetch_holdoff_seconds,exc)
                    await asyncio.sleep(self._fetch_holdoff_seconds)
                except Exception as exc:
                    if attempt == self._fetch_retries:
                        _LOGGER.warning("Error in fetch_with_retry, raising: %s",exc)
                        raise
                    # Sleep a bit and try once more
                    _LOGGER.warning("Error in fetch_with_retry, waiting %s sec: %s",self._fetch_holdoff_seconds,exc)
                    await asyncio.sleep(self._fetch_holdoff_seconds)

    async def _async_post(self, url, data, cookies=None, client=None, **kwargs):
        _LOGGER.debug("HTTP POST Attempt: %s", url)
        if client is None:
            client = self.async_client
        # _LOGGER.debug("HTTP POST Data: %s", data)
        try:
            async with client:
                resp = await client.post(
                    url, cookies=cookies, data=data, timeout=30, **kwargs
                )
                _LOGGER.debug("HTTP POST %s: %s: %s", url, resp, resp.text)
                _LOGGER.debug("HTTP POST Cookie: %s", resp.cookies)
                return resp
        except httpx.TransportError:  # pylint: disable=try-except-raise
            raise

    async def _fetch_owner_token_json(self) :
        """Try to fetch the owner token json from Enlighten API"""
        async with self.non_local_async_client as client:
            # login to the enlighten website
            payload_login = {
                'user[email]': self.enlighten_user,
                'user[password]': self.enlighten_pass,
            }
            resp = await client.post(ENLIGHTEN_AUTH_URL, data=payload_login, timeout=30)
            if resp.status_code >= 400:
                raise RuntimeError(f"Could not Authenticate with Enlighten, status: {resp.status_code}, {resp}")

            # now that we're in a logged in session, we can request the 1 year owner token via enlighten
            login_data = resp.json()
            payload_token = {
                "session_id": login_data["session_id"],
                "serial_num": self.enlighten_serial_num,
                "username": self.enlighten_user,
            }
            resp = await client.post(
                ENLIGHTEN_TOKEN_URL, json=payload_token, timeout=30
            )
            if resp.status_code != 200:
                raise RuntimeError(f"Could not get enlighten token, status: {resp.status_code}, {resp}")
            return resp.text

    async def _getEnphaseToken(self):
        self._token = await self._fetch_owner_token_json()
        _LOGGER.debug("Obtained Token")

        if self._is_enphase_token_expired(self._token):
            raise RuntimeError("Just received token already expired")

        await self._refresh_token_cookies()

    async def _refresh_token_cookies(self):
        """
         Refresh the client's cookie with the token (if valid)
         :returns True if cookie refreshed, False if it couldn't be
        """
        # Create HTTP Header
        self._authorization_header = {"Authorization": "Bearer " + self._token}

        # Fetch the Enphase Token status from the local Envoy
        token_validation = await self._async_fetch_with_retry(
            ENDPOINT_URL_CHECK_JWT.format(self.host)
        )

        if token_validation.status_code == 200:
            # set the cookies for future clients
            self._cookies = token_validation.cookies
            return True

        # token not valid if we get here
        return False


    def _is_enphase_token_valid(self, response):
        if response == "Valid token.":
            _LOGGER.debug("Token is valid")
            return True
        else:
            _LOGGER.debug("Invalid token!")
            return False

    def _is_enphase_token_expired(self, token):
        decode = jwt.decode(
            token, options={"verify_signature": False}, algorithms="ES256"
        )
        exp_epoch = decode["exp"]
        # allow a buffer so we can try and grab it sooner
        exp_epoch -= self.token_refresh_buffer_seconds
        exp_time = datetime.datetime.fromtimestamp(exp_epoch)
        if datetime.datetime.now() < exp_time:
            _LOGGER.debug("Token expires at: %s", exp_time)
            return False
        else:
            _LOGGER.debug("Token expired on: %s", exp_time)
            return True

    async def check_connection(self):
        """Check if the Envoy is reachable. Also check if HTTP or"""
        """HTTPS is needed."""
        _LOGGER.debug("Checking Host: %s", self.host)
        resp = await self._async_fetch_with_retry(
            ENDPOINT_URL_PRODUCTION_V1.format(self.https_flag, self.host)
        )
        _LOGGER.debug("Check connection HTTP Code: %s", resp.status_code)
        if resp.status_code == 301:
            raise SwitchToHTTPS

    async def getData(self, getInverters=True):  # pylint: disable=invalid-name
        """Fetch data from the endpoint and if inverters selected default"""
        """to fetching inverter data."""

        # Check if the Secure flag is set
        if self.https_flag == "s":
            _LOGGER.debug(
                "Checking Token value: %s (Only first 10 characters shown)",
                self._token[1:10],
            )
            # Check if a token has already been retrieved
            if self._token == "":
                _LOGGER.debug("Found empty token: %s", self._token)
                await self._getEnphaseToken()
            else:
                _LOGGER.debug(
                    "Token is populated: %s (Only first 10 characters shown)",
                    self._token[1:10],
                )
                if self._is_enphase_token_expired(self._token):
                    _LOGGER.debug("Found Expired token - Retrieving new token")
                    await self._getEnphaseToken()

        if not self.endpoint_type:
            await self.detect_model()
        else:
            await self._update()

        _LOGGER.debug(
            "Using Model: %s (HTTP%s, Production Metering: %s phases: %s, Consumption Metering: %s phases: %s, Net consumption CT: %s, Get Inverters: %s)",
            self.endpoint_type, 
            self.https_flag,
            self.isProductionMeteringEnabled,
            self.production_meters_phase_count,
            self.isConsumptionMeteringEnabled,
            self.consumption_meters_phase_count,
            self.net_consumption_meters_type,
            self.get_inverters
        )

        if not self.get_inverters or not getInverters:
            return

        inverters_url = ENDPOINT_URL_PRODUCTION_INVERTERS.format(
            self.https_flag, self.host
        )
        if self.use_enlighten_owner_token:
            response = await self._async_fetch_with_retry(inverters_url)
        else:
            # Inverter page on envoy with old firmware requires username/password
            inverters_auth = httpx.DigestAuth(self.username, self.password)
            response = await self._async_fetch_with_retry(
                inverters_url, auth=inverters_auth
            )
        if response.status_code in [401,404]:
            if self.endpoint_type in [ENVOY_MODEL_C, ENVOY_MODEL_LEGACY]:
                self.get_inverters = False
                _LOGGER.debug("Error %s in Getdata for getting invertors, disabling inverters",response.status_code)
                return
            response.raise_for_status()
        self.endpoint_production_inverters = response
        return

    async def detect_model(self):
        """Method to determine if the Envoy supports consumption values or only production."""
        # If a password was not given as an argument when instantiating
        # the EnvoyReader object than use the last six numbers of the serial
        # number as the password.  Otherwise use the password argument value.
        _LOGGER.debug("Detect Model running")
        if self.password == "" and not self.serial_number_last_six:
            await self.get_serial_number()

        try:
            await self._update_from_pc_endpoint(detectmode=True)
        except httpx.HTTPError:
            pass

        # If self.endpoint_production_json_results.status_code is set with
        # 401 then we will give an error
        if (
            self.endpoint_production_json_results
            and self.endpoint_production_json_results.status_code == 401
        ):
            raise RuntimeError(
                "Could not connect to Envoy model. "
                + "Appears your Envoy is running firmware that requires secure communcation. "
                + "Please enter in the needed Enlighten credentials during setup."
            )

        await self._update_info_endpoint()

        if (
            self.endpoint_production_json_results
            and self.endpoint_production_json_results.status_code == 200
            and has_production_and_consumption(
                self.endpoint_production_json_results.json()
            )
        ):
            _LOGGER.debug("Detect Model found production and consumption")
             #only access meters endpoint if envoy metered, other type may choke up
            self.endpoint_type = ENVOY_MODEL_S
            
            await self._update_meters_endpoint()

            if not self.isProductionMeteringEnabled:
                await self._update_from_p_endpoint()
            return

        try:
            await self._update_from_p_endpoint()
        except httpx.HTTPError:
            pass
        if (
            self.endpoint_production_v1_results
            and self.endpoint_production_v1_results.status_code == 200
        ):
            self.endpoint_type = ENVOY_MODEL_C  # Envoy-C, production only
            return

        try:
            await self._update_from_p0_endpoint()
        except httpx.HTTPError:
            pass
        if (
            self.endpoint_production_results
            and self.endpoint_production_results.status_code == 200
        ):
            self.endpoint_type = ENVOY_MODEL_LEGACY  # older Envoy-C
            self.get_inverters = False # don't get inverters for this model
            return

        raise RuntimeError(
            "Could not connect or determine Envoy model. "
            + "Check that the device is up at 'http://"
            + self.host
            + "'."
        )

    async def get_serial_number(self):
        """Method to get last six digits of Envoy serial number for auth"""
        full_serial = await self.get_full_serial_number()
        if full_serial:
            gen_passwd = EnvoyUtils.get_password(full_serial, self.username)
            if self.username == "envoy" or self.username != "installer":
                self.password = self.serial_number_last_six = full_serial[-6:]
            else:
                self.password = gen_passwd

    async def get_full_serial_number(self):
        """Method to get the  Envoy serial number."""
        response = await self._async_fetch_with_retry(
            f"http{self.https_flag}://{self.host}/info.xml",
            follow_redirects=True,
        )
        if not response.text:
            return None
        if "<sn>" in response.text:
            return response.text.split("<sn>")[1].split("</sn>")[0]
        match = SERIAL_REGEX.search(response.text)
        if match:
            # if info.xml is in html format we're dealing with ENVOY R
            _LOGGER.debug("Legacy model identified by info.xml being html. Disabling inverters")
            self.get_inverters = False
            return match.group(1)

    def create_connect_errormessage(self):
        """Create error message if unable to connect to Envoy"""
        return (
            "Unable to connect to Envoy. "
            + "Check that the device is up at 'http://"
            + self.host
            + "'."
        )

    def create_json_errormessage(self):
        """Create error message if unable to parse JSON response"""
        return (
            "Got a response from '"
            + self.host
            + "', but metric could not be found. "
            + "Maybe your model of Envoy doesn't "
            + "support the requested metric."
        )

    async def _meters_readings_value(self,field,report="net-consumption",phase=None):
        """Extract value from meters readings json"""
        report_map = {"production": 0, "net-consumption": 1, "total-consumption": 1}

        phase_map = {"l1": 0, "l2": 1, "l3": 2}
        #meters readings is only available for ENVOY Metered with CT configured
        if (self.endpoint_type == ENVOY_MODEL_S) and (
            #net-consumption requires consumption CT installed is Solar power included mode
            (report == "net-consumption" 
                and self.isConsumptionMeteringEnabled 
                and self.net_consumption_meters_type)
            # production data requires production CT installed
            or (report == "production" and self.isProductionMeteringEnabled )
            #if at least consumption CT is installed total-consumption will be available even in Load only mode install
            or (report == "total-consumption" 
                and self.isConsumptionMeteringEnabled
                and not self.net_consumption_meters_type )
        ):
            if self.endpoint_meters_readings_json_results:
                raw_json = self.endpoint_meters_readings_json_results.json()
                if phase == None:
                    try:
                        jsondata = raw_json[report_map[report]][field]
                        return jsondata
                    except (KeyError, IndexError):
                        return None
                
                #if production data requested and multiple phases are configured and requested phase is in count of configured phases return data or
                #if consumption data requested and multiple phases are configured and requested phase is in count of configured phases return date
                if ((self.production_meters_phase_count > 1 and phase_map[phase] < self.production_meters_phase_count and report=="production")
                 or (self.consumption_meters_phase_count > 1 and phase_map[phase] < self.consumption_meters_phase_count and report!="production")):
                    try:
                        jsondata = raw_json[report_map[report]]["channels"][phase_map[phase]][field]
                        return jsondata
                    except (KeyError, IndexError):
                        return None
        return None

    async def _meters_report_value(self,field,report="production",phase=None):
        """Extract value from meters reports json if consumption meter is available"""
        report_map = {"production": 0, "net-consumption": 1, "total-consumption": 2}
        phase_map = {"l1": 0, "l2": 1, "l3": 2}
        #meters reports is only available for ENVOY Metered with CT configured
        if (self.endpoint_type == ENVOY_MODEL_S) and (
            #net-consumption requires consumption CT installed is Solar power included mode
            (report == "net-consumption" and self.isConsumptionMeteringEnabled and self.net_consumption_meters_type)
            # production data requires production CT installed
            or (report == "production" and self.isProductionMeteringEnabled)
            #if at least consumption CT is installed total-consumption will be available even in Load only mode install
            or (report == "total-consumption" and self.isConsumptionMeteringEnabled)
        ):
            if self.endpoint_meters_reports_json_results:
                raw_json = self.endpoint_meters_reports_json_results.json()
                if phase == None:
                    jsondata = raw_json[report_map[report]]["cumulative"][field]
                    return jsondata
                
                #if production data requested and multiple phases are configured and requested phase is in count of configured phases return data or
                #if consumption data requested and multiple phases are configured and requested phase is in count of configured phases return date
                if ((self.production_meters_phase_count > 1 and phase_map[phase] < self.production_meters_phase_count and report=="production")
                 or (self.consumption_meters_phase_count > 1 and phase_map[phase] < self.consumption_meters_phase_count and report!="production")):
                    try:
                        jsondata = raw_json[report_map[report]]["lines"][phase_map[phase]][field]
                        return jsondata
                    except (KeyError, IndexError):
                        return None
        return None

    async def production(self,phase=None):
        """Report System or Phase Power Production data from sources for various Envoy types"""
        if phase is not None:
            # if phase is specified return phase data rather then system data
            return await self.production_phase(phase)
        
        if self.endpoint_type == ENVOY_MODEL_S:
            if self.isProductionMeteringEnabled:
                raw_json = self.endpoint_meters_reports_json_results.json()
                production = raw_json[0]["cumulative"]["currW"]
            else:
                raw_json = self.endpoint_production_json_results.json()
                production = raw_json["production"][0]["wNow"]
        elif self.endpoint_type == ENVOY_MODEL_C:
            raw_json = self.endpoint_production_v1_results.json()
            production = raw_json["wattsNow"]
        elif self.endpoint_type == ENVOY_MODEL_LEGACY:
            text = self.endpoint_production_results.text
            match = re.search(PRODUCTION_REGEX, text, re.MULTILINE)
            if match:
                if match.group(2) == "kW":
                    production = float(match.group(1)) * 1000
                else:
                    if match.group(2) == "mW":
                        production = float(match.group(1)) * 1000000
                    else:
                        production = float(match.group(1))
            else:
                raise RuntimeError("No match for production, check REGEX  " + text)
        return int(production)

    async def production_phase(self, phase):
        """Report Phase Power Production data from meters report json"""
        jsondata = await self._meters_report_value("currW",report="production",phase=phase)
        if jsondata is None:
            return self.message_consumption_not_available if phase is None else None
        return int(jsondata)

    async def consumption(self,phase=None):
        """Report cumulative or phase Power consumption (to house) from consumption CT meters report"""
        jsondata = await self._meters_report_value("currW",report="total-consumption",phase=phase)
        if jsondata is None:
            return self.message_consumption_not_available if phase is None else None
        return int(jsondata)

    async def net_consumption(self,phase=None):
        """Report cumulative or phase Power consumption (to/from grid) from consumption CT meters report"""
        jsondata = await self._meters_readings_value("instantaneousDemand",report="net-consumption",phase=phase)
        if jsondata is None:
            return self.message_consumption_not_available if phase is None else None
        return int(jsondata)

    async def daily_production(self,phase=None):
        """Report System or Phase Daily energy Production data from sources for various Envoy types"""
        if phase is not None:
            # if phase is specified return phase data rather then system data
            return await self.daily_production_phase(phase)

        if self.endpoint_type == ENVOY_MODEL_S and self.isProductionMeteringEnabled:
            if self._do_not_use_production_json:
                return self.message_production_not_available
            raw_json = self.endpoint_production_json_results.json()
            daily_production = raw_json["production"][1]["whToday"]
        elif self.endpoint_type == ENVOY_MODEL_C or (
            self.endpoint_type == ENVOY_MODEL_S and not self.isProductionMeteringEnabled
        ):
            raw_json = self.endpoint_production_v1_results.json()
            daily_production = raw_json["wattHoursToday"]
        elif self.endpoint_type == ENVOY_MODEL_LEGACY:
            text = self.endpoint_production_results.text
            match = re.search(DAY_PRODUCTION_REGEX, text, re.MULTILINE)
            if match:
                if match.group(2) == "kWh":
                    daily_production = float(match.group(1)) * 1000
                else:
                    if match.group(2) == "MWh":
                        daily_production = float(match.group(1)) * 1000000
                    else:
                        daily_production = float(match.group(1))
            else:
                raise RuntimeError(
                    "No match for Day production, " "check REGEX  " + text
                )
        return int(daily_production)

    async def daily_production_phase(self, phase):
        """Report Phase Daily energy Production data from production json"""
        phase_map = {"l1": 0,"l2": 1,"l3": 2}

        if (self.endpoint_type == ENVOY_MODEL_S and self.isProductionMeteringEnabled and
            self.production_meters_phase_count > 1 and phase_map[phase] < self.production_meters_phase_count
            and not self._do_not_use_production_json):
            raw_json = self.endpoint_production_json_results.json()
            try:
                return int(
                    raw_json["production"][1]["lines"][phase_map[phase]]["whToday"]
                )
            except (KeyError, IndexError):
                return None

        return None

    async def daily_consumption(self,phase=None):
        """Report System or Phase Daily energy Consumption data from production json"""
        if phase is not None:
            # if phase is specified return phase data rather then system data
            return await self.daily_consumption_phase(phase)
 
        """Only return data if Envoy supports Consumption"""
        if self.endpoint_type == ENVOY_MODEL_S and self.isConsumptionMeteringEnabled:
            if self._do_not_use_production_json:
                return self.message_consumption_not_available
            raw_json = self.endpoint_production_json_results.json()
            daily_consumption = raw_json["consumption"][0]["whToday"]
            return int(daily_consumption)

        return self.message_consumption_not_available

    async def daily_consumption_phase(self, phase):
        """Report Phase Daily energy Consumption data from production json"""
        phase_map = {"l1": 0,"l2": 1,"l3": 2}

        """Only return data if Envoy supports Consumption"""
        if (self.endpoint_type == ENVOY_MODEL_S and self.isConsumptionMeteringEnabled and
            self.consumption_meters_phase_count > 1 and phase_map[phase] < self.consumption_meters_phase_count):
            if self._do_not_use_production_json:
                return None
            raw_json = self.endpoint_production_json_results.json()
            try:
                return int(
                    raw_json["consumption"][0]["lines"][phase_map[phase]]["whToday"]
                )
            except (KeyError, IndexError):
                return None

        return None

    async def seven_days_production(self):
        """Report Last seven day energy production data from production json"""

        if self.endpoint_type == ENVOY_MODEL_S and self.isProductionMeteringEnabled:
            if self._do_not_use_production_json:
                return self.message_production_not_available
            raw_json = self.endpoint_production_json_results.json()
            seven_days_production = raw_json["production"][1]["whLastSevenDays"]
        elif self.endpoint_type == ENVOY_MODEL_C or (
            self.endpoint_type == ENVOY_MODEL_S and not self.isProductionMeteringEnabled
        ):
            raw_json = self.endpoint_production_v1_results.json()
            seven_days_production = raw_json["wattHoursSevenDays"]
        elif self.endpoint_type == ENVOY_MODEL_LEGACY:
            text = self.endpoint_production_results.text
            match = re.search(WEEK_PRODUCTION_REGEX, text, re.MULTILINE)
            if match:
                if match.group(2) == "kWh":
                    seven_days_production = float(match.group(1)) * 1000
                else:
                    if match.group(2) == "MWh":
                        seven_days_production = float(match.group(1)) * 1000000
                    else:
                        seven_days_production = float(match.group(1))
            else:
                raise RuntimeError(
                    "No match for 7 Day production, " "check REGEX " + text
                )
        return int(seven_days_production)

    async def seven_days_consumption(self):
        """Report Last seven day energy consumption data from production json"""

        """Only return data if Envoy supports Consumption"""
        if self.endpoint_type == ENVOY_MODEL_S and self.isConsumptionMeteringEnabled:
            if self._do_not_use_production_json:
                return self.message_production_not_available    
            raw_json = self.endpoint_production_json_results.json()
            seven_days_consumption = raw_json["consumption"][0]["whLastSevenDays"]
            return int(seven_days_consumption)

        return self.message_consumption_not_available

    async def lifetime_production(self,phase=None):
        """Report system or Phase lifetime Energy production from sources for various Envoy types"""
        if phase is not None:
            # if phase is specified return phase data rather then system data
            return await self.lifetime_production_phase(phase)

        if self.endpoint_type == ENVOY_MODEL_S:
            if self.isProductionMeteringEnabled:
                raw_json = self.endpoint_meters_reports_json_results.json()
                lifetime_production = raw_json[0]["cumulative"]["whDlvdCum"]
            else:
                raw_json = self.endpoint_production_json_results.json()
                lifetime_production = raw_json["production"][0]["whLifetime"]
        elif self.endpoint_type == ENVOY_MODEL_C:
            raw_json = self.endpoint_production_v1_results.json()
            lifetime_production = raw_json["wattHoursLifetime"]
        elif self.endpoint_type == ENVOY_MODEL_LEGACY:
            text = self.endpoint_production_results.text
            match = re.search(LIFE_PRODUCTION_REGEX, text, re.MULTILINE)
            if match:
                if match.group(2) == "kWh":
                    lifetime_production = float(match.group(1)) * 1000
                else:
                    if match.group(2) == "MWh":
                        lifetime_production = float(match.group(1)) * 1000000
                    else:
                        lifetime_production = float(match.group(1))
            else:
                raise RuntimeError(
                    "No match for Lifetime production, " "check REGEX " + text
                )
        return int(lifetime_production)

    async def lifetime_production_phase(self, phase):
        """Report Phase lifetime Energy production from meters repors json"""
        jsondata = await self._meters_report_value("whDlvdCum",report="production",phase=phase)
        if jsondata is None:
            return self.message_production_not_available if phase is None else None
        return int(jsondata)

    async def lifetime_net_production(self,phase=None):
        """Report cumulative or phase lifetime net production (exported to grid) from consumption CT meters report"""
        jsondata = await self._meters_readings_value("actEnergyRcvd",report="net-consumption",phase=phase)
        if jsondata is None:
            return self.message_consumption_not_available if phase is None else None
        return int(jsondata)
        
    async def lifetime_consumption(self,phase=None):
        """Report cumulative or phase lifetime total-consumption from consumption CT meters report"""
        jsondata = await self._meters_report_value("whDlvdCum",report="total-consumption",phase=phase)
        if jsondata is None:
            return self.message_consumption_not_available if phase is None else None
        return int(jsondata)
        
    async def lifetime_net_consumption(self,phase=None):
        """Report cumulative or phase lifetime net-consumption from consumption CT meters report"""
        jsondata = await self._meters_readings_value("actEnergyDlvd",report="net-consumption",phase=phase)
        if jsondata is None:
            return self.message_consumption_not_available if phase is None else None
        return int(jsondata)
        
    async def inverters_production(self):
        """Running getData() beforehand will set self.enpoint_type and self.isDataRetrieved"""
        """so that this method will only read data from stored variables"""

        """Only return data if Envoy supports retrieving Inverter data"""
        if not self.get_inverters:
            return None
        
        response_dict = {}
        try:
            for item in self.endpoint_production_inverters.json():
                response_dict[item["serialNumber"]] = [
                    item["lastReportWatts"],
                    time.strftime(
                        "%Y-%m-%d %H:%M:%S", time.localtime(item["lastReportDate"])
                    ),
                ]
        except (JSONDecodeError, KeyError, IndexError, TypeError, AttributeError):
            return None

        return response_dict

    async def battery_storage(self):
        """Return battery data from Envoys that support and have batteries installed"""
        if self.endpoint_type in [ENVOY_MODEL_C,ENVOY_MODEL_LEGACY]:
            return self.message_battery_not_available

        try:
            raw_json = self.endpoint_production_json_results.json()
        except JSONDecodeError:
            return None

        """For Envoys that support batteries but do not have them installed the"""
        """percentFull will not be available in the JSON results. The API will"""
        """only return battery data if batteries are installed."""
        if "percentFull" not in raw_json["storage"][0].keys():
            # "ENCHARGE" batteries are part of the "ENSEMBLE" api instead
            # Check to see if it's there. Enphase has too much fun with these names
            if self.endpoint_ensemble_json_results is not None:
                ensemble_json = self.endpoint_ensemble_json_results.json()
                if len(ensemble_json) > 0 and "devices" in ensemble_json[0].keys():
                    return ensemble_json[0]["devices"]
            return self.message_battery_not_available

        return raw_json["storage"][0]

    async def pf(self,phase=None):
        """Report cumulative or phase PowerFactor from consumption CT meters report"""
        jsondata = await self._meters_report_value("pwrFactor",report="net-consumption",phase=phase)
        if jsondata is None:
            return self.message_pf_not_available if phase is None else None
        return float(str(jsondata))
        
    async def voltage(self,phase=None):
        """Report cumulative or phase Voltage from consumption CT meters report"""
        jsondata = await self._meters_report_value("rmsVoltage",report="net-consumption",phase=phase)
        if jsondata is None:
            return self.message_voltage_not_available if phase is None else None
        return float(str(jsondata))
        
    async def frequency(self,phase=None):
        """Report cumulative or phase Frequency from consumption CT meters report"""
        jsondata = await self._meters_report_value("freqHz",report="net-consumption",phase=phase)
        if jsondata is None:
            return self.message_frequency_not_available if phase is None else None
        return float(str(jsondata))

    async def consumption_Current(self,phase=None):
        """Report cumulative or phase rmsCurrent from consumption CT meters report"""
        jsondata = await self._meters_report_value("rmsCurrent",report="net-consumption",phase=phase)
        if jsondata is None:
            return self.message_current_consumption_not_available if phase is None else None
        return float(str(jsondata))
        
    async def production_Current(self,phase=None):
        """Report cumulative or phase rmsCurrent from production CT meters report"""
        jsondata = await self._meters_report_value("rmsCurrent",report="production",phase=phase)
        if jsondata is None:
            return self.message_current_production_not_available if phase is None else None
        return float(str(jsondata))
        
    async def grid_status(self):
        """Return grid status reported by Envoy"""
        if self.has_grid_status and self.endpoint_home_json_results is not None:
            if self.endpoint_home_json_results.status_code == 200:
                home_json = self.endpoint_home_json_results.json()
                if ("enpower" in home_json.keys() and "grid_status" in home_json["enpower"].keys()):
                    return home_json["enpower"]["grid_status"]
        self.has_grid_status = False
        return None

    async def active_inverter_count(self) -> int|str:
        """Return active inverter count from /home html for legacy envoy"""
        if (self.endpoint_type == ENVOY_MODEL_LEGACY
            and self.endpoint_home_results
            and self.endpoint_home_results.status_code == 200):
                
            text = self.endpoint_home_results.text
            match = re.search(ACTIVE_INVERTER_COUNT_REGEX, text, re.MULTILINE)
            if match:
                active_count = int(match.group(1))
                return active_count

        return self.message_active_inverters_not_available

    async def envoy_info(self):
        """Return information reported by Envoy info.xml."""
        device_data = {}

        if self.endpoint_info_results:
            try:
                data = xmltodict.parse(self.endpoint_info_results.text)
                device_data["software"] = data["envoy_info"]["device"]["software"]
                device_data["pn"] = data["envoy_info"]["device"]["pn"]
                device_data["metered"] = data["envoy_info"]["device"]["imeter"]
            except Exception:  # pylint: disable=broad-except
                pass
        # add internal key information for envoy class
        device_data["Using-model"] = self.endpoint_type
        device_data["Using-httpsflag"] = self.https_flag
        device_data["Using-ProductionMeteringEnabled"] = self.isProductionMeteringEnabled
        device_data["Using-ConsumptionMeteringEnabled"] = self.isConsumptionMeteringEnabled
        device_data["Using-GetInverters"] = self.get_inverters
        device_data["Using-UseEnligthen"] = self.use_enlighten_owner_token
        device_data["Using-InfoUpdateInterval"] = self.info_refresh_buffer_seconds
        device_data["Using-hasgridstatus"] = self.has_grid_status
        device_data["Using-FetchRetryCount"] = self._fetch_retries
        device_data["Using-FetchTimeOut"] = self._fetch_timeout_seconds
        device_data["Using-FetchHoldoff"] = self._fetch_holdoff_seconds

        if self.endpoint_meters_json_results:
            device_data["Endpoint-meters"] = self.endpoint_meters_json_results.text
        else:
            device_data["Endpoint-meters"] = self.endpoint_meters_json_results
        if self.endpoint_meters_readings_json_results:
            device_data["Endpoint-meters-readings"] = self.endpoint_meters_readings_json_results.text
        else:
            device_data["Endpoint-meters-readings"] = self.endpoint_meters_readings_json_results
        if self.endpoint_meters_reports_json_results:
            device_data["Endpoint-meters-reports"] = self.endpoint_meters_reports_json_results.text
        else:
            device_data["Endpoint-meters-reports"] = self.endpoint_meters_reports_json_results
        if self.endpoint_production_json_results:
            device_data[
                "Endpoint-production_json"
            ] = self.endpoint_production_json_results.text
        else:
            device_data[
                "Endpoint-production_json"
            ] = self.endpoint_production_json_results
        if self.endpoint_production_v1_results:
            device_data[
                "Endpoint-production_v1"
            ] = self.endpoint_production_v1_results.text
        else:
            device_data["Endpoint-production_v1"] = self.endpoint_production_v1_results
        if self.endpoint_production_results:
            device_data["Endpoint-production"] = self.endpoint_production_results.text
        else:
            device_data["Endpoint-production"] = self.endpoint_production_results
        if self.endpoint_production_inverters:
            device_data[
                "Endpoint-production_inverters"
            ] = self.endpoint_production_inverters.text
        else:
            device_data[
                "Endpoint-production_inverters"
            ] = self.endpoint_production_inverters
        if self.endpoint_ensemble_json_results:
            device_data[
                "Endpoint-ensemble_json"
            ] = self.endpoint_ensemble_json_results.text
        else:
            device_data["Endpoint-ensemble_json"] = self.endpoint_ensemble_json_results
        if self.endpoint_home_json_results:
            device_data["Endpoint-home"] = self.endpoint_home_json_results.text
        else:
            device_data["Endpoint-home"] = self.endpoint_home_json_results
        if self.endpoint_info_results:
            device_data["Endpoint-info"] = self.endpoint_info_results.text
        else:
            device_data["Endpoint-info"] = self.endpoint_info_results
        if self.endpoint_home_results:
            device_data["legacy-home"] = self.endpoint_home_results.text
        else:
            device_data["legacy-home"] = self.endpoint_home_results

        return device_data

    def run_in_console(self, dumpraw=False,loopcount=1,waittime=1):
        """If running this module directly, print all the values in the console."""
        loop = asyncio.get_event_loop()
        for attempt in range(0,loopcount):
            if attempt > 0:
                print("Sleeping...")
                time.sleep(waittime)
            print("Reading...")
            data_results = loop.run_until_complete(
                asyncio.gather(self.getData(), return_exceptions=False)
            )

            loop = asyncio.get_event_loop()
            results = loop.run_until_complete(
                asyncio.gather(
                    self.production(), #0
                    self.consumption(),
                    self.net_consumption(),
                    self.daily_production(),
                    self.daily_consumption(),
                    self.seven_days_production(),
                    self.seven_days_consumption(),
                    self.lifetime_production(),
                    self.lifetime_net_production(),
                    self.lifetime_consumption(),
                    self.lifetime_net_consumption(), #10
                    self.battery_storage(),
                    self.inverters_production(),
                    self.envoy_info(),
                    self.pf(),
                    self.voltage(),
                    self.frequency(),
                    self.consumption_Current(),
                    self.production_Current(),
                    #get values for phase L2
                    self.production_phase("l2"),
                    self.consumption("l2"),  #20
                    self.net_consumption("l2"),
                    self.daily_production_phase("l2"),
                    self.daily_consumption_phase("l2"),
                    self.lifetime_production_phase("l2"),
                    self.lifetime_net_production("l2"),
                    self.lifetime_consumption("l2"),
                    self.lifetime_net_consumption("l2"),
                    self.pf("l2"),
                    self.voltage("l2"),
                    self.frequency("l2"), #30
                    self.consumption_Current("l2"),
                    self.production_Current("l2"),
                    self.grid_status(),
                    self.active_inverter_count(), #34
                    return_exceptions=False,
                )
            )

            print("--System values--")
            print(f"production:               {results[0]}")
            print(f"consumption:              {results[1]}")
            print(f"net_consumption:          {results[2]}")
            print(f"daily_production:         {results[3]}")
            print(f"daily_consumption:        {results[4]}")
            print(f"seven_days_production:    {results[5]}")
            print(f"seven_days_consumption:   {results[6]}")
            print(f"lifetime_production:      {results[7]}")
            print(f"lifetime_net_production:  {results[8]}")
            print(f"lifetime_consumption:     {results[9]}")
            print(f"lifetime_net_consumption: {results[10]}")
            print(f"battery_storage:          {results[11]}")
            print(f"pf:                       {results[14]}")
            print(f"voltage:                  {results[15]}")
            print(f"frequency:                {results[16]}")
            print(f"consumption_Current:      {results[17]}")
            print(f"production_Current:       {results[18]}")
            print("--Phase L2 values--")
            print(f"production:               {results[19]}")
            print(f"consumption:              {results[20]}")
            print(f"net_consumption:          {results[21]}")
            print(f"daily_production:         {results[22]}")
            print(f"daily_consumption:        {results[23]}")
            print(f"lifetime_production:      {results[24]}")
            print(f"lifetime_net_production:  {results[25]}")
            print(f"lifetime_consumption:     {results[26]}")
            print(f"lifetime_net_consumption: {results[27]}")
            print(f"pf:                       {results[28]}")
            print(f"voltage:                  {results[29]}")
            print(f"frequency:                {results[30]}")
            print(f"consumption_Current:      {results[31]}")
            print(f"production_Current:       {results[32]}")
            print(f"grid_status:              {results[33]}")
            print(f"active_inverters:         {results[34]}")
            if "401" in str(data_results):
                print(
                    "inverters_production:    Unable to retrieve inverter data - Authentication failure"
                )
            elif results[12] is None:
                print(
                    "inverters_production:    Inverter data not available for your Envoy device."
                )
            else:
                print(f"inverters_production:     {results[12]}")
            if dumpraw:
                print(f"envoy_info:              {json.dumps(results[13],indent=2)}")


if __name__ == "__main__":
    SECURE = ""

    parser = argparse.ArgumentParser(
        description="Retrieve energy information from the Enphase Envoy device."
    )
    parser.add_argument(
        "-u", "--user", dest="username", help="Username (Envoy or Enphase)"
    )
    parser.add_argument(
        "-p", "--pass", dest="password", help="Password (Envoy or Enphase)"
    )
    parser.add_argument(
        "-o",
        "--ownertoken",
        dest="ownertoken",
        help="Use Enphase owner token from enlighten",
        action='store_true'
    )
    parser.add_argument(
        "-s",
        "--serialnum",
        dest="enlighten_serial_num",
        help="Envoy Serial Number. Needed to get Token from Enphase",
    )
    parser.add_argument(
        "-i",
        "--ipaddress",
        dest="host_ip",
        help="Envoy IP address.",
    )
    parser.add_argument(
        "-r",
        "--rawdump",
        dest="rawdump",
        help="Dump raw json content of envoy info",
        action='store_true'
    )
    parser.add_argument(
        "-d",
        "--debuglog",
        dest="debuglog",
        help="Enable Debug log output",
        action='store_true'
    )
    parser.add_argument(
        "-n",
        "--number",
        dest="loopcount",
        help="NUmber of loops to executet",
    )
    parser.add_argument(
        "-w",
        "--waittime",
        dest="waittime",
        help="TIme to wait between loops [sec]",
    )


    args = parser.parse_args()

    if args.debuglog:
        _LOGGER.setLevel(logging.DEBUG)
        _LOGGER.addHandler(logging.StreamHandler(sys.stdout))

    if args.host_ip is None:
        HOST = input(
            "Enter the Envoy IP address or host name, "
            + "or press enter to use 'envoy' as default: "
        )
    else:
        HOST = args.host_ip 

    if args.username is None:
        USERNAME = input(
            "Enter the Username for Enphase site or Envoy, "
            + "or press enter to use 'envoy' as default: "
        )
    else:
        USERNAME = args.username

    if args.password is None:
        PASSWORD = getpass.getpass(
            "Enter the Password for Enphase site or Envoy, "
            + "or press enter to use the default password: "
        )
    else:
        PASSWORD = args.password

    if (
        args.username is None
        and args.password is None
        and args.ownertoken == False
        and USERNAME != ""
        and PASSWORD != ""
    ):
        OWNERTOKEN = (input(
            "Use Token from Enphase to login to Envoy (Y/N):"
        ).lower()[0]=="y")
    else:
        OWNERTOKEN = args.ownertoken

    if OWNERTOKEN and args.enlighten_serial_num is None:
        SERIALNUM = input(
            "Enter the Envoy serialnumber: "
        )
    else:
        SERIALNUM = args.enlighten_serial_num

    if OWNERTOKEN:
        SECURE = "s"
    else:
        SECURE = ""

    if HOST == "":
        HOST = "envoy"

    if USERNAME == "":
        USERNAME = "envoy"

    LOOPCOUNT = 1
    if (args.loopcount is not None):
        LOOPCOUNT = int(args.loopcount)
    
    WAITTIME = 1
    if (args.waittime is not None):
        WAITTIME = int(args.waittime)
 
    _LOGGER.debug("Host %s",HOST)
    _LOGGER.debug("Username %s",USERNAME)
    _LOGGER.debug("Password specified %s",PASSWORD!="")
    _LOGGER.debug("serialnum %s",SERIALNUM)
    _LOGGER.debug("Secure %s",SECURE)
    _LOGGER.debug("Loopcount %s",LOOPCOUNT)
    _LOGGER.debug("waittime %s",WAITTIME)

    TESTREADER = EnvoyReader(
        HOST,
        username=USERNAME,
        password=PASSWORD,
        enlighten_user=USERNAME,
        enlighten_pass=PASSWORD,
        inverters=True,
        enlighten_serial_num=SERIALNUM,
        https_flag=SECURE,
        use_enlighten_owner_token=OWNERTOKEN,
    )

    TESTREADER.run_in_console(args.rawdump,LOOPCOUNT,WAITTIME)