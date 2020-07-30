import asyncio
from datetime import timedelta
import logging
import json

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Config, HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from custom_components.wahoo.wahoo import Wahoo
from websocket import WebSocket, WebSocketApp, enableTrace
import requests

from custom_components.wahoo.const import (
    CONF_LIVE_URL,
    DOMAIN,
    PLATFORMS,
    STARTUP_MESSAGE,
)

SCAN_INTERVAL = timedelta(seconds=30)

WAHOO_WSS: str = "wss://mb.wahooligan.com/faye"
WAHOO_HTTPS: str = "https://mb.wahooligan.com/faye"
WAHOO_SUBSCRIPTION_CHANNEL: str = "/meta/subscribe"
WAHOO_CONNECTION_CHANNEL: str = "/meta/connect"

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: Config):
    """Set up this integration using YAML."""
    if hass.data.get(DOMAIN) is None:
        hass.data.setdefault(DOMAIN, {})
        _LOGGER.info(STARTUP_MESSAGE)

    # live_url = config.get(DOMAIN).get(CONF_LIVE_URL)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up this integration using UI."""
    if hass.data.get(DOMAIN) is None:
        hass.data.setdefault(DOMAIN, {})
        _LOGGER.info(STARTUP_MESSAGE)

    live_url = entry.data.get(CONF_LIVE_URL)

    coordinator = WahooDataUpdateCoordinator(hass, live_url=live_url)
    await coordinator.async_refresh()

    if not coordinator.last_update_success:
        raise ConfigEntryNotReady

    hass.data[DOMAIN][entry.entry_id] = coordinator

    for platform in PLATFORMS:
        if entry.options.get(platform, True):
            coordinator.platforms.append(platform)
            hass.async_add_job(
                hass.config_entries.async_forward_entry_setup(entry, platform)
            )

    entry.add_update_listener(async_reload_entry)
    return True


class WahooDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    def __init__(self, hass, live_url):
        """Initialize."""
        enableTrace(True)
        self.websocket_app = WebSocketApp(
            WAHOO_WSS,
            on_error=self.on_error(),
            on_close=self.on_close(),
            on_message=self.on_message(),
        )
        self.client_id = get_client_id()
        self.tracking_id = get_tracking_id(live_url)
        self.websocket_app.on_open = self.on_open()
        self.websocket_app.run_forever()
        self.platforms = []

        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=SCAN_INTERVAL)

    def on_error(self):
        def on_error(ws, error):
            _LOGGER.debug("on_error")

        return on_error

    def on_close(self):
        def on_close(ws):
            _LOGGER.debug("on_close")

        return on_close

    def on_message(self):
        def on_message(ws, message):
            _LOGGER.debug("on_message")

            response = message2json(message)
            if is_subscription_channel(response):
                send_connect(ws, self.client_id)

            _LOGGER.debug(response)

        return on_message

    def on_open(self):
        def on_open(ws):
            _LOGGER.debug("on_open")

            send_subscribe(ws, self.client_id, self.tracking_id)

        return on_open

    async def _async_update_data(self):
        """Update data via library."""
        try:
            return {}
        except Exception as exception:
            raise UpdateFailed(exception)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Handle removal of an entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    unloaded = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, platform)
                for platform in PLATFORMS
                if platform in coordinator.platforms
            ]
        )
    )
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unloaded


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


def get_tracking_id(live_url) -> str:
    parts: list = live_url.split("/")

    return parts[-1]


def get_client_id() -> str:
    message: list = [
        {
            "channel": "/meta/handshake",
            "version": "1.0",
            "supportedConnectionTypes": [
                "websocket",
                "eventsource",
                "long-polling",
                "cross-origin-long-polling",
                "callback-polling",
            ],
            "id": "1",
        }
    ]

    response = requests.get(url=WAHOO_HTTPS, params={"message": json.dumps(message)},)

    json_response: dict = json.loads(parse_jsonp(response.text))

    return json_response[0].get("clientId")


def parse_jsonp(jsonp) -> dict:
    try:
        l_index = jsonp.index("(") + 1
        r_index = jsonp.rindex(")")
    except ValueError:
        return jsonp

    return jsonp[l_index:r_index]


def message2json(message: str) -> dict:
    message_as_json: list = json.loads(message)
    return message_as_json[0]


def is_subscription_channel(message: dict) -> bool:
    return "channel" in message and message.get("channel") == WAHOO_SUBSCRIPTION_CHANNEL


def send_connect(ws: WebSocket, client_id: str):
    message: list = [
        {
            "channel": WAHOO_CONNECTION_CHANNEL,
            "clientId": client_id,
            "connectionType": "websocket",
        }
    ]
    ws.send(json.dumps(message))


def send_subscribe(ws: WebSocket, client_id: str, tracking_id: str):
    message: list = [
        {
            "channel": WAHOO_SUBSCRIPTION_CHANNEL,
            "clientId": client_id,
            "subscription": f"/livetrack/{tracking_id}",
        }
    ]
    ws.send(json.dumps(message))

