from homeassistant.core import Config, HomeAssistant


def setup(hass: HomeAssistant, config: Config):
    hass.states.set("hello_state.world", "Paulus")
    return True
