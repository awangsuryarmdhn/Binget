# ⚡ NITRO TRADER — Bitget Trading Bot v2.0

A full-featured Bitget spot trading bot with a premium interactive CLI and VPS-accessible web dashboard.

## 🚀 One-Command VPS Install

```bash
# SSH into your VPS, then:
git clone https://github.com/YOUR_USER/Binget.git ~/nitro-trader
cd ~/nitro-trader
sudo bash install.sh
```

The installer will:
- ✅ Install Python 3, pip, git, tmux
- ✅ Create isolated virtual environment
- ✅ Install all dependencies
- ✅ Prompt for your API keys
- ✅ Setup systemd auto-restart service
- ✅ Open firewall port 8888
- ✅ Create `./nitro` management CLI

## 📋 Management Commands

```bash
./nitro start       # Start interactive CLI
./nitro start-bg    # Run as background service (auto-restart)
./nitro tmux        # Start in tmux session (recommended)
./nitro stop        # Stop background service
./nitro restart     # Restart service
./nitro status      # Check service status
./nitro logs        # Follow live logs
./nitro update      # Pull latest from GitHub & update deps
```

## 🔄 Interactive Mode Switcher

Press `m` in the main menu to toggle between modes:

| Mode | Features |
|------|----------|
| **LIGHT** | Market watch, manual trading, charts, order book |
| **FULL AUTO** | Everything + Grid Bot, DCA Bot, Scalp Bot |

Mode changes are **persistent** — saved to `bot_state.json`.

Switching to FULL mode requires explicit confirmation (real money warning).

## 📊 All Features

| # | Feature | Description |
|---|---------|-------------|
| 1 | Market Watch | Live prices, top gainers/losers, recent trades |
| 2 | Portfolio | Real-time balances & API key info |
| 3 | Orders | Open orders, history, cancel single/all |
| 4 | Trade | Market & limit buy/sell with confirmations |
| 5 | Plan Orders | Stop-limit & trigger orders |
| 6 | Candle Chart | ASCII candlestick visualization |
| 7 | Order Book | Visual depth bars + spread analysis |
| 8 | Strategies | Grid / DCA / Scalp auto-trading bots |
| 9 | Settings | Change symbol, toggle mode, test API |
| m | Mode Toggle | Quick LIGHT ↔ FULL switch |
| 0 | Exit | Clean shutdown |

## 🌐 VPS Web Dashboard

Access remotely at `http://YOUR_VPS_IP:8888`:
- Real-time portfolio & BTC price
- Quick buy/sell buttons
- Order management
- Auto-refresh every 15s
- Dark mode UI

## ⚙️ Configuration (.env)

```env
BITGET_API_KEY=your_api_key
BITGET_SECRET_KEY=your_secret_key
BITGET_PASSPHRASE=your_passphrase
DEFAULT_SYMBOL=BTCUSDT_SPBL
TRADE_MODE=light
WEB_DASHBOARD_PORT=8888
ENABLE_WEB_DASHBOARD=true
```

## 📁 Project Structure

```
Binget/
├── bot.py                  # Main CLI application
├── core/
│   ├── auth.py             # HMAC-SHA256 signature engine
│   ├── api.py              # Full REST API client (50+ endpoints)
│   ├── websocket_client.py # Real-time WebSocket streams
│   ├── strategies.py       # Auto-trading strategies (Grid/DCA/Scalp)
│   └── dashboard.py        # Flask web dashboard
├── install.sh              # VPS one-command auto-installer
├── start.bat               # Windows launcher
├── start.sh                # Linux launcher
├── .env                    # API credentials (gitignored)
├── bot_state.json          # Persistent config (gitignored)
└── requirements.txt        # Python dependencies
```

## 🔒 Security

- API credentials in `.env` (gitignored, `chmod 600`)
- HMAC-SHA256 signed requests
- FULL mode requires explicit confirmation
- Built-in rate limiting (10 req/s)
- 3x retry logic with 30s timeout

## 📊 Supported Pairs

All Bitget spot pairs: `BTCUSDT_SPBL`, `ETHUSDT_SPBL`, `SOLUSDT_SPBL`, etc.

---
**NITRO TRADER v2.0** — Built for speed, designed for traders. ⚡
