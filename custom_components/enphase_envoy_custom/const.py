"""The enphase_envoy component."""

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntityDescription
)

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import ENERGY_WATT_HOUR, POWER_WATT, Platform, PERCENTAGE

DOMAIN = "enphase_envoy"

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]

ICON = "mdi:flash"

COORDINATOR = "coordinator"
NAME = "name"

CONF_SERIAL = "serial"
CONF_USE_ENLIGHTEN = "use_enlighten"

SENSORS = (
    SensorEntityDescription(
        key="production",
        name="Current Power Production",
        native_unit_of_measurement=POWER_WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="daily_production",
        name="Today's Energy Production",
        native_unit_of_measurement=ENERGY_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
    ),
    SensorEntityDescription(
        key="seven_days_production",
        name="Last Seven Days Energy Production",
        native_unit_of_measurement=ENERGY_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
    ),
    SensorEntityDescription(
        key="lifetime_production",
        name="Lifetime Energy Production",
        native_unit_of_measurement=ENERGY_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
    ),
    SensorEntityDescription(
        key="consumption",
        name="Current Power Consumption",
        native_unit_of_measurement=POWER_WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="daily_consumption",
        name="Today's Energy Consumption",
        native_unit_of_measurement=ENERGY_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
    ),
    SensorEntityDescription(
        key="seven_days_consumption",
        name="Last Seven Days Energy Consumption",
        native_unit_of_measurement=ENERGY_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
    ),
    SensorEntityDescription(
        key="lifetime_consumption",
        name="Lifetime Energy Consumption",
        native_unit_of_measurement=ENERGY_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
    ),
    SensorEntityDescription(
        key="inverters",
        name="Inverter",
        native_unit_of_measurement=POWER_WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="batteries",
        name="Battery",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.BATTERY
    ),
    SensorEntityDescription(
        key="total_battery_percentage",
        name="Total Battery Percentage",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT
    ),
    SensorEntityDescription(
        key="current_battery_capacity",
        name="Current Battery Capacity",
        native_unit_of_measurement=ENERGY_WATT_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.ENERGY
    ),
)

BATTERY_ENERGY_DISCHARGED_SENSOR = SensorEntityDescription(
    key="battery_energy_discharged",
    name="Battery Energy Discharged",
    native_unit_of_measurement=ENERGY_WATT_HOUR,
    state_class=SensorStateClass.TOTAL,
    device_class=SensorDeviceClass.ENERGY
)

BATTERY_ENERGY_CHARGED_SENSOR = SensorEntityDescription(
    key="battery_energy_charged",
    name="Battery Energy Charged",
    native_unit_of_measurement=ENERGY_WATT_HOUR,
    state_class=SensorStateClass.TOTAL,
    device_class=SensorDeviceClass.ENERGY
)

GRID_STATUS_BINARY_SENSOR = BinarySensorEntityDescription(
    key="grid_status",
    name="Grid Status",
    device_class=BinarySensorDeviceClass.CONNECTIVITY
)
