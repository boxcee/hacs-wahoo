from homeassistant.core import Config, HomeAssistant


async def async_setup(hass: HomeAssistant, config: Config):
    hass.states.set("hello_state.world", "Paulus")
    return True

