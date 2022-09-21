"""Support for Enphase Envoy solar energy monitor."""
from __future__ import annotations

import datetime

from time import strftime, localtime

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import BATTERY_ENERGY_DISCHARGED_SENSOR, BATTERY_ENERGY_CHARGED_SENSOR, COORDINATOR, DOMAIN, NAME, SENSORS, ICON

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up envoy sensor platform."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    coordinator = data[COORDINATOR]
    name = data[NAME]

    entities = []
    for sensor_description in SENSORS:
        if (sensor_description.key == "inverters"):
            if (coordinator.data.get("inverters_production") is not None):
                for inverter in coordinator.data["inverters_production"]:
                    entity_name = f"{name} {sensor_description.name} {inverter}"
                    split_name = entity_name.split(" ")
                    serial_number = split_name[-1]
                    entities.append(
                        EnvoyInverterEntity(
                            sensor_description,
                            entity_name,
                            name,
                            config_entry.unique_id,
                            serial_number,
                            coordinator,
                        )
                    )
        elif (sensor_description.key == "batteries"):
            if (coordinator.data.get("batteries") is not None):
                for battery in coordinator.data["batteries"]:
                    entity_name = f"{name} {sensor_description.name} {battery}"
                    serial_number = battery
                    entities.append(
                        EnvoyBatteryEntity(
                            sensor_description,
                            entity_name,
                            name,
                            config_entry.unique_id,
                            serial_number,
                            coordinator
                        )
                    )

        elif (sensor_description.key == "current_battery_capacity"):
            if (coordinator.data.get("batteries") is not None):
                battery_capacity_entity = TotalBatteryCapacityEntity(
                    sensor_description,
                    f"{name} {sensor_description.name}",
                    name,
                    config_entry.unique_id,
                    None,
                    coordinator
                )
                entities.append(battery_capacity_entity)

                entities.append(
                    BatteryEnergyChangeEntity(
                        BATTERY_ENERGY_CHARGED_SENSOR,
                        f"{name} {BATTERY_ENERGY_CHARGED_SENSOR.name}",
                        name,
                        config_entry.unique_id,
                        None,
                        battery_capacity_entity,
                        True
                    )
                )

                entities.append(
                    BatteryEnergyChangeEntity(
                        BATTERY_ENERGY_DISCHARGED_SENSOR,
                        f"{name} {BATTERY_ENERGY_DISCHARGED_SENSOR.name}",
                        name,
                        config_entry.unique_id,
                        None,
                        battery_capacity_entity,
                        False
                    )
                )

        elif (sensor_description.key == "total_battery_percentage"):
            if (coordinator.data.get("batteries") is not None):
                entities.append(TotalBatteryPercentageEntity(
                        sensor_description,
                        f"{name} {sensor_description.name}",
                        name,
                        config_entry.unique_id,
                        None,
                        coordinator
                    ))

        else:
            data = coordinator.data.get(sensor_description.key)
            if isinstance(data, str) and "not available" in data:
                continue

            entity_name = f"{name} {sensor_description.name}"
            entities.append(
                CoordinatedEnvoyEntity(
                    sensor_description,
                    entity_name,
                    name,
                    config_entry.unique_id,
                    None,
                    coordinator,
                )
            )

    async_add_entities(entities)

class EnvoyEntity(SensorEntity):
    """Envoy entity"""

    def __init__(
        self,
        description,
        name,
        device_name,
        device_serial_number,
        serial_number,
    ):
        """Initialize Envoy entity."""
        self.entity_description = description
        self._name = name
        self._serial_number = serial_number
        self._device_name = device_name
        self._device_serial_number = device_serial_number

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def unique_id(self):
        """Return the unique id of the sensor."""
        if self._serial_number:
            return self._serial_number
        if self._device_serial_number:
            return f"{self._device_serial_number}_{self.entity_description.key}"

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return ICON

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return None

    @property
    def device_info(self) -> DeviceInfo | None:
        """Return the device_info of the device."""
        if not self._device_serial_number:
            return None
        return DeviceInfo(
            identifiers={(DOMAIN, str(self._device_serial_number))},
            manufacturer="Enphase",
            model="Envoy",
            name=self._device_name,
        )

class CoordinatedEnvoyEntity(EnvoyEntity, CoordinatorEntity):
    def __init__(
        self,
        description,
        name,
        device_name,
        device_serial_number,
        serial_number,
        coordinator,
    ):
        EnvoyEntity.__init__(self, description, name, device_name, device_serial_number, serial_number)
        CoordinatorEntity.__init__(self, coordinator)

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.coordinator.data.get(self.entity_description.key)

