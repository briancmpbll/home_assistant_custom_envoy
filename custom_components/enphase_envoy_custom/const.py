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
        device_class=SensorDeviceClass.POWER,
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
        key="lifetime_net_production",
        name="Lifetime Net Energy Production",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
    ),
    SensorEntityDescription(
        key="consumption",
        name="Current Power Consumption",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
    ),
    SensorEntityDescription(
        key="net_consumption",
        name="Current Net Power Consumption",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
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
        key="lifetime_net_consumption",
        name="Lifetime Net Energy Consumption",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
    ),
    SensorEntityDescription(
        key="inverters",
        name="Inverter",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
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
        key="pf",
        name="Power Factor",
        device_class=SensorDeviceClass.POWER_FACTOR,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="voltage",
        name="Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="frequency",
        name="Frequency",
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        device_class=SensorDeviceClass.FREQUENCY,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="consumption_Current",
        name="Consumption Current",
        native_unit_of_measurement="A",
        device_class=SensorDeviceClass.CURRENT,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="production_Current",
        name="Production Current",
        native_unit_of_measurement="A",
        device_class=SensorDeviceClass.CURRENT,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="active_inverter_count",
        name="Active Inverter Count",
        state_class=SensorStateClass.MEASUREMENT,
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
        device_class=SensorDeviceClass.POWER,
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
        key="lifetime_net_production_l1",
        name="Lifetime Net Energy Production L1",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
    ),
    SensorEntityDescription(
        key="production_l2",
        name="Current Power Production L2",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
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
        key="lifetime_net_production_l2",
        name="Lifetime Net Energy Production L2",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
    ),
    SensorEntityDescription(
        key="production_l3",
        name="Current Power Production L3",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
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
        key="lifetime_net_production_l3",
        name="Lifetime Net Energy Production L3",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
    ),
    SensorEntityDescription(
        key="consumption_l1",
        name="Current Power Consumption L1",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
    ),
    SensorEntityDescription(
        key="net_consumption_l1",
        name="Current Net Power Consumption L1",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
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
        key="lifetime_net_consumption_l1",
        name="Lifetime Net Energy Consumption L1",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
    ),
    SensorEntityDescription(
        key="consumption_l2",
        name="Current Power Consumption L2",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
    ),
    SensorEntityDescription(
        key="net_consumption_l2",
        name="Current Net Power Consumption L2",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
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
        key="lifetime_net_consumption_l2",
        name="Lifetime Net Energy Consumption L2",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
    ),
    SensorEntityDescription(
        key="consumption_l3",
        name="Current Power Consumption L3",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
    ),
    SensorEntityDescription(
        key="net_consumption_l3",
        name="Current Net Power Consumption L3",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
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
        key="lifetime_net_consumption_l3",
        name="Lifetime Net Energy Consumption L3",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
    ),
    SensorEntityDescription(
        key="pf_l1",
        name="Power Factor L1",
        device_class=SensorDeviceClass.POWER_FACTOR,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="pf_l2",
        name="Power Factor L2",
        device_class=SensorDeviceClass.POWER_FACTOR,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="pf_l3",
        name="Power Factor L3",
        device_class=SensorDeviceClass.POWER_FACTOR,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="voltage_l1",
        name="Voltage L1",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="voltage_l2",
        name="Voltage L2",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="voltage_l3",
        name="Voltage L3",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="frequency_l1",
        name="Frequency L1",
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        device_class=SensorDeviceClass.FREQUENCY,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="frequency_l2",
        name="Frequency L2",
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        device_class=SensorDeviceClass.FREQUENCY,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="frequency_l3",
        name="Frequency L3",
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        device_class=SensorDeviceClass.FREQUENCY,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="consumption_Current_l1",
        name="Consumption Current L1",
        native_unit_of_measurement="A",
        device_class=SensorDeviceClass.CURRENT,
        entity_registry_enabled_default=False,
    ),
     SensorEntityDescription(
        key="consumption_Current_l2",
        name="Consumption Current L2",
        native_unit_of_measurement="A",
        device_class=SensorDeviceClass.CURRENT,
        entity_registry_enabled_default=False,
    ),
     SensorEntityDescription(
        key="consumption_Current_l3",
        name="Consumption Current L3",
        native_unit_of_measurement="A",
        device_class=SensorDeviceClass.CURRENT,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="production_Current_l1",
        name="Production Current L1",
        native_unit_of_measurement="A",
        device_class=SensorDeviceClass.CURRENT,
        entity_registry_enabled_default=False,
    ),
     SensorEntityDescription(
        key="production_Current_l2",
        name="Production Current L2",
        native_unit_of_measurement="A",
        device_class=SensorDeviceClass.CURRENT,
        entity_registry_enabled_default=False,
    ),
     SensorEntityDescription(
        key="production_Current_l3",
        name="Production Current L3",
        native_unit_of_measurement="A",
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
