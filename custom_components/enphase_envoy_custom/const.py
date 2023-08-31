"""The enphase_envoy component."""

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntityDescription
)

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass

)
from homeassistant.const import (
    UnitOfEnergy, 
    UnitOfPower, 
    UnitOfElectricPotential,
    UnitOfFrequency,
    Platform, 
    PERCENTAGE
)

DOMAIN = "enphase_envoy"

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]

ICON = "mdi:flash"

COORDINATOR = "coordinator"
NAME = "name"

DEFAULT_SCAN_INTERVAL = 60  # default in seconds

CONF_SERIAL = "serial"
CONF_USE_ENLIGHTEN = "use_enlighten"

SENSORS = (
    SensorEntityDescription(
        key="production",
        name="Current Power Production",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="daily_production",
        name="Today's Energy Production",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
    ),
    SensorEntityDescription(
        key="seven_days_production",
        name="Last Seven Days Energy Production",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL,
        device_class=SensorDeviceClass.ENERGY,
    ),
    SensorEntityDescription(
        key="lifetime_production",
        name="Lifetime Energy Production",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
    ),
    SensorEntityDescription(
        key="consumption",
        name="Current Power Consumption",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="daily_consumption",
        name="Today's Energy Consumption",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
    ),
    SensorEntityDescription(
        key="seven_days_consumption",
        name="Last Seven Days Energy Consumption",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL,
        device_class=SensorDeviceClass.ENERGY,
    ),
    SensorEntityDescription(
        key="lifetime_consumption",
        name="Lifetime Energy Consumption",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
    ),
    SensorEntityDescription(
        key="inverters",
        name="Inverter",
        native_unit_of_measurement=UnitOfPower.WATT,
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
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL,
        device_class=SensorDeviceClass.ENERGY
    ),
    SensorEntityDescription(
        key="import_index",
        name="Index Import",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
    ),
    SensorEntityDescription(
        key="export_index",
        name="Index Export",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
    ),
    SensorEntityDescription(
        key="current_pf",
        name="Current Power Factor",
        device_class=SensorDeviceClass.POWER_FACTOR,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="current_voltage",
        name="Current Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="current_frequency",
        name="Current Frequency",
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        device_class=SensorDeviceClass.FREQUENCY,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="current_amps",
        name="Current Amps",
        Unit_of_measurement="A",
        device_class=SensorDeviceClass.CURRENT,
        entity_registry_enabled_default=False,
    ),
)

BINARY_SENSORS = (
    BinarySensorEntityDescription(
        key="grid_status",
        name="Grid Status",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
    ),
)

PHASE_SENSORS = (
    SensorEntityDescription(
        key="production_l1",
        name="Current Power Production L1",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="daily_production_l1",
        name="Today's Energy Production L1",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
    ),
    SensorEntityDescription(
        key="lifetime_production_l1",
        name="Lifetime Energy Production L1",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
    ),
    SensorEntityDescription(
        key="production_l2",
        name="Current Power Production L2",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="daily_production_l2",
        name="Today's Energy Production L2",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
    ),
    SensorEntityDescription(
        key="lifetime_production_l2",
        name="Lifetime Energy Production L2",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
    ),
    SensorEntityDescription(
        key="production_l3",
        name="Current Power Production L3",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="daily_production_l3",
        name="Today's Energy Production L3",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
    ),
    SensorEntityDescription(
        key="lifetime_production_l3",
        name="Lifetime Energy Production L3",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
    ),
    SensorEntityDescription(
        key="consumption_l1",
        name="Current Power Consumption L1",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="daily_consumption_l1",
        name="Today's Energy Consumption L1",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
    ),
    SensorEntityDescription(
        key="lifetime_consumption_l1",
        name="Lifetime Energy Consumption L1",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
    ),
    SensorEntityDescription(
        key="consumption_l2",
        name="Current Power Consumption L2",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="daily_consumption_l2",
        name="Today's Energy Consumption L2",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
    ),
    SensorEntityDescription(
        key="lifetime_consumption_l2",
        name="Lifetime Energy Consumption L2",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
    ),
    SensorEntityDescription(
        key="consumption_l3",
        name="Current Power Consumption L3",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="daily_consumption_l3",
        name="Today's Energy Consumption L3",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
    ),
    SensorEntityDescription(
        key="lifetime_consumption_l3",
        name="Lifetime Energy Consumption L3",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
    ),
    SensorEntityDescription(
        key="import_index_l1",
        name="Index Import L1",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
    ),
    SensorEntityDescription(
        key="export_index_l1",
        name="Index Export L1",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
    ),
    SensorEntityDescription(
        key="import_index_l2",
        name="Index Import L2",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
    ),
    SensorEntityDescription(
        key="export_index_l2",
        name="Index Export L2",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
    ),
    SensorEntityDescription(
        key="import_index_l3",
        name="Index Import L3",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
    ),
    SensorEntityDescription(
        key="export_index_l3",
        name="Index Export L3",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
    ),
    SensorEntityDescription(
        key="current_pf_l1",
        name="Current Power Factor L1",
        device_class=SensorDeviceClass.POWER_FACTOR,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="current_pf_l2",
        name="Current Power Factor L2",
        device_class=SensorDeviceClass.POWER_FACTOR,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="current_pf_l3",
        name="Current Power Factor L3",
        device_class=SensorDeviceClass.POWER_FACTOR,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="current_voltage_l1",
        name="Current Voltage L1",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="current_voltage_l2",
        name="Current Voltage L2",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="current_voltage_l3",
        name="Current Voltage L3",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="current_frequency_l1",
        name="Current Frequency L1",
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        device_class=SensorDeviceClass.FREQUENCY,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="current_frequency_l2",
        name="Current Frequency L2",
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        device_class=SensorDeviceClass.FREQUENCY,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="current_frequency_l3",
        name="Current Frequency L3",
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        device_class=SensorDeviceClass.FREQUENCY,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="current_amps_l1",
        name="Current Amps L1",
        Unit_of_measurement="A",
        device_class=SensorDeviceClass.CURRENT,
        entity_registry_enabled_default=False,
    ),
     SensorEntityDescription(
        key="current_amps_l2",
        name="Current Amps L2",
        Unit_of_measurement="A",
        device_class=SensorDeviceClass.CURRENT,
        entity_registry_enabled_default=False,
    ),
     SensorEntityDescription(
        key="current_amps_l3",
        name="Current Amps L3",
        Unit_of_measurement="A",
        device_class=SensorDeviceClass.CURRENT,
        entity_registry_enabled_default=False,
    ),

)

BATTERY_ENERGY_DISCHARGED_SENSOR = SensorEntityDescription(
    key="battery_energy_discharged",
    name="Battery Energy Discharged",
    native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
    state_class=SensorStateClass.TOTAL,
    device_class=SensorDeviceClass.ENERGY
)

BATTERY_ENERGY_CHARGED_SENSOR = SensorEntityDescription(
    key="battery_energy_charged",
    name="Battery Energy Charged",
    native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
    state_class=SensorStateClass.TOTAL,
    device_class=SensorDeviceClass.ENERGY
)
