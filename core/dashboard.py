import threading
from flask import Flask, render_template_string, jsonify, request
from flask_cors import CORS

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>NITRO GENESIS — Bitget Pro Hub</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=JetBrains+Mono&display=swap" rel="stylesheet">
    <script src="https://unpkg.com/lightweight-charts/dist/lightweight-charts.standalone.production.js"></script>
    <style>
        :root {
            --bg: #06090f;
            --card: rgba(13, 17, 23, 0.7);
            --accent: #00f2ff;
            --purple: #bc8cff;
            --buy: #00d18e;
            --sell: #ff3b69;
            --border: rgba(255, 255, 255, 0.08);
            --glass: blur(12px);
        }
        * { margin:0; padding:0; box-sizing:border-box; font-family:'Inter', sans-serif; }
        body { background: var(--bg); color: #c9d1d9; overflow: hidden; height: 100vh; display: flex; flex-direction: column; }
        
        .header {
            height: 60px; background: rgba(0,0,0,0.5); backdrop-filter: var(--glass);
            border-bottom: 1px solid var(--border); padding: 0 24px;
            display: flex; align-items: center; justify-content: space-between;
        }
        .header h1 { font-size: 1.2rem; font-weight: 800; letter-spacing: -0.5px; background: linear-gradient(90deg, #fff, var(--accent)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        
        .main-layout { display: flex; flex: 1; overflow: hidden; }
        .sidebar { width: 320px; border-right: 1px solid var(--border); display: flex; flex-direction: column; background: rgba(0,0,0,0.2); }
        .viewport { flex: 1; display: flex; flex-direction: column; background: #000; position: relative; }
        
        .search-box { padding: 15px; border-bottom: 1px solid var(--border); }
        .search-input { width: 100%; background: #161b22; border: 1px solid var(--border); padding: 10px; border-radius: 8px; color: var(--accent); font-family: 'JetBrains Mono'; }
        
        .tabs { display: flex; padding: 10px; gap: 5px; }
        .tab { flex: 1; padding: 10px; text-align: center; font-size: 0.7rem; font-weight: 700; cursor: pointer; border-radius: 6px; background: rgba(255,255,255,0.03); color: #8b949e; }
        .tab.active { background: var(--accent); color: #000; }
        
        .asset-list { flex: 1; overflow-y: auto; padding: 10px; }
        .asset-item { display: flex; justify-content: space-between; padding: 12px; border-radius: 8px; margin-bottom: 5px; background: var(--card); border: 1px solid transparent; cursor: pointer; }
        .asset-item:hover { border-color: var(--accent); }
        .asset-name { font-weight: 700; color: #fff; font-size: 0.9rem; }
        .asset-balance { font-family: 'JetBrains Mono'; font-size: 0.8rem; color: var(--accent); text-align: right; }

        #chart { flex: 1; border-bottom: 1px solid var(--border); }
        
        .control-bar { height: 350px; display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px; padding: 20px; background: var(--bg); }
        .panel h3 { font-size: 0.7rem; color: #8b949e; margin-bottom: 15px; }
        
        input, select { width: 100%; background: #0d1117; border: 1px solid var(--border); color: #fff; padding: 10px; border-radius: 6px; margin-bottom: 10px; font-size: 0.85rem; }
        
        .btn { padding: 12px; border: none; border-radius: 6px; font-weight: 800; cursor: pointer; text-transform: uppercase; transition: 0.2s; }
        .btn-buy { background: var(--buy); color: #000; }
        .btn-sell { background: var(--sell); color: #fff; }
        .btn-auto { background: linear-gradient(135deg, var(--accent), var(--purple)); color: #000; }

        .modal { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.8); backdrop-filter: blur(5px); z-index: 1000; align-items: center; justify-content: center; }
        .modal-content { background: var(--bg); width: 400px; padding: 30px; border: 1px solid var(--border); border-radius: 16px; }

        #log { background: #000; color: #8b949e; font-family: 'JetBrains Mono'; font-size: 0.7rem; padding: 10px; overflow-y: auto; height: 120px; border: 1px solid var(--border); border-radius: 8px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>NITRO ⚡ GENESIS PRO</h1>
        <div style="display:flex; gap:20px; font-size: 0.8rem;">
            <span id="p-price" style="color:var(--accent); font-weight:800">--</span>
            <span id="p-change" style="color:var(--buy)">0.00%</span>
        </div>
        <div style="display:flex; gap:10px">
            <button class="btn" style="padding: 5px 15px; font-size: 0.7rem; background:#21262d" onclick="openTransfer()">Transfer</button>
        </div>
    </div>

    <div class="main-layout">
        <div class="sidebar">
            <div class="search-box"><input type="text" class="search-input" id="s-input" placeholder="Search Symbols..."></div>
            <div class="tabs">
                <div class="tab active" id="t-spot" onclick="setAccount('spot')">SPOT</div>
                <div class="tab" id="t-futures" onclick="setAccount('futures')">FUTURES</div>
            </div>
            <div class="asset-list" id="asset-list"></div>
        </div>
        <div class="viewport">
            <div id="chart"></div>
            <div class="control-bar">
                <div class="panel">
                    <h3>Lightning Order <span id="c-sym" style="color:var(--accent)">XAUTUSDT</span></h3>
                    <input type="number" id="o-qty" placeholder="Size">
                    <input type="number" id="o-price" placeholder="Price (Market if empty)">
                    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:10px">
                        <button class="btn btn-buy" onclick="trade('buy')">Buy</button>
                        <button class="btn btn-sell" onclick="trade('sell')">Sell</button>
                    </div>
                </div>
                <div class="panel">
                    <h3>Auto-Genesis Core</h3>
                    <input type="number" id="a-loops" value="10" placeholder="Loops">
                    <input type="number" id="a-delay" value="250" placeholder="Delay MS">
                    <button class="btn btn-auto" style="width:100%" onclick="startAuto()">Engage Auto Protocol</button>
                </div>
                <div class="panel">
                    <h3>Execution Logs</h3>
                    <div id="log"></div>
                </div>
            </div>
        </div>
    </div>

    <div class="modal" id="transfer-modal">
        <div class="modal-content">
            <h2 style="color:#fff; margin-bottom:20px">Internal Transfer</h2>
            <select id="xf-from"><option value="spot">Spot Account</option><option value="mix">Futures Account</option></select>
            <div style="text-align:center; color:var(--accent); margin:10px">⬇</div>
            <select id="xf-to"><option value="mix">Futures Account</option><option value="spot">Spot Account</option></select>
            <input type="text" id="xf-coin" value="USDT">
            <input type="number" id="xf-amt" placeholder="Amount">
            <div style="display:flex; gap:10px; margin-top:20px">
                <button class="btn btn-auto" style="flex:1" onclick="doTransfer()">Transfer</button>
                <button class="btn" style="background:#30363d" onclick="closeTransfer()">Cancel</button>
            </div>
        </div>
    </div>

    <script>
        let currentSym = 'XAUTUSDT';
        let accountType = 'spot';
        let chart, candleSeries;

        function log(m, t='') {
            const l = document.getElementById('log');
            l.innerHTML = `<div>[${new Date().toLocaleTimeString()}] ${m}</div>` + l.innerHTML;
        }

        function initChart() {
            chart = LightweightCharts.createChart(document.getElementById('chart'), {
                layout: { background: { color: '#000' }, textColor: '#8b949e' },
                grid: { vertLines: { color: '#161b22' }, horzLines: { color: '#161b22' } },
                timeScale: { borderColor: '#21262d', timeVisible: true }
            });
            candleSeries = chart.addCandlestickSeries({ upColor: '#00d18e', downColor: '#ff3b69' });
            updateCandles();
        }

        async function updateCandles() {
            const res = await fetch(`/api/candles?symbol=${currentSym}`);
            const d = await res.json();
            if(d.data) {
                candleSeries.setData(d.data.map(c => ({
                    time: parseInt(c[0])/1000, open:parseFloat(c[1]), high:parseFloat(c[2]), low:parseFloat(c[3]), close:parseFloat(c[4])
                })));
            }
        }

        async function refreshAssets() {
            const res = await fetch(accountType === 'spot' ? '/api/assets' : '/api/assets-futures');
            const d = await res.json();
            const list = document.getElementById('asset-list');
            list.innerHTML = '';
            if(d.data) {
                d.data.filter(a => parseFloat(a.available||a.availableBalance) > 0).forEach(a => {
                    list.innerHTML += `<div class="asset-item"><div class="asset-name">${a.coin||a.symbol}</div><div class="asset-balance">${parseFloat(a.available||a.availableBalance).toFixed(2)}</div></div>`;
                });
            }
        }

        async function refreshTicker() {
            const res = await fetch(`/api/ticker?symbol=${currentSym}`);
            const d = await res.json();
            if(d.data && d.data[0]) {
                const t = d.data[0];
                document.getElementById('p-price').textContent = `$${parseFloat(t.lastPr).toLocaleString()}`;
            }
        }

        function setAccount(t) {
            accountType = t;
            document.querySelectorAll('.tab').forEach(e => e.classList.remove('active'));
            document.getElementById('t-'+t).classList.add('active');
            refreshAssets();
        }

        function openTransfer() { document.getElementById('transfer-modal').style.display='flex'; }
        function closeTransfer() { document.getElementById('transfer-modal').style.display='none'; }

        async function trade(side) {
            const qty = document.getElementById('o-qty').value;
            const px = document.getElementById('o-price').value;
            const res = await fetch('/api/order', {
                method:'POST', headers:{'Content-Type':'application/json'},
                body: JSON.stringify({symbol:currentSym, side, size:qty, price:px})
            });
            const d = await res.json();
            if(d.success) log(side.toUpperCase() + " Success");
            else log(d.msg);
        }

        async function doTransfer() {
            const body = {
                from: document.getElementById('xf-from').value,
                to: document.getElementById('xf-to').value,
                coin: document.getElementById('xf-coin').value,
                amount: document.getElementById('xf-amt').value
            };
            const res = await fetch('/api/transfer', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)});
            const d = await res.json();
            if(d.success) { log("Transfer Success"); closeTransfer(); refreshAssets(); }
        }

        initChart();
        setInterval(refreshTicker, 2000);
        setInterval(updateCandles, 10000);
        refreshAssets();
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
        def index(): return render_template_string(DASHBOARD_HTML)

        @self.app.route("/api/ticker")
        def ticker(): return jsonify(self.api.get_ticker(request.args.get("symbol", "XAUTUSDT")))

        @self.app.route("/api/candles")
        def candles(): return jsonify(self.api.get_candles(request.args.get("symbol", "XAUTUSDT")))

        @self.app.route("/api/assets")
        def assets(): return jsonify(self.api.get_assets())

        @self.app.route("/api/assets-futures")
        def futures(): return jsonify(self.api.get_futures_assets())

        @self.app.route("/api/transfer", methods=["POST"])
        def transfer():
            d = request.json
            return jsonify(self.api.internal_transfer(d['from'], d['to'], d['coin'], d['amount']))

        @self.app.route("/api/order", methods=["POST"])
        def order():
            d = request.json
            return jsonify(self.api.place_order(symbol=d['symbol'], side=d['side'], size=d['size'], price=d.get('price')))

    def start(self, ssl=False):
        kwargs = {"host": "0.0.0.0", "port": self.port, "debug": False}
        if ssl: kwargs["ssl_context"] = "adhoc"
        threading.Thread(target=lambda: self.app.run(**kwargs), daemon=True).start()
