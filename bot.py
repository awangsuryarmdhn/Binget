"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                            ║
║   ███╗   ██╗██╗████████╗██████╗  ██████╗     ████████╗██████╗              ║
║   ████╗  ██║██║╚══██╔══╝██╔══██╗██╔═══██╗    ╚══██╔══╝██╔══██╗             ║
║   ██╔██╗ ██║██║   ██║   ██████╔╝██║   ██║       ██║   ██████╔╝             ║
║   ██║╚██╗██║██║   ██║   ██╔══██╗██║   ██║       ██║   ██╔══██╗             ║
║   ██║ ╚████║██║   ██║   ██║  ██║╚██████╔╝       ██║   ██║  ██║             ║
║   ╚═╝  ╚═══╝╚═╝   ╚═╝   ╚═╝  ╚═╝ ╚═════╝        ╚═╝   ╚═╝  ╚═╝             ║
║                                                                            ║
║           ⚡ BITGET FULL & LIGHT TRADING BOT v2.0 ⚡                        ║
║        Premium Interactive CLI + VPS Web Dashboard                         ║
║                                                                            ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import io
import time
import json
import signal
from datetime import datetime
from dotenv import load_dotenv

# Fix Windows console encoding for Unicode support
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    os.environ['PYTHONIOENCODING'] = 'utf-8'

# Rich for premium CLI UI
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.layout import Layout
from rich.live import Live
from rich.text import Text
from rich.prompt import Prompt, Confirm, IntPrompt, FloatPrompt
from rich.progress import Progress, BarColumn, TextColumn
from rich.markdown import Markdown
from rich import box

# Core modules
from core.api import BitgetAPI
from core.websocket_client import BitgetWebSocket
from core.strategies import GridStrategy, DCAStrategy, ScalpStrategy
from core.dashboard import WebDashboard

# ═══════════════════════════════════════════════════
# GLOBALS
# ═══════════════════════════════════════════════════

console = Console(force_terminal=True)
load_dotenv()

API_KEY = os.getenv("BITGET_API_KEY", "")
SECRET_KEY = os.getenv("BITGET_SECRET_KEY", "")
PASSPHRASE = os.getenv("BITGET_PASSPHRASE", "")
DEFAULT_SYMBOL = os.getenv("DEFAULT_SYMBOL", "BTCUSDT_SPBL")
TRADE_MODE = os.getenv("TRADE_MODE", "light")
WEB_PORT = int(os.getenv("WEB_DASHBOARD_PORT", "8888"))
ENABLE_WEB = os.getenv("ENABLE_WEB_DASHBOARD", "true").lower() == "true"

api: BitgetAPI = None
ws: BitgetWebSocket = None
dashboard: WebDashboard = None
strategies = {}
current_symbol = DEFAULT_SYMBOL


# ═══════════════════════════════════════════════════
# PERSISTENT CONFIG
# ═══════════════════════════════════════════════════

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot_state.json")

def save_config():
    """Save persistent bot state to disk."""
    state = {
        "trade_mode": TRADE_MODE,
        "current_symbol": current_symbol,
        "web_port": WEB_PORT
    }
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(state, f, indent=2)
    except Exception:
        pass

def load_config():
    """Load persistent bot state from disk."""
    global TRADE_MODE, current_symbol
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                state = json.load(f)
            TRADE_MODE = state.get("trade_mode", TRADE_MODE)
            current_symbol = state.get("current_symbol", current_symbol)
    except Exception:
        pass


# ═══════════════════════════════════════════════════
# UI HELPERS
# ═══════════════════════════════════════════════════

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')


def show_banner():
    """Show premium startup banner."""
    art_lines = [
        "    _   _ ___ _____ ____   ___    _____ ____      _    ____  _____ ____  ",
        "   | \\ | |_ _|_   _|  _ \\ / _ \\  |_   _|  _ \\   / \\  |  _ \\| ____|  _ \\ ",
        "   |  \\| || |  | | | |_) | | | |   | | | |_) | / _ \\ | | | |  _| | |_) |",
        "   | |\\  || |  | | |  _ <| |_| |   | | |  _ < / ___ \\| |_| | |___|  _ < ",
        "   |_| \\_|___|_|_| |_| \\_\\\\___/    |_| |_| \\_/_/   \\_|____/|_____|_| \\_\\\\",
    ]
    for line in art_lines:
        console.print(line, style="bold cyan")
    console.print()
    console.print("              [Bitget Full & Light Trading Bot v2.0]", style="dim")
    console.print("         Premium CLI + VPS Web Dashboard - Design Thinking UX", style="dim cyan")
    console.print()


def show_status_bar():
    """Show a compact status bar."""
    mode_color = "green" if TRADE_MODE == "full" else "yellow"
    mode_text = "FULL AUTO" if TRADE_MODE == "full" else "LIGHT"

    ticker = api.get_ticker(current_symbol)
    price = "—"
    change = "—"
    change_color = "white"
    if ticker["success"] and ticker["data"]:
        price = f"${float(ticker['data'].get('close', 0)):,.2f}"
        ch = float(ticker["data"].get("changeUtc", ticker["data"].get("change", 0)) or 0)
        change = f"{'+' if ch >= 0 else ''}{ch:.2f}%"
        change_color = "green" if ch >= 0 else "red"

    web_status = f"[green]● :8888[/green]" if ENABLE_WEB else "[dim]○ OFF[/dim]"

    table = Table(show_header=False, box=box.SIMPLE, padding=(0, 2))
    table.add_column(justify="left")
    table.add_column(justify="center")
    table.add_column(justify="center")
    table.add_column(justify="center")
    table.add_column(justify="right")
    table.add_row(
        f"[{mode_color}]● {mode_text}[/{mode_color}]",
        f"[bold]{current_symbol}[/bold]",
        f"[bold white]{price}[/bold white]",
        f"[{change_color}]{change}[/{change_color}]",
        f"Web: {web_status}  [dim]{datetime.now().strftime('%H:%M:%S')}[/dim]"
    )
    console.print(Panel(table, border_style="blue", padding=(0, 0)))


