"""
╔══════════════════════════════════════════════════════════════╗
║  BITGET REST API CLIENT                                     ║
║  Full spot trading API: Market, Account, Trade, Wallet      ║
╚══════════════════════════════════════════════════════════════╝
"""

import json
import requests
import time
from typing import Optional, Dict, List, Any
from urllib.parse import urlencode
from core.auth import BitgetAuth


class BitgetAPI:
    """Complete Bitget Spot REST API client."""

    BASE_URL = "https://api.bitget.com"

    # ─── API V2 Endpoints ────────────────────────────────
    # Public
    EP_SERVER_TIME   = "/api/v2/public/time"
    EP_COINS         = "/api/v2/spot/public/coins"
    EP_SYMBOLS       = "/api/v2/spot/public/symbols"
    EP_SINGLE_SYMBOL = "/api/v2/spot/public/symbols"

    # Market
    EP_TICKER        = "/api/v2/spot/market/tickers"
    EP_ALL_TICKERS   = "/api/v2/spot/market/tickers"
    EP_RECENT_TRADES = "/api/v2/spot/market/fills"
    EP_CANDLES       = "/api/v2/spot/market/candles"
    EP_DEPTH         = "/api/v2/spot/market/orderbook"
    EP_MERGED_DEPTH  = "/api/v2/spot/market/merge-depth"

    # Account
    EP_API_INFO      = "/api/v2/spot/account/info"
    EP_ASSETS        = "/api/v2/spot/account/assets"
    EP_ASSETS_LITE   = "/api/v2/spot/account/assets"
    EP_BILLS         = "/api/v2/spot/account/bills"

    # Trade
    EP_PLACE_ORDER   = "/api/v2/spot/trade/place-order"
    EP_BATCH_ORDER   = "/api/v2/spot/trade/batch-orders"
    EP_CANCEL_ORDER  = "/api/v2/spot/trade/cancel-order"
    EP_CANCEL_SYMBOL = "/api/v2/spot/trade/cancel-symbol-order"
    EP_ORDER_DETAIL  = "/api/v2/spot/trade/orderInfo"
    EP_OPEN_ORDERS   = "/api/v2/spot/trade/unfilled-orders"
    EP_ORDER_HISTORY = "/api/v2/spot/trade/history-orders"
    EP_FILLS         = "/api/v2/spot/trade/fills"

    # Plan Orders
    EP_PLAN_ORDER       = "/api/v2/spot/trade/place-plan-order"
    EP_MODIFY_PLAN      = "/api/v2/spot/trade/modify-plan-order"
    EP_CANCEL_PLAN      = "/api/v2/spot/trade/cancel-plan-order"
    EP_CURRENT_PLANS    = "/api/v2/spot/trade/current-plan-order"
    EP_HISTORY_PLANS    = "/api/v2/spot/trade/history-plan-order"

    # Wallet
    EP_TRANSFER      = "/api/v2/spot/wallet/transfer"
    EP_DEPOSIT_ADDR  = "/api/v2/spot/wallet/deposit-address"
    EP_WITHDRAW_LIST = "/api/v2/spot/wallet/withdrawal-records"
    EP_DEPOSIT_LIST  = "/api/v2/spot/wallet/deposit-records"

    def __init__(self, api_key: str, secret_key: str, passphrase: str, base_url: str = None):
        self.auth = BitgetAuth(api_key, secret_key, passphrase)
        self.base_url = base_url or self.BASE_URL
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self._last_request_time = 0
        self._rate_limit_ms = 100  # 10 req/s default

    def _rate_limit(self):
        """Simple rate limiter to respect API limits."""
        now = time.time() * 1000
        elapsed = now - self._last_request_time
        if elapsed < self._rate_limit_ms:
            time.sleep((self._rate_limit_ms - elapsed) / 1000)
        self._last_request_time = time.time() * 1000

    def _request(self, method: str, endpoint: str, params: dict = None,
                 body: dict = None, auth_required: bool = True) -> dict:
        """Make an authenticated or public API request."""
        self._rate_limit()

        url = f"{self.base_url}{endpoint}"
        query_string = ""
        body_str = ""

        if method.upper() == "GET" and params:
            query_string = urlencode(params)
            url = f"{url}?{query_string}"

        if method.upper() == "POST" and body:
            body_str = json.dumps(body)

        if auth_required:
            headers = self.auth.get_headers(method, endpoint, query_string, body_str)
        else:
            headers = self.auth.get_public_headers()

        max_retries = 3
        for attempt in range(max_retries):
            try:
                if method.upper() == "GET":
                    resp = self.session.get(url, headers=headers, timeout=30)
                else:
                    resp = self.session.post(url, headers=headers, data=body_str, timeout=30)

                data = resp.json()

                if data.get("code") == "00000":
                    return {"success": True, "data": data.get("data"), "msg": data.get("msg", "OK")}
                else:
                    return {"success": False, "data": None,
                            "msg": f"[{data.get('code')}] {data.get('msg', 'Unknown error')}"}
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                return {"success": False, "data": None, "msg": "Request timed out after retries"}
            except requests.exceptions.ConnectionError:
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                return {"success": False, "data": None, "msg": "Connection error - check network/VPN"}
            except Exception as e:
                return {"success": False, "data": None, "msg": str(e)}

    # ═══════════════════════════════════════════════════
    # PUBLIC ENDPOINTS
    # ═══════════════════════════════════════════════════

    def get_server_time(self) -> dict:
        return self._request("GET", self.EP_SERVER_TIME, auth_required=False)

    def get_symbols(self) -> dict:
        return self._request("GET", self.EP_SYMBOLS, auth_required=False)

    def get_single_symbol(self, symbol: str) -> dict:
        return self._request("GET", self.EP_SINGLE_SYMBOL,
                             params={"symbol": symbol}, auth_required=False)

    def get_coins(self) -> dict:
        return self._request("GET", self.EP_COINS, auth_required=False)

    # ═══════════════════════════════════════════════════
    # MARKET ENDPOINTS
    # ═══════════════════════════════════════════════════

    def get_ticker(self, symbol: str) -> dict:
        return self._request("GET", self.EP_TICKER,
                             params={"symbol": symbol}, auth_required=False)

    def get_all_tickers(self) -> dict:
        return self._request("GET", self.EP_ALL_TICKERS, auth_required=False)

    def get_recent_trades(self, symbol: str, limit: int = 50) -> dict:
        return self._request("GET", self.EP_RECENT_TRADES,
                             params={"symbol": symbol, "limit": str(limit)},
                             auth_required=False)

    def get_candles(self, symbol: str, period: str = "1h",
                    after: str = "", before: str = "", limit: int = 100) -> dict:
        params = {"symbol": symbol, "period": period, "limit": str(limit)}
        if after:
            params["after"] = after
        if before:
            params["before"] = before
        return self._request("GET", self.EP_CANDLES, params=params, auth_required=False)

    def get_depth(self, symbol: str, limit: int = 20, step: str = "") -> dict:
        params = {"symbol": symbol, "limit": str(limit)}
        if step:
            params["type"] = step
        return self._request("GET", self.EP_DEPTH, params=params, auth_required=False)

    # ═══════════════════════════════════════════════════
    # ACCOUNT ENDPOINTS
    # ═══════════════════════════════════════════════════

    def get_api_info(self) -> dict:
        return self._request("GET", self.EP_API_INFO)

    def get_assets(self, coin: str = "") -> dict:
        params = {}
        if coin:
            params["coin"] = coin
        return self._request("GET", self.EP_ASSETS, params=params if params else None)

    def get_assets_lite(self) -> dict:
        return self._request("GET", self.EP_ASSETS_LITE)

    def get_bills(self, coin_id: str = "", group_type: str = "",
                  biz_type: str = "", after: str = "", before: str = "") -> dict:
        params = {}
        if coin_id:
            params["coinId"] = coin_id
        if group_type:
            params["groupType"] = group_type
        if biz_type:
            params["bizType"] = biz_type
        if after:
            params["after"] = after
        if before:
            params["before"] = before
        return self._request("GET", self.EP_BILLS, params=params if params else None)

    # ═══════════════════════════════════════════════════
    # TRADE ENDPOINTS
    # ═══════════════════════════════════════════════════

    def place_order(self, symbol: str, side: str, order_type: str,
                    quantity: str, price: str = "", force: str = "normal",
                    client_oid: str = "") -> dict:
        """
        Place a spot order.
        side: buy / sell
        order_type: limit / market
        force: normal / post_only / fok / ioc
        """
        body = {
            "symbol": symbol,
            "side": side,
            "orderType": order_type,
            "size": quantity,
            "force": force
        }
        if price:
            body["price"] = price
        if client_oid:
            body["clientOid"] = client_oid
        return self._request("POST", self.EP_PLACE_ORDER, body=body)

    def place_market_buy(self, symbol: str, quantity: str) -> dict:
        """Quick market buy."""
        return self.place_order(symbol, "buy", "market", quantity)

    def place_market_sell(self, symbol: str, quantity: str) -> dict:
        """Quick market sell."""
        return self.place_order(symbol, "sell", "market", quantity)

    def place_limit_buy(self, symbol: str, price: str, quantity: str) -> dict:
        """Quick limit buy."""
        return self.place_order(symbol, "buy", "limit", quantity, price)

    def place_limit_sell(self, symbol: str, price: str, quantity: str) -> dict:
        """Quick limit sell."""
        return self.place_order(symbol, "sell", "limit", quantity, price)

    def batch_orders(self, symbol: str, order_list: List[dict]) -> dict:
        """Place multiple orders at once."""
        body = {"symbol": symbol, "orderList": order_list}
        return self._request("POST", self.EP_BATCH_ORDER, body=body)

    def cancel_order(self, symbol: str, order_id: str) -> dict:
        body = {"symbol": symbol, "orderId": order_id}
        return self._request("POST", self.EP_CANCEL_ORDER, body=body)

    def cancel_all_orders(self, symbol: str) -> dict:
        body = {"symbol": symbol}
        return self._request("POST", self.EP_CANCEL_SYMBOL, body=body)

    def get_order_detail(self, symbol: str, order_id: str = "",
                         client_oid: str = "") -> dict:
        params = {"symbol": symbol}
        if order_id:
            params["orderId"] = order_id
        if client_oid:
            params["clientOrderId"] = client_oid
        return self._request("GET", self.EP_ORDER_DETAIL, params=params)

    def get_open_orders(self, symbol: str = "") -> dict:
        params = {}
        if symbol:
            params["symbol"] = symbol
        return self._request("GET", self.EP_OPEN_ORDERS, params=params if params else None)

    def get_order_history(self, symbol: str, after: str = "",
                          before: str = "", limit: int = 50) -> dict:
        params = {"symbol": symbol, "limit": str(limit)}
        if after:
            params["after"] = after
        if before:
            params["before"] = before
        return self._request("GET", self.EP_ORDER_HISTORY, params=params)

    def get_fills(self, symbol: str, order_id: str = "",
                  after: str = "", before: str = "", limit: int = 50) -> dict:
        params = {"symbol": symbol, "limit": str(limit)}
        if order_id:
            params["orderId"] = order_id
        if after:
            params["after"] = after
        if before:
            params["before"] = before
        return self._request("GET", self.EP_FILLS, params=params)

    # ═══════════════════════════════════════════════════
    # PLAN ORDER ENDPOINTS (Stop-Limit / Trigger Orders)
    # ═══════════════════════════════════════════════════

    def place_plan_order(self, symbol: str, side: str, trigger_price: str,
                         execute_price: str, size: str, trigger_type: str = "market_price",
                         order_type: str = "limit") -> dict:
        body = {
            "symbol": symbol,
            "side": side,
            "triggerPrice": trigger_price,
            "executePrice": execute_price,
            "size": size,
            "triggerType": trigger_type,
            "orderType": order_type
        }
        return self._request("POST", self.EP_PLAN_ORDER, body=body)

    def cancel_plan_order(self, symbol: str, order_id: str) -> dict:
        body = {"symbol": symbol, "orderId": order_id}
        return self._request("POST", self.EP_CANCEL_PLAN, body=body)

    def get_current_plans(self, symbol: str, page_size: int = 20) -> dict:
        params = {"symbol": symbol, "pageSize": str(page_size)}
        return self._request("GET", self.EP_CURRENT_PLANS, params=params)

    # ═══════════════════════════════════════════════════
    # WALLET ENDPOINTS
    # ═══════════════════════════════════════════════════

    def get_deposit_address(self, coin: str, chain: str = "") -> dict:
        params = {"coin": coin}
        if chain:
            params["chain"] = chain
        return self._request("GET", self.EP_DEPOSIT_ADDR, params=params)

    def get_deposit_list(self, coin: str, start_time: str = "",
                         end_time: str = "", page_size: int = 20) -> dict:
        params = {"coin": coin, "pageSize": str(page_size)}
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time
        return self._request("GET", self.EP_DEPOSIT_LIST, params=params)

    def get_withdraw_list(self, coin: str, start_time: str = "",
                          end_time: str = "", page_size: int = 20) -> dict:
        params = {"coin": coin, "pageSize": str(page_size)}
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time
        return self._request("GET", self.EP_WITHDRAW_LIST, params=params)
