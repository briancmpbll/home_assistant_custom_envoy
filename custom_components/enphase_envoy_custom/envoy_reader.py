"""Module to read production and consumption values from an Enphase Envoy on the local network."""
import argparse
import asyncio
import datetime
import logging
import jwt
import re
import time
from json.decoder import JSONDecodeError

import httpx
import xmltodict
from envoy_utils.envoy_utils import EnvoyUtils
from homeassistant.util.network import is_ipv6_address
import xmltodict

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

ENDPOINT_URL_PRODUCTION_JSON = "http{}://{}/production.json?details=1"
ENDPOINT_URL_PRODUCTION_V1 = "http{}://{}/api/v1/production"
ENDPOINT_URL_PRODUCTION_INVERTERS = "http{}://{}/api/v1/production/inverters"
ENDPOINT_URL_PRODUCTION = "http{}://{}/production"
ENDPOINT_URL_CHECK_JWT = "https://{}/auth/check_jwt"
ENDPOINT_URL_ENSEMBLE_INVENTORY = "http{}://{}/ivp/ensemble/inventory"
ENDPOINT_URL_HOME_JSON = "http{}://{}/home.json"
ENDPOINT_URL_INFO_XML = "http{}://{}/info"
ENDPOINT_URL_METERS = "http{}://{}/ivp/meters/readings"

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
    
    message_import_export_not_available = (
        "Import Export data not available for your Envoy device."
    )

    message_consumption_not_available = (
        "Consumption data not available for your Envoy device."
    )

    message_grid_status_not_available = (
        "Grid status not available for your Envoy device."
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
    ):
        """Init the EnvoyReader."""
        self.host = host.lower()
        # IPv6 addresses need to be enclosed in brackets
        if is_ipv6_address(self.host):
            self.host = f"[{self.host}]"
        self.username = username
        self.password = password
        self.get_inverters = inverters
        self.endpoint_type = None
        self.has_grid_status = True
        self.serial_number_last_six = None
        self.endpoint_production_json_results = None
        self.endpoint_production_v1_results = None
        self.endpoint_production_inverters = None
        self.endpoint_meters_json_results = None
        self.endpoint_production_results = None
        self.endpoint_ensemble_json_results = None
        self.endpoint_home_json_results = None
        self.isMeteringEnabled = False  # pylint: disable=invalid-name
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
        self.info_refresh_buffer_seconds = info_refresh_buffer_seconds
        self.info_next_refresh_time = datetime.datetime.now()
        self._store = store
        self._store_data = {}
        self._store_update_pending = False

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

    async def _update(self):
        """Update the data."""
        if self.endpoint_type == ENVOY_MODEL_S:
            await self._update_from_pc_endpoint()
        if self.endpoint_type == ENVOY_MODEL_C or (
            self.endpoint_type == ENVOY_MODEL_S and not self.isMeteringEnabled
        ):
            await self._update_from_p_endpoint()
        if self.endpoint_type == ENVOY_MODEL_LEGACY:
            await self._update_from_p0_endpoint()
            
        await self._update_info_endpoint()

    async def _update_from_pc_endpoint(self):
        """Update from PC endpoint."""
        await self._update_endpoint(
            "endpoint_production_json_results", ENDPOINT_URL_PRODUCTION_JSON
        )
        await self._update_endpoint(
            "endpoint_ensemble_json_results", ENDPOINT_URL_ENSEMBLE_INVENTORY
        )
        await self._update_endpoint(
            "endpoint_meters_json_results", ENDPOINT_URL_METERS
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

    async def _update_info_endpoint(self):
        """Update from info endpoint if next time expried."""
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

    async def _update_endpoint(self, attr, url):
        """Update a property from an endpoint."""
        formatted_url = url.format(self.https_flag, self.host)
        response = await self._async_fetch_with_retry(
            formatted_url, follow_redirects=False
        )
        setattr(self, attr, response)

    async def _async_fetch_with_retry(self, url, **kwargs):
        """Retry 3 times to fetch the url if there is a transport error."""
        for attempt in range(3):
            header = " <Blank Authorization Header> "
            if self._authorization_header:
                header = " <Authorization header with Token hidden> "
            _LOGGER.debug(
                "HTTP GET Attempt #%s: %s: use owner token: %s: Header:%s",
                attempt + 1,
                url,
                self.use_enlighten_owner_token,
                header,
            )
            try:
                async with self.async_client as client:
                    resp = await client.get(
                        url, headers=self._authorization_header, timeout=30, **kwargs
                    )
                    if resp.status_code == 401 and attempt < 2:
                        if self.use_enlighten_owner_token:
                            _LOGGER.debug(
                                "Received 401 from Envoy; refreshing cookies, attempt %s of 2:",
                                attempt+1
                             )
                            could_refresh_cookies = await self._refresh_token_cookies()
                            if not could_refresh_cookies:
                                _LOGGER.debug(
                                    "cookie refresh failed, getting token, attempt %s of 2:",
                                    attempt+1
                                )
                                await self._getEnphaseToken()
                            continue
                        # don't try token and cookies refresh for legacy envoy
                        else:
                            _LOGGER.debug(
                                "Received 401 from Envoy; retrying, attempt %s of 2",
                                attempt+1
                            )
                            continue
                    _LOGGER.debug("Fetched (%s) from %s: %s: %s",  attempt + 1, url, resp, resp.text)
                    if resp.status_code == 404:
                        return None
                    return resp
            except httpx.TransportError:
                if attempt == 2:
                    raise

    async def _async_post(self, url, data=None, cookies=None, **kwargs):
        _LOGGER.debug("HTTP POST Attempt: %s", url)
        # _LOGGER.debug("HTTP POST Data: %s", data)
        try:
            async with self.async_client as client:
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
        async with self.async_client as client:
            # login to the enlighten website
            payload_login = {
                'user[email]': self.enlighten_user,
                'user[password]': self.enlighten_pass,
            }
            resp = await client.post(ENLIGHTEN_AUTH_URL, data=payload_login, timeout=30)
            if resp.status_code >= 400:
                raise RuntimeError("Could not Authenticate via Enlighten")

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
                raise RuntimeError("Could not get enlighten token")
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
            "Using Model: %s (HTTP%s, Metering enabled: %s, Get Inverters: %s)",
            self.endpoint_type, 
            self.https_flag,
            self.isMeteringEnabled,
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
        if response.status_code == 401:
            if self.endpoint_type in [ENVOY_MODEL_C, ENVOY_MODEL_LEGACY]:
                self.get_inverters = False
                _LOGGER.debug("Error 401 in Getdata for getting invertors, disabling inverters")
            response.raise_for_status()
        self.endpoint_production_inverters = response
        return

    async def detect_model(self):
        """Method to determine if the Envoy supports consumption values or only production."""
        # If a password was not given as an argument when instantiating
        # the EnvoyReader object than use the last six numbers of the serial
        # number as the password.  Otherwise use the password argument value.
        if self.password == "" and not self.serial_number_last_six:
            await self.get_serial_number()

        try:
            await self._update_from_pc_endpoint()
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
            self.isMeteringEnabled = has_metering_setup(
                self.endpoint_production_json_results.json()
            )
            if not self.isMeteringEnabled:
                await self._update_from_p_endpoint()
            self.endpoint_type = ENVOY_MODEL_S
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

    async def production(self):
        """Running getData() beforehand will set self.enpoint_type and self.isDataRetrieved"""
        """so that this method will only read data from stored variables"""

        if self.endpoint_type == ENVOY_MODEL_S:
            raw_json = self.endpoint_production_json_results.json()
            idx = 1 if self.isMeteringEnabled else 0
            production = raw_json["production"][idx]["wNow"]
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
        """Running getData() beforehand will set self.enpoint_type and self.isDataRetrieved"""
        """so that this method will only read data from stored variables"""
        phase_map = {"production_l1": 0, "production_l2": 1, "production_l3": 2}

        if self.endpoint_type == ENVOY_MODEL_S:
            raw_json = self.endpoint_production_json_results.json()
            idx = 1 if self.isMeteringEnabled else 0
            try:
                return int(
                    raw_json["production"][idx]["lines"][phase_map[phase]]["wNow"]
                )
            except (KeyError, IndexError):
                return None

        return None

    async def consumption(self):
        """Running getData() beforehand will set self.enpoint_type and self.isDataRetrieved"""
        """so that this method will only read data from stored variables"""

        """Only return data if Envoy supports Consumption"""
        if self.endpoint_type in [ENVOY_MODEL_C,ENVOY_MODEL_LEGACY]:
            return self.message_consumption_not_available

        raw_json = self.endpoint_production_json_results.json()
        consumption = raw_json["consumption"][0]["wNow"]
        return int(consumption)

    async def consumption_phase(self, phase):
        """Running getData() beforehand will set self.enpoint_type and self.isDataRetrieved"""
        """so that this method will only read data from stored variables"""
        phase_map = {"consumption_l1": 0, "consumption_l2": 1, "consumption_l3": 2}

        """Only return data if Envoy supports Consumption"""
        if self.endpoint_type in [ENVOY_MODEL_C,ENVOY_MODEL_LEGACY]:
            return None

        raw_json = self.endpoint_production_json_results.json()
        try:
            return int(raw_json["consumption"][0]["lines"][phase_map[phase]]["wNow"])
        except (KeyError, IndexError):
            return None

    async def daily_production(self):
        """Running getData() beforehand will set self.enpoint_type and self.isDataRetrieved"""
        """so that this method will only read data from stored variables"""

        if self.endpoint_type == ENVOY_MODEL_S and self.isMeteringEnabled:
            raw_json = self.endpoint_production_json_results.json()
            daily_production = raw_json["production"][1]["whToday"]
        elif self.endpoint_type == ENVOY_MODEL_C or (
            self.endpoint_type == ENVOY_MODEL_S and not self.isMeteringEnabled
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
        """Running getData() beforehand will set self.enpoint_type and self.isDataRetrieved"""
        """so that this method will only read data from stored variables"""
        phase_map = {"daily_production_l1": 0,"daily_production_l2": 1,"daily_production_l3": 2}

        if self.endpoint_type == ENVOY_MODEL_S and self.isMeteringEnabled:
            raw_json = self.endpoint_production_json_results.json()
            try:
                return int(
                    raw_json["production"][1]["lines"][phase_map[phase]]["whToday"]
                )
            except (KeyError, IndexError):
                return None

        return None

    async def daily_consumption(self):
        """Running getData() beforehand will set self.enpoint_type and self.isDataRetrieved"""
        """so that this method will only read data from stored variables"""

        """Only return data if Envoy supports Consumption"""
        if self.endpoint_type in [ENVOY_MODEL_C,ENVOY_MODEL_LEGACY]:
            return self.message_consumption_not_available

        raw_json = self.endpoint_production_json_results.json()
        daily_consumption = raw_json["consumption"][0]["whToday"]
        return int(daily_consumption)

    async def daily_consumption_phase(self, phase):
        """Running getData() beforehand will set self.enpoint_type and self.isDataRetrieved"""
        """so that this method will only read data from stored variables"""
        phase_map = {"daily_consumption_l1": 0,"daily_consumption_l2": 1,"daily_consumption_l3": 2}

        """Only return data if Envoy supports Consumption"""
        if self.endpoint_type in [ENVOY_MODEL_C,ENVOY_MODEL_LEGACY]:
            return None

        raw_json = self.endpoint_production_json_results.json()
        try:
            return int(
                raw_json["consumption"][0]["lines"][phase_map[phase]]["whToday"]
            )
        except (KeyError, IndexError):
            return None

    async def seven_days_production(self):
        """Running getData() beforehand will set self.enpoint_type and self.isDataRetrieved"""
        """so that this method will only read data from stored variables"""

        if self.endpoint_type == ENVOY_MODEL_S and self.isMeteringEnabled:
            raw_json = self.endpoint_production_json_results.json()
            seven_days_production = raw_json["production"][1]["whLastSevenDays"]
        elif self.endpoint_type == ENVOY_MODEL_C or (
            self.endpoint_type == ENVOY_MODEL_S and not self.isMeteringEnabled
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
        """Running getData() beforehand will set self.enpoint_type and self.isDataRetrieved"""
        """so that this method will only read data from stored variables"""

        """Only return data if Envoy supports Consumption"""
        if self.endpoint_type in [ENVOY_MODEL_C,ENVOY_MODEL_LEGACY]:
            return self.message_consumption_not_available

        raw_json = self.endpoint_production_json_results.json()
        seven_days_consumption = raw_json["consumption"][0]["whLastSevenDays"]
        return int(seven_days_consumption)

    async def lifetime_production(self):
        """Running getData() beforehand will set self.enpoint_type and self.isDataRetrieved"""
        """so that this method will only read data from stored variables"""

        if self.endpoint_type == ENVOY_MODEL_S:
            raw_json = self.endpoint_production_json_results.json()
            idx = 1 if self.isMeteringEnabled else 0
            lifetime_production = raw_json["production"][idx]["whLifetime"]
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
        """Running getData() beforehand will set self.enpoint_type and self.isDataRetrieved"""
        """so that this method will only read data from stored variables"""
        phase_map = {"lifetime_production_l1": 0,"lifetime_production_l2": 1,"lifetime_production_l3": 2}

        if self.endpoint_type == ENVOY_MODEL_S and self.isMeteringEnabled:
            raw_json = self.endpoint_production_json_results.json()

            try:
                return int(
                    raw_json["production"][1]["lines"][phase_map[phase]]["whLifetime"]
                )
            except (KeyError, IndexError):
                return None

        return None

    async def lifetime_consumption(self):
        """Running getData() beforehand will set self.enpoint_type and self.isDataRetrieved"""
        """so that this method will only read data from stored variables"""

        """Only return data if Envoy supports Consumption"""
        if self.endpoint_type in [ENVOY_MODEL_C,ENVOY_MODEL_LEGACY]:
            return self.message_consumption_not_available

        raw_json = self.endpoint_production_json_results.json()
        lifetime_consumption = raw_json["consumption"][0]["whLifetime"]
        return int(lifetime_consumption)

    async def lifetime_consumption_phase(self, phase):
        """Running getData() beforehand will set self.enpoint_type and self.isDataRetrieved"""
        """so that this method will only read data from stored variables"""
        phase_map = {"lifetime_consumption_l1": 0,"lifetime_consumption_l2": 1,"lifetime_consumption_l3": 2}

        """Only return data if Envoy supports Consumption"""
        if self.endpoint_type in [ENVOY_MODEL_C,ENVOY_MODEL_LEGACY]:
            return None

        raw_json = self.endpoint_production_json_results.json()
        try:
            return int(
                raw_json["consumption"][0]["lines"][phase_map[phase]]["whLifetime"]
            )
        except (KeyError, IndexError):
            return None

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

    async def import_index(self):
        """import index"""
        """Running getData() beforehand will set self.enpoint_type and self.isDataRetrieved"""
        """so that this method will only read data from stored variables"""
        if self.endpoint_type in [ENVOY_MODEL_C,ENVOY_MODEL_LEGACY]:
            return self.message_import_export_not_available
        
        raw_json = self.endpoint_meters_json_results.json()
        index_imp = raw_json[1]["actEnergyDlvd"]
        return int(index_imp)

    async def import_index_phase(self, phase):
        """import index"""
        """Running getData() beforehand will set self.enpoint_type and self.isDataRetrieved"""
        """so that this method will only read data from stored variables"""
        phase_map = {"import_index_l1": 0, "import_index_l2": 1, "import_index_l3": 2}
        if self.endpoint_type in [ENVOY_MODEL_C,ENVOY_MODEL_LEGACY]:
            return self.message_import_export_not_available
        
        raw_json = self.endpoint_meters_json_results.json()
        try:
            return int(
                raw_json[1]["channels"][phase_map[phase]]["actEnergyDlvd"]
            )
        except (KeyError, IndexError):
            return None

        return None

    async def export_index(self):
        """import export"""
        """Running getData() beforehand will set self.enpoint_type and self.isDataRetrieved"""
        """so that this method will only read data from stored variables"""
        
        if self.endpoint_type in [ENVOY_MODEL_C,ENVOY_MODEL_LEGACY]:
            return self.message_import_export_not_available
        
        raw_json = self.endpoint_meters_json_results.json()
        index_exp = raw_json[1]['actEnergyRcvd']
        return int(index_exp)

    async def export_index_phase(self, phase):
        """import export"""
        """Running getData() beforehand will set self.enpoint_type and self.isDataRetrieved"""
        """so that this method will only read data from stored variables"""
        phase_map = {"export_index_l1": 0, "export_index_l2": 1, "export_index_l3": 2}
        
        if self.endpoint_type in [ENVOY_MODEL_C,ENVOY_MODEL_LEGACY]:
            return self.message_import_export_not_available
        
        raw_json = self.endpoint_meters_json_results.json()
        try:
            return int(
                raw_json[1]["channels"][phase_map[phase]]["actEnergyRcvd"]
            )
        except (KeyError, IndexError):
            return None

    return None

    async def grid_status(self):
        """Return grid status reported by Envoy"""
        if self.has_grid_status and self.endpoint_home_json_results is not None:
            if self.endpoint_production_json_results.status_code == 200:
                home_json = self.endpoint_home_json_results.json()
                if ("enpower" in home_json.keys() and "grid_status" in home_json["enpower"].keys()):
                    return home_json["enpower"]["grid_status"]
        self.has_grid_status = False
        return None

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
        device_data["Using-MeteringEnabled"] = self.isMeteringEnabled
        device_data["Using-GetInverters"] = self.get_inverters
        device_data["Using-UseEnligthen"] = self.use_enlighten_owner_token
        device_data["Using-InfoUpdateInterval"] = self.info_refresh_buffer_seconds
        device_data["Using-hasgridstatus"] = self.has_grid_status

        return device_data

    def run_in_console(self):
        """If running this module directly, print all the values in the console."""
        print("Reading...")
        loop = asyncio.get_event_loop()
        data_results = loop.run_until_complete(
            asyncio.gather(self.getData(), return_exceptions=False)
        )

        loop = asyncio.get_event_loop()
        results = loop.run_until_complete(
            asyncio.gather(
                self.production(),
                self.consumption(),
                self.daily_production(),
                self.daily_consumption(),
                self.seven_days_production(),
                self.seven_days_consumption(),
                self.lifetime_production(),
                self.lifetime_consumption(),
                self.import_index(),
                self.export_index(),
                self.inverters_production(),
                self.battery_storage(),
                return_exceptions=False,
            )
        )

        print(f"production:              {results[0]}")
        print(f"consumption:             {results[1]}")
        print(f"daily_production:        {results[2]}")
        print(f"daily_consumption:       {results[3]}")
        print(f"seven_days_production:   {results[4]}")
        print(f"seven_days_consumption:  {results[5]}")
        print(f"lifetime_production:     {results[6]}")
        print(f"lifetime_consumption:    {results[7]}")
        print(f"index_import:            {results[8]}")
        print(f"index_export:            {results[9]}")
        if "401" in str(data_results):
            print(
                "inverters_production:    Unable to retrieve inverter data - Authentication failure"
            )
        elif results[10] is None:
            print(
                "inverters_production:    Inverter data not available for your Envoy device."
            )
        else:
            print(f"inverters_production:    {results[10]}")
        print(f"battery_storage:         {results[11]}")


if __name__ == "__main__":
    SECURE = ""

    parser = argparse.ArgumentParser(
        description="Retrieve energy information from the Enphase Envoy device."
    )
    parser.add_argument(
        "-u", "--user", dest="enlighten_user", help="Enlighten Username"
    )
    parser.add_argument(
        "-p", "--pass", dest="enlighten_pass", help="Enlighten Password"
    )
    parser.add_argument(
        "-c",
        "--comissioned",
        dest="commissioned",
        help="Commissioned Envoy (True/False)",
    )
    parser.add_argument(
        "-o",
        "--ownertoken",
        dest="ownertoken",
        help="use the 6 month owner token  from enlighten instead of the 1hr entrez token",
        action='store_true'
    )
    parser.add_argument(
        "-i",
        "--siteid",
        dest="enlighten_site_id",
        help="Enlighten Site ID. Only used when Commissioned=True.",
    )
    parser.add_argument(
        "-s",
        "--serialnum",
        dest="enlighten_serial_num",
        help="Enlighten Envoy Serial Number. Only used when Commissioned=True.",
    )
    args = parser.parse_args()

    if (
        args.enlighten_user is not None
        and args.enlighten_pass is not None
        and args.commissioned is not None
    ):
        SECURE = "s"

    HOST = input(
        "Enter the Envoy IP address or host name, "
        + "or press enter to use 'envoy' as default: "
    )

    USERNAME = input(
        "Enter the Username for Inverter data authentication, "
        + "or press enter to use 'envoy' as default: "
    )

    PASSWORD = input(
        "Enter the Password for Inverter data authentication, "
        + "or press enter to use the default password: "
    )

    if HOST == "":
        HOST = "envoy"

    if USERNAME == "":
        USERNAME = "envoy"

    if PASSWORD == "":
        TESTREADER = EnvoyReader(
            HOST,
            USERNAME,
            inverters=True,
            enlighten_user=args.enlighten_user,
            enlighten_pass=args.enlighten_pass,
            commissioned=args.commissioned,
            enlighten_site_id=args.enlighten_site_id,
            enlighten_serial_num=args.enlighten_serial_num,
            https_flag=SECURE,
            use_enlighten_owner_token=args.ownertoken
        )
    else:
        TESTREADER = EnvoyReader(
            HOST,
            USERNAME,
            PASSWORD,
            inverters=True,
            enlighten_user=args.enlighten_user,
            enlighten_pass=args.enlighten_pass,
            commissioned=args.commissioned,
            enlighten_site_id=args.enlighten_site_id,
            enlighten_serial_num=args.enlighten_serial_num,
            https_flag=SECURE,
            use_enlighten_owner_token=args.ownertoken
        )

    TESTREADER.run_in_console()