def show_main_menu():
    """Display the interactive main menu."""
    mode_label = "FULL AUTO" if TRADE_MODE == "full" else "LIGHT"
    mode_color = "green" if TRADE_MODE == "full" else "yellow"
    menu_items = [
        ("1", "📊", "Market Watch", "Live prices, depth, trades"),
        ("2", "💰", "Portfolio", "Balances & asset overview"),
        ("3", "📋", "Orders", "Open orders & history"),
        ("4", "🛒", "Trade", "Place buy/sell orders"),
        ("5", "🎯", "Plan Orders", "Stop-limit & trigger orders"),
        ("6", "📈", "Candle Chart", "OHLCV chart data"),
        ("7", "🔍", "Order Book", "Live depth visualization"),
        ("8", "⚡", "Strategies", "Auto-trading (Grid/DCA/Scalp)"),
        ("9", "🔧", "Settings", "Symbol, mode, dashboard"),
        ("m", "🔄", f"Mode [{mode_label}]", f"Quick toggle LIGHT <-> FULL"),
        ("0", "🚪", "Exit", "Quit NITRO TRADER"),
    ]

    table = Table(title="[bold cyan]⚡ COMMAND CENTER[/bold cyan]",
                  box=box.DOUBLE_EDGE, border_style="cyan",
                  title_style="bold cyan", padding=(0, 2))
    table.add_column("#", style="bold yellow", width=3, justify="center")
    table.add_column("", width=3)
    table.add_column("Action", style="bold white", min_width=16)
    table.add_column("Description", style="dim")

    for num, icon, name, desc in menu_items:
        style = f"bold {mode_color}" if num == "m" else None
        table.add_row(num, icon, name, desc, style=style)

    console.print(table)


# ═══════════════════════════════════════════════════
# FEATURE: MARKET WATCH
# ═══════════════════════════════════════════════════

def market_watch():
    """Live market watch with top tickers."""
    clear()
    console.print(Panel("[bold cyan]📊 MARKET WATCH[/bold cyan]", border_style="cyan"))

    with Progress(TextColumn("[cyan]Fetching market data..."), BarColumn(),
                  transient=True) as progress:
        task = progress.add_task("", total=3)
        tickers_resp = api.get_all_tickers()
        progress.advance(task)
        ticker_resp = api.get_ticker(current_symbol)
        progress.advance(task)
        trades_resp = api.get_recent_trades(current_symbol, limit=10)
        progress.advance(task)

    # Current symbol detail
    if ticker_resp["success"] and ticker_resp["data"]:
        d = ticker_resp["data"]
        detail = Table(title=f"[bold]{current_symbol}[/bold]", box=box.ROUNDED, border_style="blue")
        detail.add_column("Metric", style="dim")
        detail.add_column("Value", style="bold")
        detail.add_row("Last Price", f"[bold white]${float(d.get('close', 0)):,.6f}[/bold white]")
        detail.add_row("24h High", f"[green]{float(d.get('high24h', 0)):,.6f}[/green]")
        detail.add_row("24h Low", f"[red]{float(d.get('low24h', 0)):,.6f}[/red]")
        detail.add_row("24h Volume", f"{float(d.get('baseVol', 0)):,.2f}")
        detail.add_row("Quote Volume", f"${float(d.get('quoteVol', 0)):,.2f}")
        detail.add_row("Best Bid", f"[green]{d.get('buyOne', '—')}[/green]")
        detail.add_row("Best Ask", f"[red]{d.get('sellOne', '—')}[/red]")
        console.print(detail)

    # Top movers
    if tickers_resp["success"] and tickers_resp["data"]:
        all_tickers = tickers_resp["data"]
        # Sort by change
        for t in all_tickers:
            try:
                t["_change"] = float(t.get("changeUtc", t.get("change", 0)) or 0)
            except (ValueError, TypeError):
                t["_change"] = 0.0

        top_gainers = sorted(all_tickers, key=lambda x: x["_change"], reverse=True)[:8]
        top_losers = sorted(all_tickers, key=lambda x: x["_change"])[:8]

        gains_table = Table(title="[green]🚀 TOP GAINERS[/green]", box=box.SIMPLE,
                           border_style="green")
        gains_table.add_column("Symbol", style="bold")
        gains_table.add_column("Price", justify="right")
        gains_table.add_column("Change", justify="right", style="green")
        for t in top_gainers:
            gains_table.add_row(
                t.get("symbol", ""),
                f"{float(t.get('close', 0)):,.6f}",
                f"+{t['_change']:.2f}%"
            )

        loss_table = Table(title="[red]📉 TOP LOSERS[/red]", box=box.SIMPLE,
                          border_style="red")
        loss_table.add_column("Symbol", style="bold")
        loss_table.add_column("Price", justify="right")
        loss_table.add_column("Change", justify="right", style="red")
        for t in top_losers:
            loss_table.add_row(
                t.get("symbol", ""),
                f"{float(t.get('close', 0)):,.6f}",
                f"{t['_change']:.2f}%"
            )

        console.print(Columns([gains_table, loss_table]))

    # Recent trades
    if trades_resp["success"] and trades_resp["data"]:
        trades_table = Table(title="[bold]Recent Trades[/bold]", box=box.SIMPLE)
        trades_table.add_column("Time")
        trades_table.add_column("Side", justify="center")
        trades_table.add_column("Price", justify="right")
        trades_table.add_column("Qty", justify="right")
        for t in trades_resp["data"][:10]:
            side = t.get("side", "buy")
            color = "green" if side == "buy" else "red"
            ts = datetime.fromtimestamp(int(t.get("timestamp", 0)) / 1000).strftime("%H:%M:%S")
            trades_table.add_row(
                ts,
                f"[{color}]{side.upper()}[/{color}]",
                f"{float(t.get('price', 0)):,.6f}",
                f"{float(t.get('size', t.get('quantity', 0))):,.6f}"
            )
        console.print(trades_table)

    input("\n[Press Enter to return] ")


