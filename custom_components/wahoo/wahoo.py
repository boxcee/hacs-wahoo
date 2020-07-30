import asyncio
import requests
import json
import websocket
import logging


WAHOO_WSS: str = "wss://mb.wahooligan.com/faye"
WAHOO_HTTPS: str = "https://mb.wahooligan.com/faye"

_LOGGER = logging.getLogger(__name__)


class Wahoo:
    def __init__(self, live_url):
        """Initialize."""
        self.tracking_id = get_tracking_id(live_url)
        self.ws = websocket.create_connection(WAHOO_WSS)
        self.client_id = None

    def subscribe_to_live_tracking(self):
        message: list = [
            {
                "channel": "/meta/subscribe",
                "clientId": self.client_id,
                "subscription": f"/livetrack/{self.tracking_id}",
            }
        ]

        self.ws.send(json.dumps(message))
        ws_response = self.ws.recv()
        _LOGGER.debug(ws_response)

    def get_workout_status(self):
        if self.client_id is None:
            self.client_id = get_client_id()
            self.subscribe_to_live_tracking()

        message: list = [
            {
                "channel": "/meta/connect",
                "clientId": self.client_id,
                "connectionType": "websocket",
            }
        ]

        self.ws.send(json.dumps(message))
        ws_response = self.ws.recv()
        _LOGGER.debug(ws_response)

        json_response = json.loads(ws_response)
        return json_response[0].get("data", {})


def parse_jsonp(jsonp) -> dict:
    try:
        l_index = jsonp.index("(") + 1
        r_index = jsonp.rindex(")")
    except ValueError:
        return jsonp

    return jsonp[l_index:r_index]


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