class EnvoyInverterEntity(CoordinatedEnvoyEntity):
    """Envoy inverter entity."""

    def __init__(
        self,
        description,
        name,
        device_name,
        device_serial_number,
        serial_number,
        coordinator,
    ):
        super().__init__(
            description=description,
            name=name,
            device_name=device_name,
            device_serial_number=device_serial_number,
            serial_number=serial_number,
            coordinator=coordinator
        )

    @property
    def native_value(self):
        """Return the state of the sensor."""
        if (
            self.coordinator.data.get("inverters_production") is not None
        ):
            return self.coordinator.data.get("inverters_production").get(
                self._serial_number
            )[0]

        return None

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        if (
            self.coordinator.data.get("inverters_production") is not None
        ):
            value = self.coordinator.data.get("inverters_production").get(
                self._serial_number
            )[1]
            return {"last_reported": value}

        return None

class EnvoyBatteryEntity(CoordinatedEnvoyEntity):
    """Envoy battery entity."""

    def __init__(
        self,
        description,
        name,
        device_name,
        device_serial_number,
        serial_number,
        coordinator,
    ):
        super().__init__(
            description=description,
            name=name,
            device_name=device_name,
            device_serial_number=device_serial_number,
            serial_number=serial_number,
            coordinator=coordinator
        )

    @property
    def native_value(self):
        """Return the state of the sensor."""
        if (
            self.coordinator.data.get("batteries") is not None
        ):
            return self.coordinator.data.get("batteries").get(
                self._serial_number
            ).get("percentFull")

        return None

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        if (
            self.coordinator.data.get("batteries") is not None
        ):
            battery = self.coordinator.data.get("batteries").get(
                self._serial_number
            )
            last_reported = strftime(
                "%Y-%m-%d %H:%M:%S", localtime(battery.get("last_rpt_date"))
            )
            return {
                "last_reported": last_reported,
                "capacity": battery.get("encharge_capacity")
            }

        return None

class TotalBatteryCapacityEntity(CoordinatedEnvoyEntity):
    def __init__(
        self,
        description,
        name,
        device_name,
        device_serial_number,
        serial_number,
        coordinator,
    ):
        super().__init__(
            description=description,
            name=name,
            device_name=device_name,
            device_serial_number=device_serial_number,
            serial_number=serial_number,
            coordinator=coordinator
        )

    @property
    def native_value(self):
        """Return the state of the sensor."""
        batteries = self.coordinator.data.get("batteries")
        if (
            batteries is not None
        ):
            total = 0
            for battery in batteries:
                percentage = batteries.get(battery).get("percentFull")
                capacity = batteries.get(battery).get("encharge_capacity")
                total += round(capacity * (percentage / 100.0))

            return total

        return None


class TotalBatteryPercentageEntity(CoordinatedEnvoyEntity):
    def __init__(
        self,
        description,
        name,
        device_name,
        device_serial_number,
        serial_number,
        coordinator,
    ):
        super().__init__(
            description=description,
            name=name,
            device_name=device_name,
            device_serial_number=device_serial_number,
            serial_number=serial_number,
            coordinator=coordinator
        )

    @property
    def native_value(self):
        """Return the state of the sensor."""
        batteries = self.coordinator.data.get("batteries")
        if (
            batteries is not None
        ):
            battery_sum = 0
            for battery in batteries:
                battery_sum += batteries.get(battery).get("percentFull", 0)

            return round(battery_sum / len(batteries), 2)

        return None

class BatteryEnergyChangeEntity(EnvoyEntity):
    def __init__(
        self,
        description,
        name,
        device_name,
        device_serial_number,
        serial_number,
        total_battery_capacity_entity,
        positive: bool
    ):
        super().__init__(
            description=description,
            name=name,
            device_name=device_name,
            device_serial_number=device_serial_number,
            serial_number=serial_number,
        )

        self._sensor_source = total_battery_capacity_entity
        self._positive = positive
        self._state = 0
        self._attr_last_reset = datetime.datetime.now()

    async def async_added_to_hass(self):
        """Handle entity which will be added."""
        await super().async_added_to_hass()

        @callback
        def calc_change(event):
            """Handle the sensor state changes."""
            old_state = event.data.get("old_state")
            new_state = event.data.get("new_state")

            if (
                old_state is None
                or old_state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE)
                or new_state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE)
            ):
                self._state = 0

            else:
                old_state_value = int(old_state.state)
                new_state_value = int(new_state.state)

                if (self._positive):
                    if (new_state_value > old_state_value):
                        self._state = new_state_value - old_state_value
                    else:
                        self._state = 0

                else:
                    if (old_state_value > new_state_value):
                        self._state = old_state_value - new_state_value
                    else:
                        self._state = 0

            self._attr_last_reset = datetime.datetime.now()
            self.async_write_ha_state()

        self.async_on_remove(
            async_track_state_change_event(
                self.hass, self._sensor_source.entity_id, calc_change
            )
        )

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self._state
