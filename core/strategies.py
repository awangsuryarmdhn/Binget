"""
╔══════════════════════════════════════════════════════════════╗
║  TRADING STRATEGIES ENGINE                                  ║
║  Built-in strategies for auto-trading (FULL mode)           ║
╚══════════════════════════════════════════════════════════════╝
"""

import time
import json
import os
import threading
from datetime import datetime
from typing import Optional, Dict, List
from core.api import BitgetAPI

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


class TradingStrategy:
    """Base class for all trading strategies."""

    def __init__(self, name: str, api: BitgetAPI, symbol: str):
        self.name = name
        self.api = api
        self.symbol = symbol
        self.running = False
        self.trades: List[dict] = []
        self.pnl = 0.0
        self.win_count = 0
        self.loss_count = 0

    def log_trade(self, side: str, price: float, qty: float, reason: str):
        trade = {
            "time": datetime.now().isoformat(),
            "strategy": self.name,
            "symbol": self.symbol,
            "side": side,
            "price": price,
            "qty": qty,
            "reason": reason
        }
        self.trades.append(trade)
        return trade

    def start(self):
        self.running = True

    def stop(self):
        self.running = False

    def get_stats(self) -> dict:
        total = self.win_count + self.loss_count
        win_rate = (self.win_count / total * 100) if total > 0 else 0
        return {
            "strategy": self.name,
            "symbol": self.symbol,
            "total_trades": total,
            "wins": self.win_count,
            "losses": self.loss_count,
            "win_rate": f"{win_rate:.1f}%",
            "pnl": f"{self.pnl:.4f}",
            "status": "RUNNING" if self.running else "STOPPED"
        }


class GridStrategy(TradingStrategy):
    """
    Grid Trading Strategy.
    Places buy/sell orders at fixed price intervals.
    """

    def __init__(self, api: BitgetAPI, symbol: str, upper_price: float,
                 lower_price: float, grid_count: int, investment: float):
        super().__init__("GRID", api, symbol)
        self.upper_price = upper_price
        self.lower_price = lower_price
        self.grid_count = grid_count
        self.investment = investment
        self.grid_levels = []
        self.active_orders = {}
        self._thread: Optional[threading.Thread] = None

    def _calculate_grids(self):
        """Calculate grid price levels."""
        step = (self.upper_price - self.lower_price) / self.grid_count
        self.grid_levels = []
        for i in range(self.grid_count + 1):
            price = self.lower_price + (step * i)
            self.grid_levels.append(round(price, 6))

    def _place_grid_orders(self):
        """Place initial grid orders."""
        qty_per_grid = self.investment / self.grid_count
        ticker = self.api.get_ticker(self.symbol)
        if not ticker["success"]:
            return False

        current_price = float(ticker["data"]["close"])

        for level in self.grid_levels:
            if level < current_price:
                # Buy below current price
                qty = str(round(qty_per_grid / level, 6))
                result = self.api.place_limit_buy(
                    self.symbol, str(level), qty
                )
                if result["success"]:
                    self.active_orders[str(level)] = {
                        "side": "buy", "order_id": result["data"].get("orderId")
                    }
            elif level > current_price:
                # Sell above current price
                qty = str(round(qty_per_grid / level, 6))
                result = self.api.place_limit_sell(
                    self.symbol, str(level), qty
                )
                if result["success"]:
                    self.active_orders[str(level)] = {
                        "side": "sell", "order_id": result["data"].get("orderId")
                    }
        return True

    def _monitor_loop(self):
        """Monitor and re-place filled orders."""
        while self.running:
            try:
                time.sleep(10)
                # Check open orders and re-place filled ones
                open_orders = self.api.get_open_orders(self.symbol)
                if open_orders["success"] and open_orders["data"]:
                    active_ids = {o.get("orderId") for o in open_orders["data"]}
                    for level, info in list(self.active_orders.items()):
                        if info["order_id"] not in active_ids:
                            # Order was filled — place reverse order
                            price = float(level)
                            qty_per_grid = self.investment / self.grid_count
                            qty = str(round(qty_per_grid / price, 6))

                            if info["side"] == "buy":
                                # Buy filled → place sell at next grid up
                                idx = self.grid_levels.index(price)
                                if idx < len(self.grid_levels) - 1:
                                    sell_price = self.grid_levels[idx + 1]
                                    result = self.api.place_limit_sell(
                                        self.symbol, str(sell_price), qty
                                    )
                                    if result["success"]:
                                        self.active_orders[str(sell_price)] = {
                                            "side": "sell",
                                            "order_id": result["data"].get("orderId")
                                        }
                                        self.win_count += 1
                                        self.log_trade("sell", sell_price, float(qty), "Grid fill")
                            else:
                                # Sell filled → place buy at next grid down
                                idx = self.grid_levels.index(price)
                                if idx > 0:
                                    buy_price = self.grid_levels[idx - 1]
                                    result = self.api.place_limit_buy(
                                        self.symbol, str(buy_price), qty
                                    )
                                    if result["success"]:
                                        self.active_orders[str(buy_price)] = {
                                            "side": "buy",
                                            "order_id": result["data"].get("orderId")
                                        }
                                        self.win_count += 1
                                        self.log_trade("buy", buy_price, float(qty), "Grid fill")

                            del self.active_orders[level]
            except Exception:
                time.sleep(5)

    def start(self):
        super().start()
        self._calculate_grids()
        self._place_grid_orders()
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def stop(self):
        super().stop()
        # Cancel all grid orders
        self.api.cancel_all_orders(self.symbol)
        self.active_orders.clear()


