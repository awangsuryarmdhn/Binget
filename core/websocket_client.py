"""
╔══════════════════════════════════════════════════════════════╗
║  BITGET WEBSOCKET CLIENT                                    ║
║  Real-time market data & private order updates              ║
╚══════════════════════════════════════════════════════════════╝
"""

import json
import time
import hmac
import hashlib
import base64
import threading
import websocket
from typing import Callable, Optional, Dict, List
from rich.console import Console

console = Console()


class BitgetWebSocket:
    """WebSocket client for Bitget real-time data streams."""

    WS_PUBLIC_URL = "wss://ws.bitget.com/spot/v1/stream/public"
    WS_PRIVATE_URL = "wss://ws.bitget.com/spot/v1/stream/private"

    def __init__(self, api_key: str = "", secret_key: str = "", passphrase: str = ""):
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase
        self.ws_public: Optional[websocket.WebSocketApp] = None
        self.ws_private: Optional[websocket.WebSocketApp] = None
        self._callbacks: Dict[str, List[Callable]] = {}
        self._running = False
        self._threads: List[threading.Thread] = []
        self._ping_interval = 30

    def _sign_ws(self) -> dict:
        """Generate login message for private WebSocket."""
        timestamp = str(int(time.time()))
        message = f"{timestamp}GET/user/verify"
        mac = hmac.new(
            self.secret_key.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        )
        sign = base64.b64encode(mac.digest()).decode('utf-8')
        return {
            "op": "login",
            "args": [{
                "apiKey": self.api_key,
                "passphrase": self.passphrase,
                "timestamp": timestamp,
                "sign": sign
            }]
        }

    def on(self, event: str, callback: Callable):
        """Register event callback: ticker, depth, trade, candle, account, order"""
        if event not in self._callbacks:
            self._callbacks[event] = []
        self._callbacks[event].append(callback)

    def _emit(self, event: str, data: dict):
        """Emit event to registered callbacks."""
        for cb in self._callbacks.get(event, []):
            try:
                cb(data)
            except Exception as e:
                console.print(f"[red]WS callback error ({event}): {e}[/red]")

    def _on_public_message(self, ws, message):
        """Handle incoming public WebSocket messages."""
        try:
            data = json.loads(message)
            if "action" in data and "arg" in data:
                channel = data["arg"].get("channel", "")
                if "ticker" in channel:
                    self._emit("ticker", data)
                elif "candle" in channel:
                    self._emit("candle", data)
                elif "depth" in channel:
                    self._emit("depth", data)
                elif "trade" in channel:
                    self._emit("trade", data)
        except json.JSONDecodeError:
            pass

    def _on_private_message(self, ws, message):
        """Handle incoming private WebSocket messages."""
        try:
            data = json.loads(message)
            if "action" in data and "arg" in data:
                channel = data["arg"].get("channel", "")
                if "account" in channel:
                    self._emit("account", data)
                elif "orders" in channel:
                    self._emit("order", data)
            elif data.get("event") == "login" and data.get("code") == 0:
                self._emit("login", data)
        except json.JSONDecodeError:
            pass

    def _on_error(self, ws, error):
        console.print(f"[red]WS Error: {error}[/red]")

    def _on_close(self, ws, close_status_code, close_msg):
        console.print(f"[yellow]WS Closed: {close_msg}[/yellow]")

    def _keep_alive(self, ws):
        """Send ping to keep connection alive."""
        while self._running:
            try:
                ws.send("ping")
                time.sleep(self._ping_interval)
            except Exception:
                break

    def subscribe_public(self, channels: List[dict]):
        """Subscribe to public channels (ticker, depth, candle, trade)."""
        def on_open(ws):
            sub_msg = {"op": "subscribe", "args": channels}
            ws.send(json.dumps(sub_msg))
            # Start keepalive
            t = threading.Thread(target=self._keep_alive, args=(ws,), daemon=True)
            t.start()

        self.ws_public = websocket.WebSocketApp(
            self.WS_PUBLIC_URL,
            on_open=on_open,
            on_message=self._on_public_message,
            on_error=self._on_error,
            on_close=self._on_close
        )
        t = threading.Thread(target=self.ws_public.run_forever, daemon=True)
        t.start()
        self._threads.append(t)

    def subscribe_private(self, channels: List[dict]):
        """Subscribe to private channels (account, orders) - requires auth."""
        def on_open(ws):
            # Login first
            login_msg = self._sign_ws()
            ws.send(json.dumps(login_msg))
            time.sleep(1)
            # Then subscribe
            sub_msg = {"op": "subscribe", "args": channels}
            ws.send(json.dumps(sub_msg))
            # Keepalive
            t = threading.Thread(target=self._keep_alive, args=(ws,), daemon=True)
            t.start()

        self.ws_private = websocket.WebSocketApp(
            self.WS_PRIVATE_URL,
            on_open=on_open,
            on_message=self._on_private_message,
            on_error=self._on_error,
            on_close=self._on_close
        )
        t = threading.Thread(target=self.ws_private.run_forever, daemon=True)
        t.start()
        self._threads.append(t)

    def start(self):
        """Mark WebSocket as running."""
        self._running = True

    def stop(self):
        """Stop all WebSocket connections."""
        self._running = False
        if self.ws_public:
            self.ws_public.close()
        if self.ws_private:
            self.ws_private.close()
