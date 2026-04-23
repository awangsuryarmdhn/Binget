import threading
import time
from flask import Flask, render_template_string, jsonify, request
from flask_cors import CORS

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>NITRO GENESIS PRO</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=JetBrains+Mono&display=swap" rel="stylesheet">
    <script src="https://unpkg.com/lightweight-charts/dist/lightweight-charts.standalone.production.js"></script>
    <style>
        :root {
            --bg: #06090f; --card: rgba(13, 17, 23, 0.9);
            --accent: #00f2ff; --purple: #bc8cff;
            --buy: #00d18e; --sell: #ff3b69;
            --border: rgba(255, 255, 255, 0.1);
        }
        * { margin:0; padding:0; box-sizing:border-box; }
        body { background: var(--bg); color: #c9d1d9; font-family:'Inter',sans-serif; overflow: hidden; height: 100vh; display:flex; flex-direction:column; }
        
        /* Pulse Animation */
        @keyframes pulse { 0% { opacity: 0.4; } 50% { opacity: 1; } 100% { opacity: 0.4; } }
        .heartbeat { width: 10px; height: 10px; background: var(--buy); border-radius: 50%; display: inline-block; box-shadow: 0 0 10px var(--buy); animation: pulse 1.5s infinite; }

        .header { height: 65px; background: #000; border-bottom: 1px solid var(--border); display:flex; align-items:center; justify-content:space-between; padding: 0 25px; z-index: 10; }
        .header h1 { font-size: 1.1rem; font-weight: 800; background: linear-gradient(90deg, #fff, var(--accent)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        
        .main { display: flex; flex: 1; overflow: hidden; }
        .sidebar { width: 330px; border-right: 1px solid var(--border); background: #0d1117; display:flex; flex-direction:column; }
        .viewport { flex: 1; display:flex; flex-direction:column; background: #000; }
        
        /* Stats & Chart */
        #chart { flex: 1; background: #000; }
        .stats-top { display:flex; gap:30px; font-size:0.8rem; font-weight:600; }
        
        .control-panel { height: 380px; display: grid; grid-template-columns: 1fr 1fr 1.2fr; gap: 20px; padding: 20px; background: #06090f; border-top: 1px solid var(--border); }
        .panel { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 18px; display:flex; flex-direction:column; }
        .panel h3 { font-size: 0.75rem; color: #8b949e; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 15px; border-bottom: 1px solid var(--border); padding-bottom: 5px; }

        input, select { background: #000; border: 1px solid var(--border); color: #fff; padding: 12px; border-radius: 6px; margin-bottom: 10px; width: 100%; font-family:'JetBrains Mono'; font-size: 0.85rem; }
        input:focus { border-color: var(--accent); outline:none; }
        
        .btn { padding: 12px; border:none; border-radius: 6px; font-weight:800; cursor:pointer; text-transform:uppercase; transition: 0.2s; }
        .btn-buy { background: var(--buy); color: #000; }
        .btn-sell { background: var(--sell); color: #fff; }
        .btn-auto { background: linear-gradient(135deg, var(--accent), var(--purple)); color: #000; width: 100%; }
        .btn:hover { filter: brightness(1.2); transform: scale(1.02); }

        .tabs { display:flex; gap:5px; padding:15px; }
        .tab { flex:1; text-align:center; padding:10px; font-size:0.7rem; font-weight:800; cursor:pointer; background: #161b22; border-radius: 6px; color: #8b949e; }
        .tab.active { background: var(--accent); color: #000; }
        
        .asset-list { flex:1; overflow-y:auto; padding:0 15px; }
        .asset-item { display:flex; justify-content:space-between; padding:12px; border-bottom: 1px solid var(--border); }
        .coin-name { font-weight: 700; color: #fff; }
        .coin-val { font-family: 'JetBrains Mono'; color: var(--accent); font-size: 0.85rem; }

        #log-box { background: #000; flex:1; font-family: 'JetBrains Mono'; font-size: 0.7rem; color: #8b949e; overflow-y:auto; border-radius: 8px; padding: 10px; border: 1px solid #161b22; }
    </style>
</head>
<body>
    <div class="header">
        <div style="display:flex; align-items:center; gap:12px">
            <div class="heartbeat"></div>
            <h1>NITRO GENESIS PRO</h1>
        </div>
        <div class="stats-top">
            <div id="p-sym" style="color:#fff">XAUTUSDT</div>
            <div id="p-price" style="color:var(--accent)">$0.00</div>
            <div id="p-change" style="color:var(--buy)">+0.00%</div>
        </div>
        <div>
            <button class="btn" style="background:#21262d; font-size:0.7rem; padding: 5px 15px" onclick="openXf()">TRANSFER</button>
        </div>
    </div>

    <div class="main">
        <div class="sidebar">
            <div class="tabs">
                <div class="tab active" id="btn-spot" onclick="setMode('spot')">SPOT</div>
                <div class="tab" id="btn-futures" onclick="setMode('futures')">FUTURES</div>
            </div>
            <div class="asset-list" id="assets-list">
                <div style="text-align:center; padding:20px; color:#555">Loading Balances...</div>
            </div>
        </div>

        <div class="viewport">
            <div id="chart"></div>
            <div class="control-panel">
                <div class="panel">
                    <h3>Manual Execution</h3>
                    <input type="number" id="manual-size" placeholder="Order Size">
                    <input type="number" id="manual-price" placeholder="Limit Price (Auto Market if empty)">
                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px">
                        <button class="btn btn-buy" onclick="sendOrder('buy')">Buy</button>
                        <button class="btn btn-sell" onclick="sendOrder('sell')">Sell</button>
                    </div>
                </div>
                <div class="panel">
                    <h3>Auto Engine Core</h3>
                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px">
                        <input type="number" id="auto-loops" value="10">
                        <input type="number" id="auto-delay" value="250">
                    </div>
                    <select id="auto-strat">
                        <option value="scalp">Scalping Protocol</option>
                        <option value="dca">DCA Strategy</option>
                    </select>
                    <button class="btn btn-auto" id="auto-btn" onclick="startAuto()">ENGAGE PROTOCOL</button>
                </div>
                <div class="panel">
                    <h3>System Logs</h3>
                    <div id="log-box"></div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let symbol = 'XAUTUSDT';
        let mode = 'spot';
        let chart, candleSeries;

        function addLog(msg, type='') {
            const lb = document.getElementById('log-box');
            lb.innerHTML = `<div style="margin-bottom:4px; ${type=='e'?'color:var(--sell)':''}">[${new Date().toLocaleTimeString()}] ${msg}</div>` + lb.innerHTML;
        }

        async function init() {
            chart = LightweightCharts.createChart(document.getElementById('chart'), {
                layout: { background: { color: '#000' }, textColor: '#8b949e' },
                grid: { vertLines: { color: '#161b22' }, horzLines: { color: '#161b22' } },
                timeScale: { borderColor: '#21262d', timeVisible: true }
            });
            candleSeries = chart.addCandlestickSeries({ upColor: '#00d18e', downColor: '#ff3b69' });
            updateCandles();
            updateStats();
            updateAssets();
            window.addEventListener('resize', () => chart.applyOptions({ width: document.getElementById('chart').clientWidth }));
        }

        async function updateCandles() {
            try {
                const res = await fetch(`/api/candles?symbol=${symbol}`);
                const d = await res.json();
                if(d.data) {
                    candleSeries.setData(d.data.map(c => ({
                        time: parseInt(c[0])/1000, 
                        open:parseFloat(c[1]), high:parseFloat(c[2]), low:parseFloat(c[3]), close:parseFloat(c[4])
                    })));
                } else { addLog("Chart sync failure", "e"); }
            } catch(e) {}
        }

        async function updateStats() {
            try {
                const res = await fetch(`/api/ticker?symbol=${symbol}`);
                const d = await res.json();
                if(d.data && d.data[0]) {
                    const t = d.data[0];
                    document.getElementById('p-price').textContent = '$' + parseFloat(t.lastPr).toLocaleString();
                    const ch = (parseFloat(t.change24h)||0) * 100;
                    document.getElementById('p-change').textContent = (ch>=0?'+':'') + ch.toFixed(2) + '%';
                    document.getElementById('p-change').style.color = ch >= 0 ? 'var(--buy)' : 'var(--sell)';
                }
            } catch(e) {}
        }

        async function updateAssets() {
            try {
                const url = mode === 'spot' ? '/api/assets' : '/api/assets-futures';
                const res = await fetch(url);
                const d = await res.json();
                const list = document.getElementById('assets-list');
                list.innerHTML = '';
                if(d.data) {
                    d.data.filter(a => parseFloat(a.available||a.availableBalance) > 0).forEach(a => {
                        list.innerHTML += `<div class="asset-item"><span class="coin-name">${a.coin||a.symbol}</span><span class="coin-val">${parseFloat(a.available||a.availableBalance).toFixed(4)}</span></div>`;
                    });
                }
            } catch(e) {}
        }

        async function sendOrder(side) {
            const size = document.getElementById('manual-size').value;
            const px = document.getElementById('manual-price').value;
            if(!size) return alert("Enter size!");
            
            addLog(`Sending ${side.toUpperCase()} order...`);
            const res = await fetch('/api/order', {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({symbol, side, size, price: px})
            });
            const d = await res.json();
            if(d.success) addLog("Order Filled Success!", "s");
            else addLog("Error: " + d.msg, "e");
            updateAssets();
        }

        function setMode(m) {
            mode = m;
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.getElementById('btn-'+m).classList.add('active');
            updateAssets();
        }

        init();
        setInterval(updateStats, 2000);
        setInterval(updateCandles, 5000);
        setInterval(updateAssets, 10000);
    </script>
</body>
</html>
"""

class WebDashboard:
    def __init__(self, bitget_api, port=8888):
        self.app = Flask(__name__)
        self.api = bitget_api
        self.port = port
        CORS(self.app)
        self._setup_routes()

    def _setup_routes(self):
        @self.app.route("/")
        def index():
            return render_template_string(DASHBOARD_HTML)

        @self.app.route("/api/ticker")
        def ticker():
            sym = request.args.get("symbol", "XAUTUSDT")
            return jsonify(self.api.get_ticker(sym))

        @self.app.route("/api/candles")
        def candles():
            sym = request.args.get("symbol", "XAUTUSDT")
            return jsonify(self.api.get_candles(sym))

        @self.app.route("/api/assets")
        def assets():
            return jsonify(self.api.get_assets())

        @self.app.route("/api/assets-futures")
        def futures():
            return jsonify(self.api.get_futures_assets())

        @self.app.route("/api/order", methods=["POST"])
        def post_order():
            d = request.json
            return jsonify(self.api.place_order(symbol=d['symbol'], side=d['side'], size=d['size'], price=d.get('price')))

    def start(self, ssl=False):
        kwargs = {"host": "0.0.0.0", "port": self.port, "debug": False}
        if ssl: kwargs["ssl_context"] = "adhoc"
        threading.Thread(target=lambda: self.app.run(**kwargs), daemon=True).start()
