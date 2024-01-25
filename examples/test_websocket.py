import json

import websocket

host = '192.168.221.169'


def on_message(ws, message):
    print(f"Received message: {message}")


def on_error(ws, error):
    print(f"Encountered an error: {error}")


def on_close(ws):
    print("WebSocket connection closed")


def on_open(ws):
    msg = {"cmd": "set", "dev": "owbus", "circuit": "OWFS", "do_reset": True}
    # msg = {"cmd": "filter", "devices": ["ao", "input"]}
    ws.send(json.dumps(msg))


if __name__ == "__main__":
    ws = websocket.WebSocketApp(f"ws://{host}/ws",
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close)
    ws.on_open = on_open
    ws.run_forever()
