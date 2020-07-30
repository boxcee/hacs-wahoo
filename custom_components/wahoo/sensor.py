"""Sensor platform for Wahoo."""
from custom_components.wahoo.const import DEFAULT_NAME, DOMAIN, ICON, SENSOR
from custom_components.wahoo.entity import WahooEntity


async def async_setup_entry(hass, entry, async_add_devices):
    """Setup sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_devices([WahooSensor(coordinator, entry)])


class WahooSensor(WahooEntity):
    """Wahoo Sensor class."""

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{DEFAULT_NAME}_{SENSOR}"

    @property
    def state(self):
        """Return the state of the sensor."""
        return self.coordinator.data.get("workout_state")

    @property
    def icon(self):
        """Return the icon of the sensor."""
        return ICON