# ═══════════════════════════════════════════════════
# FEATURE: PORTFOLIO
# ═══════════════════════════════════════════════════

def portfolio():
    """Show account balances and portfolio overview."""
    clear()
    console.print(Panel("[bold cyan]💰 PORTFOLIO & BALANCES[/bold cyan]", border_style="cyan"))

    with Progress(TextColumn("[cyan]Loading portfolio..."), BarColumn(), transient=True) as p:
        task = p.add_task("", total=2)
        assets_resp = api.get_assets()
        p.advance(task)
        api_info = api.get_api_info()
        p.advance(task)

    # API Info
    if api_info["success"] and api_info["data"]:
        info = api_info["data"]
        console.print(Panel(
            f"[dim]User ID:[/dim] [bold]{info.get('userId', '—')}[/bold]  "
            f"[dim]Permissions:[/dim] [green]{', '.join(info.get('authorities', []))}[/green]  "
            f"[dim]IP:[/dim] {info.get('ipList', ['—'])[0] if info.get('ipList') else '—'}",
            title="[bold]API Key Info[/bold]",
            border_style="dim"
        ))

    # Balances
    if assets_resp["success"] and assets_resp["data"]:
        balances = [a for a in assets_resp["data"]
                    if float(a.get("available", 0)) > 0 or float(a.get("frozen", 0)) > 0]

        if balances:
            table = Table(title="[bold]Asset Balances[/bold]", box=box.ROUNDED,
                         border_style="green")
            table.add_column("Coin", style="bold yellow")
            table.add_column("Available", justify="right", style="green")
            table.add_column("Frozen", justify="right", style="red")
            table.add_column("Total", justify="right", style="bold")

            for b in balances:
                avail = float(b.get("available", 0))
                frozen = float(b.get("frozen", 0))
                total = avail + frozen
                table.add_row(
                    b.get("coinName", b.get("coin", "?")),
                    f"{avail:,.8f}",
                    f"{frozen:,.8f}",
                    f"{total:,.8f}"
                )
            console.print(table)
        else:
            console.print("[yellow]No assets with balance found.[/yellow]")
    else:
        console.print(f"[red]Failed to load assets: {assets_resp['msg']}[/red]")

    input("\n[Press Enter to return] ")


# ═══════════════════════════════════════════════════
# FEATURE: ORDERS
# ═══════════════════════════════════════════════════

def orders():
    """View open orders and order history."""
    clear()
    console.print(Panel("[bold cyan]📋 ORDER MANAGEMENT[/bold cyan]", border_style="cyan"))

    console.print("[1] Open Orders  [2] Order History  [3] Cancel Order  [4] Cancel All  [0] Back")
    choice = Prompt.ask("Select", choices=["1", "2", "3", "4", "0"], default="1")

    if choice == "0":
        return

    if choice == "1":
        resp = api.get_open_orders(current_symbol)
        if resp["success"] and resp["data"]:
            table = Table(title="[bold]Open Orders[/bold]", box=box.ROUNDED)
            table.add_column("Order ID", style="dim")
            table.add_column("Side", justify="center")
            table.add_column("Type")
            table.add_column("Price", justify="right")
            table.add_column("Qty", justify="right")
            table.add_column("Status")
            for o in resp["data"]:
                side = o.get("side", "buy")
                color = "green" if side == "buy" else "red"
                table.add_row(
                    o.get("orderId", "")[:16] + "...",
                    f"[{color}]{side.upper()}[/{color}]",
                    o.get("orderType", ""),
                    o.get("price", "—"),
                    o.get("quantity", o.get("size", "—")),
                    o.get("status", "—")
                )
            console.print(table)
        else:
            console.print("[yellow]No open orders.[/yellow]")

    elif choice == "2":
        resp = api.get_order_history(current_symbol)
        if resp["success"] and resp["data"]:
            table = Table(title="[bold]Order History[/bold]", box=box.ROUNDED)
            table.add_column("Time")
            table.add_column("Side", justify="center")
            table.add_column("Type")
            table.add_column("Price", justify="right")
            table.add_column("Filled", justify="right")
            table.add_column("Status")
            for o in resp["data"][:20]:
                side = o.get("side", "buy")
                color = "green" if side == "buy" else "red"
                ts = "—"
                if o.get("cTime"):
                    ts = datetime.fromtimestamp(int(o["cTime"]) / 1000).strftime("%m/%d %H:%M")
                table.add_row(
                    ts,
                    f"[{color}]{side.upper()}[/{color}]",
                    o.get("orderType", ""),
                    o.get("price", "—"),
                    o.get("fillQuantity", o.get("filledQty", "—")),
                    o.get("status", "—")
                )
            console.print(table)
        else:
            console.print("[yellow]No order history.[/yellow]")

    elif choice == "3":
        order_id = Prompt.ask("[bold]Order ID to cancel[/bold]")
        resp = api.cancel_order(current_symbol, order_id)
        if resp["success"]:
            console.print("[green]✓ Order cancelled successfully![/green]")
        else:
            console.print(f"[red]✗ Failed: {resp['msg']}[/red]")

    elif choice == "4":
        if Confirm.ask(f"[red]Cancel ALL open orders for {current_symbol}?[/red]"):
            resp = api.cancel_all_orders(current_symbol)
            if resp["success"]:
                console.print("[green]✓ All orders cancelled![/green]")
            else:
                console.print(f"[red]✗ Failed: {resp['msg']}[/red]")

    input("\n[Press Enter to return] ")


