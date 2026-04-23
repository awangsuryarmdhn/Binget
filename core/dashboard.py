"""
╔══════════════════════════════════════════════════════════════╗
║  BITGET WEB DASHBOARD                                       ║
║  Remote VPS access via Flask REST API + Web UI              ║
╚══════════════════════════════════════════════════════════════╝
"""

import json
import threading
from datetime import datetime
from flask import Flask, jsonify, request, render_template_string
from flask_cors import CORS

# Inline HTML dashboard template
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>NITRO TRADER — Bitget Pro Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=JetBrains+Mono&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #0a0e17;
            --card-bg: rgba(22, 27, 34, 0.8);
            --accent: #00f2ff;
            --purple: #bc8cff;
            --buy: #00d18e;
            --sell: #ff3b69;
            --border: rgba(255, 255, 255, 0.1);
        }
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Inter', sans-serif; }
        body { background: var(--bg); color: #e0e6ed; overflow-x: hidden; }
        
        /* Glassmorphism Header */
        .header {
            background: rgba(13, 17, 23, 0.9);
            backdrop-filter: blur(10px);
            border-bottom: 1px solid var(--border);
            padding: 1rem 2rem;
            display: flex;
            align-items: center;
            position: sticky;
            top: 0;
            z-index: 100;
        }
        .header h1 { font-size: 1.5rem; background: linear-gradient(90deg, var(--accent), var(--purple)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .status-badge { background: var(--buy); color: #000; padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; font-weight: 800; margin-left: 10px; }

        .container { display: grid; grid-template-columns: 1fr 350px; gap: 20px; padding: 20px; max-width: 1600px; margin: auto; }
        .main-col { display: flex; flex-direction: column; gap: 20px; }
        
        .card { background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px; padding: 20px; backdrop-filter: blur(5px); }
        .card h2 { font-size: 0.8rem; text-transform: uppercase; letter-spacing: 2px; color: #8b949e; margin-bottom: 15px; display: flex; align-items: center; gap: 8px; }
        
        /* Stats Grid */
        .stats-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; }
        .stat-val { font-size: 1.8rem; font-weight: 700; color: #fff; }
        .stat-label { font-size: 0.7rem; color: #8b949e; }

        /* Auto-Trade Panel */
        .trade-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
        .input-group { margin-bottom: 15px; }
        .input-group label { display: block; font-size: 0.65rem; color: #8b949e; margin-bottom: 5px; }
        input { width: 100%; background: #0d1117; border: 1px solid var(--border); color: #fff; padding: 10px; border-radius: 6px; font-family: 'JetBrains Mono', monospace; font-size: 0.9rem; }
        input:focus { border-color: var(--accent); outline: none; }

        .btn-row { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
        .btn { padding: 12px; border: none; border-radius: 6px; font-weight: 700; cursor: pointer; transition: 0.3s; text-transform: uppercase; font-size: 0.8rem; }
        .btn-buy { background: var(--buy); color: #000; }
        .btn-sell { background: var(--sell); color: #fff; }
        .btn-auto { background: var(--purple); color: #000; grid-column: span 2; margin-top: 10px; }
        .btn:hover { filter: brightness(1.2); transform: scale(1.02); }

        /* Logs Console */
        #console { 
            background: #000; 
            border: 1px solid var(--border); 
            height: 300px; 
            border-radius: 8px; 
            padding: 15px; 
            font-family: 'JetBrains Mono', monospace; 
            font-size: 0.75rem; 
            overflow-y: auto;
            color: #a0a0a0;
        }
        .log-entry { margin-bottom: 4px; border-left: 2px solid #333; padding-left: 8px; }
        .log-time { color: #58a6ff; font-weight: bold; }
        .log-success { color: var(--buy); }
        .log-error { color: var(--sell); }

        table { width: 100%; border-collapse: collapse; }
        th { text-align: left; font-size: 0.7rem; color: #8b949e; padding: 10px; border-bottom: 1px solid var(--border); }
        td { padding: 10px; font-size: 0.8rem; border-bottom: 1px solid rgba(255,255,255,0.05); }
    </style>
</head>
<body>
    <div class="header">
        <h1>NITRO ⚡ TRADER</h1>
        <span class="status-badge" id="bot-status">PRO LIVE</span>
        <div style="flex:1"></div>
        <div id="price-ticker" style="font-family: 'JetBrains Mono'; color: var(--accent); font-weight: bold;">--</div>
    </div>

    <div class="container">
        <div class="main-col">
            <div class="stats-grid">
                <div class="card"><div class="stat-label">PORTFOLIO (USDT)</div><div class="stat-val" id="total-val">0.00</div></div>
                <div class="card"><div class="stat-label">24H CHANGE</div><div id="change24" class="stat-val">0.00%</div></div>
                <div class="card"><div class="stat-label">AVG EXEC SPEED</div><div class="stat-val" style="color:var(--purple)">42ms</div></div>
            </div>

            <div class="card" style="flex:1">
                <h2>📊 ASSETS & LIVE BALANCES</h2>
                <table id="balance-table">
                    <thead><tr><th>Coin</th><th>Available</th><th>Frozen</th><th>Value (USDT)</th></tr></thead>
                    <tbody></tbody>
                </table>
            </div>

            <div id="console"></div>
        </div>

        <div class="side-col">
            <div class="card">
                <h2>⚡ LIGHTNING TRADE</h2>
                <div class="input-group">
                    <label>TRADING SYMBOL</label>
                    <input type="text" id="symbol" value="XAUTUSDT">
                </div>
                <div class="trade-grid">
                    <div class="input-group">
                        <label>QUANTITY</label>
                        <input type="number" id="qty" placeholder="0.0">
                    </div>
                    <div class="input-group">
                        <label>LIMIT PRICE (OPT)</label>
                        <input type="number" id="price" placeholder="Market">
                    </div>
                </div>
                <div class="btn-row">
                    <button class="btn btn-buy" onclick="trade('buy')">Buy</button>
                    <button class="btn btn-sell" onclick="trade('sell')">Sell</button>
                </div>
            </div>

            <div class="card" style="margin-top:20px; border-color: var(--purple)">
                <h2 style="color: var(--purple)">🤖 AUTO-GENESIS ENGINE</h2>
                <div class="input-group">
                    <label>LOOP COUNT (ITERATIONS)</label>
                    <input type="number" id="loops" value="10">
                </div>
                <div class="input-group">
                    <label>DELAY BETWEEN (MS)</label>
                    <input type="number" id="delay" value="200">
                </div>
                <div class="input-group">
                    <label>ANTI-FRAUD JITTER (%)</label>
                    <input type="number" id="jitter" value="5">
                </div>
                <button class="btn btn-auto" id="auto-btn" onclick="startAutoTrade()">Engage Auto-Loop</button>
            </div>
        </div>
    </div>

    <script>
        let isAutoTrading = false;
        const consoleEl = document.getElementById('console');

        function log(msg, type='info') {
            const time = new Date().toLocaleTimeString();
            const div = document.createElement('div');
            div.className = `log-entry log-${type}`;
            div.innerHTML = `<span class="log-time">[${time}]</span> ${msg}`;
            consoleEl.prepend(div);
        }

        async function trade(side, isAuto=false) {
            const sym = document.getElementById('symbol').value;
            const qty = document.getElementById('qty').value;
            const price = document.getElementById('price').value;
            
            if(!qty && !isAuto) return log("Invalid Quantity", "error");

            try {
                const res = await fetch('/api/order', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        symbol: sym,
                        side: side,
                        size: qty,
                        orderType: price ? 'limit' : 'market',
                        price: price || ""
                    })
                });
                const data = await res.json();
                if(data.success) {
                    log(`${side.toUpperCase()} Filled: ${qty} ${sym}`, "success");
                    return true;
                } else {
                    log(`${side.toUpperCase()} Failed: ${data.msg}`, "error");
                    return false;
                }
            } catch(e) { log("Network Error", "error"); return false; }
        }

        async function startAutoTrade() {
            if(isAutoTrading) {
                isAutoTrading = false;
                return;
            }
            const count = parseInt(document.getElementById('loops').value);
            const delay = parseInt(document.getElementById('delay').value);
            const jitter = parseInt(document.getElementById('jitter').value);
            const side = confirm("Buy/Sell Loop? (OK = BUY, CANCEL = SELL)") ? 'buy' : 'sell';

            isAutoTrading = true;
            document.getElementById('auto-btn').textContent = "STOP AUTO-ENGINE";
            log(`⚡ Genesis Engine Started: ${count} loops`, "info");

            for(let i=0; i<count; i++) {
                if(!isAutoTrading) break;
                
                const randomDelay = delay + (Math.random() * delay * (jitter/100));
                await trade(side, true);
                
                log(`Loop ${i+1}/${count} complete. Jitter delay: ${Math.round(randomDelay)}ms`);
                await new Promise(r => setTimeout(r, randomDelay));
            }
            
            isAutoTrading = false;
            document.getElementById('auto-btn').textContent = "Engage Auto-Loop";
            log("🌌 Auto-Trade Sequence Finalized", "success");
        }

        async function refresh() {
            const sym = document.getElementById('symbol').value;
            try {
                const res = await fetch(`/api/ticker?symbol=${sym}`);
                const d = await res.json();
                if(d.data && d.data[0]) {
                    document.getElementById('price-ticker').textContent = `${sym}: $${parseFloat(d.data[0].lastPr).toLocaleString()}`;
                    document.getElementById('change24').textContent = (d.data[0].change24h * 100).toFixed(2) + "%";
                }
                
                const assets = await fetch('/api/assets');
                const aData = await assets.json();
                const tbody = document.querySelector('#balance-table tbody');
                tbody.innerHTML = '';
                aData.data.forEach(a => {
                    if(parseFloat(a.available) > 0) {
                        tbody.innerHTML += `<tr><td>${a.coin}</td><td>${a.available}</td><td>${a.frozen}</td><td>--</td></tr>`;
                    }
                });
            } catch(e){}
        }

        setInterval(refresh, 3000);
        refresh();
    </script>
</body>
</html>
"""


class WebDashboard:
    """Flask-based web dashboard for VPS remote access."""

    def __init__(self, api_client, port: int = 8888):
        self.api = api_client
        self.port = port
        self.app = Flask(__name__)
        CORS(self.app)
        self._setup_routes()
        self._thread = None

    def _setup_routes(self):
        app = self.app
        api = self.api

        @app.route("/")
        def dashboard():
            return render_template_string(DASHBOARD_HTML)

        @app.route("/api/ticker")
        def api_ticker():
            symbol = request.args.get("symbol", "BTCUSDT_SPBL")
            return jsonify(api.get_ticker(symbol))

        @app.route("/api/all-tickers")
        def api_all_tickers():
            return jsonify(api.get_all_tickers())

        @app.route("/api/depth")
        def api_depth():
            symbol = request.args.get("symbol", "BTCUSDT_SPBL")
            limit = int(request.args.get("limit", 20))
            return jsonify(api.get_depth(symbol, limit))

        @app.route("/api/assets")
        def api_assets():
            return jsonify(api.get_assets())

        @app.route("/api/open-orders")
        def api_open_orders():
            symbol = request.args.get("symbol", "")
            return jsonify(api.get_open_orders(symbol))

        @app.route("/api/order-history")
        def api_order_history():
            symbol = request.args.get("symbol", "BTCUSDT_SPBL")
            return jsonify(api.get_order_history(symbol))

        @app.route("/api/order", methods=["POST"])
        def api_place_order():
            data = request.json
            return jsonify(api.place_order(
                symbol=data.get("symbol", "BTCUSDT_SPBL"),
                side=data.get("side", "buy"),
                order_type=data.get("orderType", "market"),
                quantity=data.get("quantity", "0"),
                price=data.get("price", ""),
                force=data.get("force", "normal")
            ))

        @app.route("/api/cancel-all", methods=["POST"])
        def api_cancel_all():
            data = request.json
            return jsonify(api.cancel_all_orders(data.get("symbol", "BTCUSDT_SPBL")))

        @app.route("/api/candles")
        def api_candles():
            symbol = request.args.get("symbol", "BTCUSDT_SPBL")
            period = request.args.get("period", "1h")
            limit = request.args.get("limit", "100")
            return jsonify(api.get_candles(symbol, period, limit=int(limit)))

        @app.route("/api/server-time")
        def api_server_time():
            return jsonify(api.get_server_time())

        @app.route("/health")
        def health():
            return jsonify({"status": "ok", "time": datetime.now().isoformat()})

    def start(self):
        """Start web dashboard in background thread."""
        self._thread = threading.Thread(
            target=lambda: self.app.run(
                host="0.0.0.0", port=self.port,
                debug=False, use_reloader=False
            ),
            daemon=True
        )
        self._thread.start()
        return self._thread

    def get_url(self) -> str:
        return f"http://0.0.0.0:{self.port}"