class DCAStrategy(TradingStrategy):
    """
    Dollar-Cost Averaging Strategy.
    Buys fixed amount at regular intervals.
    """

    def __init__(self, api: BitgetAPI, symbol: str, amount_per_buy: float,
                 interval_seconds: int = 3600):
        super().__init__("DCA", api, symbol)
        self.amount_per_buy = amount_per_buy
        self.interval = interval_seconds
        self.total_invested = 0.0
        self.total_coins = 0.0
        self.avg_price = 0.0
        self._thread: Optional[threading.Thread] = None

    def _dca_loop(self):
        while self.running:
            try:
                ticker = self.api.get_ticker(self.symbol)
                if ticker["success"]:
                    price = float(ticker["data"]["close"])
                    qty = round(self.amount_per_buy / price, 6)
                    result = self.api.place_market_buy(self.symbol, str(qty))
                    if result["success"]:
                        self.total_invested += self.amount_per_buy
                        self.total_coins += qty
                        self.avg_price = self.total_invested / self.total_coins if self.total_coins > 0 else 0
                        self.win_count += 1
                        self.log_trade("buy", price, qty, f"DCA #{self.win_count}")
                time.sleep(self.interval)
            except Exception:
                time.sleep(30)

    def start(self):
        super().start()
        self._thread = threading.Thread(target=self._dca_loop, daemon=True)
        self._thread.start()


class ScalpStrategy(TradingStrategy):
    """
    Scalping Strategy.
    Quick in-and-out trades based on spread and momentum.
    """

    def __init__(self, api: BitgetAPI, symbol: str, spread_threshold: float = 0.001,
                 take_profit_pct: float = 0.003, stop_loss_pct: float = 0.002,
                 qty_usdt: float = 50.0):
        super().__init__("SCALP", api, symbol)
        self.spread_threshold = spread_threshold
        self.take_profit_pct = take_profit_pct
        self.stop_loss_pct = stop_loss_pct
        self.qty_usdt = qty_usdt
        self._thread: Optional[threading.Thread] = None
        self._position: Optional[dict] = None

    def _scalp_loop(self):
        while self.running:
            try:
                if self._position is None:
                    # Look for entry
                    depth = self.api.get_depth(self.symbol, limit=5)
                    if depth["success"] and depth["data"]:
                        asks = depth["data"].get("asks", [])
                        bids = depth["data"].get("bids", [])
                        if asks and bids:
                            best_ask = float(asks[0][0])
                            best_bid = float(bids[0][0])
                            spread = (best_ask - best_bid) / best_bid

                            if spread <= self.spread_threshold:
                                # Tight spread → enter long
                                price = best_ask
                                qty = round(self.qty_usdt / price, 6)
                                result = self.api.place_market_buy(self.symbol, str(qty))
                                if result["success"]:
                                    self._position = {
                                        "entry_price": price,
                                        "qty": qty,
                                        "time": time.time()
                                    }
                                    self.log_trade("buy", price, qty, f"Scalp entry (spread={spread:.5f})")

                else:
                    # Monitor position
                    ticker = self.api.get_ticker(self.symbol)
                    if ticker["success"]:
                        current = float(ticker["data"]["close"])
                        entry = self._position["entry_price"]
                        pnl_pct = (current - entry) / entry

                        if pnl_pct >= self.take_profit_pct:
                            # Take profit
                            result = self.api.place_market_sell(
                                self.symbol, str(self._position["qty"])
                            )
                            if result["success"]:
                                profit = pnl_pct * self.qty_usdt
                                self.pnl += profit
                                self.win_count += 1
                                self.log_trade("sell", current, self._position["qty"],
                                               f"TP hit +{pnl_pct*100:.2f}%")
                                self._position = None

                        elif pnl_pct <= -self.stop_loss_pct:
                            # Stop loss
                            result = self.api.place_market_sell(
                                self.symbol, str(self._position["qty"])
                            )
                            if result["success"]:
                                loss = pnl_pct * self.qty_usdt
                                self.pnl += loss
                                self.loss_count += 1
                                self.log_trade("sell", current, self._position["qty"],
                                               f"SL hit {pnl_pct*100:.2f}%")
                                self._position = None

                time.sleep(2)
            except Exception:
                time.sleep(5)

    def start(self):
        super().start()
        self._thread = threading.Thread(target=self._scalp_loop, daemon=True)
        self._thread.start()