# ═══════════════════════════════════════════════════
# FEATURE: TRADE
# ═══════════════════════════════════════════════════

def trade():
    """Interactive trading interface."""
    clear()
    console.print(Panel("[bold cyan]🛒 TRADE CENTER[/bold cyan]", border_style="cyan"))

    # Show current price first
    ticker = api.get_ticker(current_symbol)
    if ticker["success"] and ticker["data"]:
        price = float(ticker["data"].get("close", 0))
        console.print(f"  [bold]{current_symbol}[/bold] → [bold white]${price:,.6f}[/bold white]")
        console.print()

    console.print("[1] Market Buy   [2] Market Sell   [3] Limit Buy   [4] Limit Sell   [0] Back")
    choice = Prompt.ask("Select", choices=["1", "2", "3", "4", "0"], default="0")

    if choice == "0":
        return

    qty = Prompt.ask("[bold]Quantity[/bold]")

    if choice in ["1", "2"]:
        side = "buy" if choice == "1" else "sell"
        if Confirm.ask(f"[yellow]Confirm MARKET {side.upper()} {qty} on {current_symbol}?[/yellow]"):
            with console.status(f"[cyan]Placing {side} order..."):
                if side == "buy":
                    resp = api.place_market_buy(current_symbol, qty)
                else:
                    resp = api.place_market_sell(current_symbol, qty)

            if resp["success"]:
                console.print(f"[green]✓ Market {side.upper()} executed! Order ID: {resp['data'].get('orderId', '—')}[/green]")
            else:
                console.print(f"[red]✗ Failed: {resp['msg']}[/red]")

    elif choice in ["3", "4"]:
        price = Prompt.ask("[bold]Price[/bold]")
        side = "buy" if choice == "3" else "sell"
        if Confirm.ask(f"[yellow]Confirm LIMIT {side.upper()} {qty} @ {price} on {current_symbol}?[/yellow]"):
            with console.status(f"[cyan]Placing {side} order..."):
                if side == "buy":
                    resp = api.place_limit_buy(current_symbol, price, qty)
                else:
                    resp = api.place_limit_sell(current_symbol, price, qty)

            if resp["success"]:
                console.print(f"[green]✓ Limit {side.upper()} placed! Order ID: {resp['data'].get('orderId', '—')}[/green]")
            else:
                console.print(f"[red]✗ Failed: {resp['msg']}[/red]")

    input("\n[Press Enter to return] ")


# ═══════════════════════════════════════════════════
# FEATURE: PLAN ORDERS
# ═══════════════════════════════════════════════════

def plan_orders():
    """Stop-limit and trigger order management."""
    clear()
    console.print(Panel("[bold cyan]🎯 PLAN ORDERS (Stop-Limit)[/bold cyan]", border_style="cyan"))

    console.print("[1] Place Plan Order  [2] View Active Plans  [3] Cancel Plan  [0] Back")
    choice = Prompt.ask("Select", choices=["1", "2", "3", "0"], default="0")

    if choice == "0":
        return

    if choice == "1":
        side = Prompt.ask("Side", choices=["buy", "sell"])
        trigger_price = Prompt.ask("Trigger Price")
        execute_price = Prompt.ask("Execute Price")
        size = Prompt.ask("Size (quantity)")

        resp = api.place_plan_order(
            current_symbol, side, trigger_price, execute_price, size
        )
        if resp["success"]:
            console.print(f"[green]✓ Plan order placed![/green]")
        else:
            console.print(f"[red]✗ Failed: {resp['msg']}[/red]")

    elif choice == "2":
        resp = api.get_current_plans(current_symbol)
        if resp["success"] and resp["data"]:
            table = Table(title="Active Plan Orders", box=box.ROUNDED)
            table.add_column("ID", style="dim")
            table.add_column("Side")
            table.add_column("Trigger", justify="right")
            table.add_column("Execute", justify="right")
            table.add_column("Size", justify="right")
            for p in (resp["data"] if isinstance(resp["data"], list) else [resp["data"]]):
                side_color = "green" if p.get("side") == "buy" else "red"
                table.add_row(
                    str(p.get("orderId", ""))[:16],
                    f"[{side_color}]{p.get('side', '').upper()}[/{side_color}]",
                    p.get("triggerPrice", "—"),
                    p.get("executePrice", "—"),
                    p.get("size", "—")
                )
            console.print(table)
        else:
            console.print("[yellow]No active plan orders.[/yellow]")

    elif choice == "3":
        order_id = Prompt.ask("Plan Order ID to cancel")
        resp = api.cancel_plan_order(current_symbol, order_id)
        if resp["success"]:
            console.print("[green]✓ Plan order cancelled![/green]")
        else:
            console.print(f"[red]✗ {resp['msg']}[/red]")

    input("\n[Press Enter to return] ")


