from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.entity import DeviceInfo

from .const import COORDINATOR, DOMAIN, NAME, GRID_STATUS_BINARY_SENSOR, ICON

async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
  data = hass.data[DOMAIN][config_entry.entry_id]
  coordinator = data[COORDINATOR]
  name = data[NAME]

  entities = []
  if (coordinator.data.get("grid_status") is not None):
    entities.append(
        EnvoyGridStatusEntity(
            GRID_STATUS_BINARY_SENSOR,
            GRID_STATUS_BINARY_SENSOR.name,
            name,
            config_entry.unique_id,
            None,
            coordinator,
        )
    )

  async_add_entities(entities)


class EnvoyGridStatusEntity(CoordinatorEntity, BinarySensorEntity):
  def __init__(
      self,
      description,
      name,
      device_name,
      device_serial_number,
      serial_number,
      coordinator,
  ):
      self.entity_description = description
      self._name = name
      self._serial_number = serial_number
      self._device_name = device_name
      self._device_serial_number = device_serial_number
      CoordinatorEntity.__init__(self, coordinator)

  @property
  def icon(self):
      """Icon to use in the frontend, if any."""
      return ICON

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
  def device_info(self) -> DeviceInfo or None:
      """Return the device_info of the device."""
      if not self._device_serial_number:
          return None
      return DeviceInfo(
          identifiers={(DOMAIN, str(self._device_serial_number))},
          manufacturer="Enphase",
          model="Envoy",
          name=self._device_name,
      )

  @property
  def is_on(self) -> bool:
      """Return the status of the requested attribute."""
      return self.coordinator.data.get("grid_status") == "closed"