# ═══════════════════════════════════════════════════
# FEATURE: CANDLE CHART (ASCII)
# ═══════════════════════════════════════════════════

def candle_chart():
    """Display ASCII candle chart."""
    clear()
    console.print(Panel("[bold cyan]📈 CANDLE CHART[/bold cyan]", border_style="cyan"))

    period = Prompt.ask("Timeframe", choices=["1min", "5min", "15min", "30min", "1h", "4h", "1day"],
                       default="1h")
    limit = IntPrompt.ask("Candles to show", default=40)

    with console.status("[cyan]Loading candle data..."):
        resp = api.get_candles(current_symbol, period, limit=limit)

    if not resp["success"] or not resp["data"]:
        console.print(f"[red]Failed: {resp['msg']}[/red]")
        input("\n[Press Enter to return] ")
        return

    candles = resp["data"]
    if not candles:
        console.print("[yellow]No candle data.[/yellow]")
        input("\n[Press Enter to return] ")
        return

    # Parse: [timestamp, open, high, low, close, volume]
    parsed = []
    for c in candles:
        if isinstance(c, list) and len(c) >= 5:
            parsed.append({
                "time": datetime.fromtimestamp(int(c[0]) / 1000).strftime("%m/%d %H:%M"),
                "open": float(c[1]),
                "high": float(c[2]),
                "low": float(c[3]),
                "close": float(c[4]),
                "vol": float(c[5]) if len(c) > 5 else 0
            })

    if not parsed:
        console.print("[yellow]Could not parse candle data.[/yellow]")
        input("\n[Press Enter to return] ")
        return

    parsed.reverse()  # oldest first

    # ASCII candlestick chart
    all_highs = [c["high"] for c in parsed]
    all_lows = [c["low"] for c in parsed]
    chart_max = max(all_highs)
    chart_min = min(all_lows)
    chart_range = chart_max - chart_min
    height = 20

    if chart_range == 0:
        chart_range = 1

    console.print(f"\n[bold]{current_symbol}[/bold] — {period} — Last {len(parsed)} candles")
    console.print(f"[dim]High: {chart_max:,.6f}  Low: {chart_min:,.6f}  Range: {chart_range:,.6f}[/dim]\n")

    # Render chart row by row
    for row in range(height, -1, -1):
        price_at_row = chart_min + (chart_range * row / height)
        line = f"  {price_at_row:>12,.4f} │"
        for c in parsed[-50:]:  # limit display width
            h_row = int((c["high"] - chart_min) / chart_range * height)
            l_row = int((c["low"] - chart_min) / chart_range * height)
            o_row = int((c["open"] - chart_min) / chart_range * height)
            c_row = int((c["close"] - chart_min) / chart_range * height)
            body_top = max(o_row, c_row)
            body_bot = min(o_row, c_row)
            bullish = c["close"] >= c["open"]

            if body_bot <= row <= body_top:
                line += "[green]█[/green]" if bullish else "[red]█[/red]"
            elif l_row <= row <= h_row:
                line += "[dim]│[/dim]"
            else:
                line += " "
        console.print(line)

    # X-axis
    console.print("              └" + "─" * min(len(parsed), 50))

    # Table for last few candles
    detail = Table(title="Recent Candles", box=box.SIMPLE)
    detail.add_column("Time")
    detail.add_column("Open", justify="right")
    detail.add_column("High", justify="right", style="green")
    detail.add_column("Low", justify="right", style="red")
    detail.add_column("Close", justify="right")
    detail.add_column("Volume", justify="right", style="dim")
    for c in parsed[-8:]:
        color = "green" if c["close"] >= c["open"] else "red"
        detail.add_row(
            c["time"],
            f"{c['open']:,.6f}",
            f"{c['high']:,.6f}",
            f"{c['low']:,.6f}",
            f"[{color}]{c['close']:,.6f}[/{color}]",
            f"{c['vol']:,.2f}"
        )
    console.print(detail)

    input("\n[Press Enter to return] ")


# ═══════════════════════════════════════════════════
# FEATURE: ORDER BOOK
# ═══════════════════════════════════════════════════

def order_book():
    """Display visual order book depth."""
    clear()
    console.print(Panel("[bold cyan]🔍 ORDER BOOK DEPTH[/bold cyan]", border_style="cyan"))

    with console.status("[cyan]Loading depth..."):
        resp = api.get_depth(current_symbol, limit=15)

    if not resp["success"] or not resp["data"]:
        console.print(f"[red]Failed: {resp['msg']}[/red]")
        input("\n[Press Enter to return] ")
        return

    asks = resp["data"].get("asks", [])[:15]
    bids = resp["data"].get("bids", [])[:15]

    asks.reverse()  # Show highest ask on top

    max_ask_qty = max([float(a[1]) for a in asks], default=1)
    max_bid_qty = max([float(b[1]) for b in bids], default=1)
    max_qty = max(max_ask_qty, max_bid_qty)
    bar_width = 30

    console.print(f"\n[bold]{current_symbol}[/bold] — Order Book\n")

    # Asks (sells)
    console.print("[bold red]  ASKS (Sells)[/bold red]")
    for a in asks:
        price = float(a[0])
        qty = float(a[1])
        bar_len = int((qty / max_qty) * bar_width)
        bar = "█" * bar_len
        console.print(f"  [red]{price:>14,.6f}[/red]  {qty:>14,.6f}  [red]{bar}[/red]")

    # Spread
    if asks and bids:
        best_ask = float(asks[-1][0])
        best_bid = float(bids[0][0])
        spread = best_ask - best_bid
        spread_pct = (spread / best_bid * 100) if best_bid > 0 else 0
        console.print(f"\n  [bold yellow]{'─' * 50}[/bold yellow]")
        console.print(f"  [bold yellow]  SPREAD: {spread:,.6f} ({spread_pct:.4f}%)[/bold yellow]")
        console.print(f"  [bold yellow]{'─' * 50}[/bold yellow]\n")

    # Bids (buys)
    console.print("[bold green]  BIDS (Buys)[/bold green]")
    for b in bids:
        price = float(b[0])
        qty = float(b[1])
        bar_len = int((qty / max_qty) * bar_width)
        bar = "█" * bar_len
        console.print(f"  [green]{price:>14,.6f}[/green]  {qty:>14,.6f}  [green]{bar}[/green]")

    input("\n[Press Enter to return] ")


# ═══════════════════════════════════════════════════
# FEATURE: STRATEGIES
# ═══════════════════════════════════════════════════

def strategy_menu():
    """Auto-trading strategy management."""
    clear()
    console.print(Panel("[bold cyan]⚡ AUTO-TRADING STRATEGIES[/bold cyan]", border_style="cyan"))

    if TRADE_MODE == "light":
        console.print("[yellow]⚠ Strategies require FULL mode. Change in Settings.[/yellow]")
        input("\n[Press Enter to return] ")
        return

    console.print("[1] Grid Trading  [2] DCA Bot  [3] Scalp Bot  [4] View Active  [5] Stop All  [0] Back")
    choice = Prompt.ask("Select", choices=["1", "2", "3", "4", "5", "0"])

    if choice == "0":
        return

    if choice == "1":
        upper = FloatPrompt.ask("Grid Upper Price")
        lower = FloatPrompt.ask("Grid Lower Price")
        grids = IntPrompt.ask("Number of Grids", default=10)
        invest = FloatPrompt.ask("Total Investment (USDT)")

        strat = GridStrategy(api, current_symbol, upper, lower, grids, invest)
        if Confirm.ask(f"[yellow]Start Grid Bot on {current_symbol}?[/yellow]"):
            strat.start()
            strategies["grid"] = strat
            console.print("[green]✓ Grid Trading Bot started![/green]")

    elif choice == "2":
        amount = FloatPrompt.ask("Amount per buy (USDT)")
        interval = IntPrompt.ask("Interval (seconds)", default=3600)

        strat = DCAStrategy(api, current_symbol, amount, interval)
        if Confirm.ask(f"[yellow]Start DCA Bot on {current_symbol}?[/yellow]"):
            strat.start()
            strategies["dca"] = strat
            console.print("[green]✓ DCA Bot started![/green]")

    elif choice == "3":
        tp = FloatPrompt.ask("Take Profit %", default=0.3)
        sl = FloatPrompt.ask("Stop Loss %", default=0.2)
        qty = FloatPrompt.ask("Trade Size (USDT)", default=50.0)

        strat = ScalpStrategy(api, current_symbol,
                              take_profit_pct=tp/100, stop_loss_pct=sl/100, qty_usdt=qty)
        if Confirm.ask(f"[yellow]Start Scalp Bot on {current_symbol}?[/yellow]"):
            strat.start()
            strategies["scalp"] = strat
            console.print("[green]✓ Scalp Bot started![/green]")

    elif choice == "4":
        if not strategies:
            console.print("[yellow]No active strategies.[/yellow]")
        else:
            table = Table(title="Active Strategies", box=box.ROUNDED, border_style="cyan")
            table.add_column("Name")
            table.add_column("Symbol")
            table.add_column("Trades")
            table.add_column("Win Rate")
            table.add_column("PnL")
            table.add_column("Status")
            for name, strat in strategies.items():
                stats = strat.get_stats()
                pnl_color = "green" if float(stats["pnl"]) >= 0 else "red"
                table.add_row(
                    stats["strategy"],
                    stats["symbol"],
                    str(stats["total_trades"]),
                    stats["win_rate"],
                    f"[{pnl_color}]{stats['pnl']}[/{pnl_color}]",
                    f"[green]{stats['status']}[/green]" if stats["status"] == "RUNNING" else stats["status"]
                )
            console.print(table)

    elif choice == "5":
        if Confirm.ask("[red]Stop ALL strategies?[/red]"):
            for name, strat in strategies.items():
                strat.stop()
            strategies.clear()
            console.print("[green]✓ All strategies stopped.[/green]")

    input("\n[Press Enter to return] ")


# ═══════════════════════════════════════════════════
# FEATURE: SETTINGS
# ═══════════════════════════════════════════════════

def settings():
    """Bot configuration."""
    global current_symbol, TRADE_MODE
    clear()
    console.print(Panel("[bold cyan]🔧 SETTINGS[/bold cyan]", border_style="cyan"))

    table = Table(box=box.SIMPLE)
    table.add_column("Setting", style="bold")
    table.add_column("Current Value", style="cyan")
    table.add_row("Active Symbol", current_symbol)
    table.add_row("Trade Mode", TRADE_MODE)
    table.add_row("Web Dashboard", f"{'Enabled' if ENABLE_WEB else 'Disabled'} (:{WEB_PORT})")
    table.add_row("API Key", f"{API_KEY[:12]}...{API_KEY[-4:]}")
    console.print(table)

    console.print("\n[1] Change Symbol  [2] Toggle Mode  [3] API Test  [0] Back")
    choice = Prompt.ask("Select", choices=["1", "2", "3", "0"])

    if choice == "1":
        new_sym = Prompt.ask("[bold]Enter symbol[/bold] (e.g. ETHUSDT_SPBL)",
                            default=current_symbol)
        # Validate
        resp = api.get_single_symbol(new_sym)
        if resp["success"]:
            current_symbol = new_sym
            console.print(f"[green]✓ Symbol changed to {current_symbol}[/green]")
        else:
            console.print(f"[red]Invalid symbol: {resp['msg']}[/red]")

    elif choice == "2":
        interactive_mode_switch()

    elif choice == "3":
        with console.status("[cyan]Testing API connection..."):
            st = api.get_server_time()
            acc = api.get_api_info()

        if st["success"]:
            console.print(f"[green]✓ Server Time: {st['data']}[/green]")
        else:
            console.print(f"[red]✗ Server Time failed: {st['msg']}[/red]")

        if acc["success"]:
            console.print(f"[green]✓ API Auth OK — User: {acc['data'].get('userId', '—')}[/green]")
        else:
            console.print(f"[red]✗ API Auth failed: {acc['msg']}[/red]")

    input("\n[Press Enter to return] ")


# ═══════════════════════════════════════════════════
# INTERACTIVE MODE SWITCHER
# ═══════════════════════════════════════════════════

def interactive_mode_switch():
    """Interactive mode switcher with visual confirmation."""
    global TRADE_MODE
    clear()

    current = TRADE_MODE
    console.print(Panel("[bold cyan]🔄 MODE SWITCHER[/bold cyan]", border_style="cyan"))
    console.print()

    # Show mode comparison
    table = Table(box=box.DOUBLE_EDGE, border_style="cyan", padding=(0, 2))
    table.add_column("Feature", style="bold")
    table.add_column("LIGHT Mode", justify="center")
    table.add_column("FULL Mode", justify="center")

    light_active = " [bold yellow]<< ACTIVE[/bold yellow]" if current == "light" else ""
    full_active = " [bold green]<< ACTIVE[/bold green]" if current == "full" else ""

    table.add_row("Market Watch",     "[green]YES[/green]", "[green]YES[/green]")
    table.add_row("Portfolio",        "[green]YES[/green]", "[green]YES[/green]")
    table.add_row("Manual Trading",   "[green]YES[/green]", "[green]YES[/green]")
    table.add_row("Order Book",       "[green]YES[/green]", "[green]YES[/green]")
    table.add_row("Candle Charts",    "[green]YES[/green]", "[green]YES[/green]")
    table.add_row("Plan Orders",      "[green]YES[/green]", "[green]YES[/green]")
    table.add_row("Web Dashboard",    "[green]YES[/green]", "[green]YES[/green]")
    table.add_row("Grid Bot",         "[red]NO[/red]",      "[green]YES[/green]")
    table.add_row("DCA Bot",          "[red]NO[/red]",      "[green]YES[/green]")
    table.add_row("Scalp Bot",        "[red]NO[/red]",      "[green]YES[/green]")
    table.add_row("Auto-Trading",     "[red]NO[/red]",      "[green]YES[/green]")
    console.print(table)

    current_color = "yellow" if current == "light" else "green"
    console.print(f"\n  Current Mode: [{current_color}][bold]{current.upper()}[/bold][/{current_color}]")
    console.print()

    console.print("  [1] Switch to [bold yellow]LIGHT[/bold yellow] mode (manual only)")
    console.print("  [2] Switch to [bold green]FULL[/bold green] mode  (auto-trading enabled)")
    console.print("  [0] Keep current & go back")
    console.print()

    choice = Prompt.ask("  Select mode", choices=["1", "2", "0"], default="0")

    if choice == "0":
        return

    new_mode = "light" if choice == "1" else "full"

    if new_mode == current:
        console.print(f"  [dim]Already in {current.upper()} mode.[/dim]")
        input("\n  [Press Enter to return] ")
        return

    # Confirmation for FULL mode
    if new_mode == "full":
        console.print()
        console.print(Panel(
            "[bold yellow]WARNING:[/bold yellow] FULL mode enables auto-trading bots.\n"
            "Strategies can place REAL orders with REAL money.\n"
            "Make sure you understand the risks before enabling.",
            border_style="yellow",
            title="[bold]Confirm Mode Change[/bold]"
        ))
        if not Confirm.ask("  [yellow]Switch to FULL AUTO mode?[/yellow]"):
            console.print("  [dim]Cancelled.[/dim]")
            input("\n  [Press Enter to return] ")
            return

    TRADE_MODE = new_mode
    save_config()

    mode_color = "green" if new_mode == "full" else "yellow"
    mode_label = "FULL AUTO" if new_mode == "full" else "LIGHT"
    console.print()
    console.print(Panel(
        f"[bold {mode_color}]Mode switched to {mode_label}![/bold {mode_color}]\n"
        f"[dim]Configuration saved to disk — persists between restarts.[/dim]",
        border_style=mode_color
    ))
    input("\n  [Press Enter to return] ")


def quick_mode_toggle():
    """Quick toggle from main menu."""
    global TRADE_MODE
    old = TRADE_MODE
    new = "full" if old == "light" else "light"

    if new == "full":
        # Require confirmation for full mode
        interactive_mode_switch()
    else:
        TRADE_MODE = new
        save_config()
        console.print(f"[yellow]✓ Switched to LIGHT mode[/yellow]")
        time.sleep(1)


# ═══════════════════════════════════════════════════
# MAIN LOOP
# ═══════════════════════════════════════════════════

def main():
    global api, dashboard

    clear()
    show_banner()

    # Load persistent config
    load_config()

    # Validate credentials
    if not API_KEY or not SECRET_KEY or not PASSPHRASE:
        console.print("[red]✗ Missing API credentials! Check your .env file.[/red]")
        sys.exit(1)

    # Initialize API client
    with console.status("[cyan]⚡ Initializing NITRO TRADER..."):
        api = BitgetAPI(API_KEY, SECRET_KEY, PASSPHRASE)
        time.sleep(0.5)

        # Test connection
        server_time = api.get_server_time()
        if not server_time["success"]:
            console.print(f"[yellow]⚠ Server time check: {server_time['msg']}[/yellow]")
        else:
            console.print(f"[green]✓ Connected to Bitget API[/green]")

        # Test auth
        api_info = api.get_api_info()
        if api_info["success"]:
            console.print(f"[green]✓ Authenticated — API Key valid[/green]")
        else:
            console.print(f"[yellow]⚠ Auth test: {api_info['msg']}[/yellow]")

        # Start web dashboard
        if ENABLE_WEB:
            dashboard = WebDashboard(api, WEB_PORT)
            dashboard.start()
            console.print(f"[green]✓ Web Dashboard running at http://0.0.0.0:{WEB_PORT}[/green]")

    console.print()
    time.sleep(1)

    # Main loop
    while True:
        try:
            clear()
            show_banner()
            show_status_bar()
            console.print()
            show_main_menu()
            console.print()

            choice = Prompt.ask(
                "[bold cyan]⚡ Enter command[/bold cyan]",
                choices=["1", "2", "3", "4", "5", "6", "7", "8", "9", "m", "0"],
                default="1"
            )

            if choice == "1":
                market_watch()
            elif choice == "2":
                portfolio()
            elif choice == "3":
                orders()
            elif choice == "4":
                trade()
            elif choice == "5":
                plan_orders()
            elif choice == "6":
                candle_chart()
            elif choice == "7":
                order_book()
            elif choice == "8":
                strategy_menu()
            elif choice == "9":
                settings()
            elif choice == "m":
                quick_mode_toggle()
            elif choice == "0":
                if Confirm.ask("[yellow]Exit NITRO TRADER?[/yellow]"):
                    # Cleanup
                    for name, strat in strategies.items():
                        strat.stop()
                    console.print("[bold cyan]⚡ NITRO TRADER — See you next time![/bold cyan]")
                    sys.exit(0)

        except KeyboardInterrupt:
            console.print("\n[yellow]Use option [0] to exit properly.[/yellow]")
            time.sleep(1)
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            time.sleep(2)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="NITRO TRADER - Bitget Trading Bot")
    parser.add_argument("--headless", action="store_true",
                        help="Run in headless mode (web dashboard only, no interactive CLI)")
    args = parser.parse_args()

    if args.headless:
        # ═══ HEADLESS MODE (for systemd / VPS background) ═══
        load_dotenv()
        load_config()
        console.print("[bold cyan]NITRO TRADER v2.0 — Headless Mode[/bold cyan]")

        if not API_KEY or not SECRET_KEY or not PASSPHRASE:
            console.print("[red]Missing API credentials in .env![/red]")
            sys.exit(1)

        api = BitgetAPI(API_KEY, SECRET_KEY, PASSPHRASE)
        console.print("[green]✓ API client initialized[/green]")

        # Start web dashboard
        if ENABLE_WEB:
            dashboard = WebDashboard(api, WEB_PORT)
            dashboard.start()
            console.print(f"[green]✓ Web Dashboard: http://0.0.0.0:{WEB_PORT}[/green]")

        console.print("[green]✓ Headless mode active — Ctrl+C to stop[/green]")

        # Keep alive with clean shutdown
        def signal_handler(sig, frame):
            console.print("\n[yellow]Shutting down...[/yellow]")
            for name, strat in strategies.items():
                strat.stop()
            sys.exit(0)

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

        try:
            while True:
                time.sleep(60)
        except (KeyboardInterrupt, SystemExit):
            console.print("[cyan]NITRO TRADER stopped.[/cyan]")
    else:
        # ═══ INTERACTIVE MODE (normal CLI) ═══
        main()
