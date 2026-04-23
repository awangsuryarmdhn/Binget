import threading
from flask import Flask, render_template_string, jsonify, request
from flask_cors import CORS

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>NITRO GENESIS PRO | PRECISION v3.0</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;900&family=JetBrains+Mono&display=swap" rel="stylesheet">
    <script src="https://unpkg.com/lightweight-charts/dist/lightweight-charts.standalone.production.js"></script>
    <style>
        :root {
            --bg: #030508; --sidebar: #0a0d14; --card: rgba(22, 27, 34, 0.85);
            --accent: #00f2ff; --purple: #bc8cff; --buy: #00d18e; --sell: #ff3b69; --border: #1d2129;
        }
        * { margin:0; padding:0; box-sizing:border-box; }
        body { background: var(--bg); color: #c9d1d9; font-family:'Inter',sans-serif; overflow: hidden; height: 100vh; display:flex; flex-direction:column; }
        
        .header { height: 55px; background: #000; border-bottom: 1px solid var(--border); display:flex; align-items:center; padding: 0 20px; gap:20px; }
        .header h1 { font-size: 0.95rem; font-weight: 900; background: linear-gradient(90deg, #fff, var(--accent)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        
        .main { display: flex; flex: 1; overflow: hidden; }
        .side-left { width: 280px; background: var(--sidebar); border-right: 1px solid var(--border); display:flex; flex-direction:column; }
        .content { flex: 1; display:flex; flex-direction:column; background: #000; }
        .side-right { width: 340px; background: var(--sidebar); border-left: 1px solid var(--border); padding: 20px; display:flex; flex-direction:column; }

        .ticker-item { padding: 15px; border-bottom: 1px solid #161b22; cursor:pointer; display:flex; justify-content:space-between; }
        .ticker-item.active { background: #0d1117; border-left: 4px solid var(--accent); }
        .t-sym { font-weight:800; font-size:0.8rem; }
        .t-price { font-family:'JetBrains Mono'; font-size:0.75rem; color:var(--accent); }

        #chart { flex: 1; width: 100%; }
        
        .control-panel { height: 350px; display: grid; grid-template-columns: 1.2fr 1fr; gap: 15px; padding: 15px; background: #030508; border-top: 1px solid var(--border); }
        .panel { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 18px; position: relative; }
        .panel h3 { font-size: 0.65rem; color: #8b949e; text-transform: uppercase; margin-bottom: 15px; display:flex; align-items:center; gap:8px; }

        input { background: #000; border: 1px solid var(--border); color: #fff; padding: 12px; border-radius: 6px; width: 100%; font-family:'JetBrains Mono'; font-size: 0.85rem; margin-bottom: 10px; }
        .btn { padding: 12px; border:none; border-radius: 6px; font-weight:900; cursor:pointer; text-transform:uppercase; font-size: 0.8rem; transition: 0.2s; }
        .btn-buy { background: var(--buy); color: #000; }
        .btn-sell { background: var(--sell); color: #fff; }
        .btn-auto { background: linear-gradient(135deg, var(--accent), var(--purple)); color: #000; width:100%; margin-top:10px; }

        .asset-box { background: #0d1117; border: 1px solid var(--border); border-radius: 8px; padding: 12px; margin-bottom: 10px; border-left: 4px solid var(--accent); }
        .asset-row { display:flex; justify-content:space-between; margin-bottom: 5px; }
        .a-coin { font-weight:900; font-size:0.85rem; }
        .a-val { font-family:'JetBrains Mono'; font-size:0.8rem; color: #fff; }
        .a-sub { font-size:0.65rem; color:#555; }

        #log-box { font-family:'JetBrains Mono'; font-size:0.65rem; color:#8b949e; height: 160px; overflow-y:auto; background:#000; border-radius:8px; padding:12px; border:1px solid #161b22; }
    </style>
</head>
<body>
    <div class="header">
        <h1>NITRO GENESIS PRO <span style="font-weight:400">v3.0</span></h1>
        <div id="ws-state" style="font-size:0.65rem; color:var(--buy)">⚡ WS ONLINE</div>
        <div id="top-price" style="font-family:'JetBrains Mono'; font-weight:900; color:var(--accent); font-size:1rem">$0.00</div>
        <div style="flex:1"></div>
        <div id="sync-clock" style="font-size:0.65rem; color:#444">SYNC: 11:40:02</div>
    </div>

    <div class="main">
        <div class="side-left">
            <div style="padding:15px; font-size:0.6rem; letter-spacing:1px; color:#555">MARKET TERMINAL</div>
            <div class="ticker-list" id="ticker-list">
                <div class="ticker-item active" onclick="changeSym('XAUTUSDT', this)">
                    <span class="t-sym">XAUT / USDT</span>
                    <span class="t-price" id="ws-XAUTUSDT">--</span>
                </div>
                <div class="ticker-item" onclick="changeSym('BTCUSDT', this)">
                    <span class="t-sym">BTC / USDT</span>
                    <span class="t-price" id="ws-BTCUSDT">--</span>
                </div>
                <div class="ticker-item" onclick="changeSym('ETHUSDT', this)">
                    <span class="t-sym">ETH / USDT</span>
                    <span class="t-price" id="ws-ETHUSDT">--</span>
                </div>
            </div>
        </div>

        <div class="content">
            <div id="chart"></div>
            <div class="control-panel">
                <div class="panel">
                    <h3>Swift Execution <span style="color:var(--accent)" id="c-sym">XAUTUSDT</span></h3>
                    <input type="number" id="o-size" placeholder="Order Size (e.g. 0.05)">
                    <input type="number" id="o-price" placeholder="Price (Blank = Market)">
                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px">
                        <button class="btn btn-buy" onclick="trade('buy')">Buy</button>
                        <button class="btn btn-sell" onclick="trade('sell')">Sell</button>
                    </div>
                </div>
                <div class="panel">
                    <h3>Terminal Logs</h3>
                    <div id="log-box"></div>
                </div>
            </div>
        </div>

        <div class="side-right">
            <h3>Precision Balances</h3>
            <div id="balance-container" style="flex:1; overflow-y:auto; margin:15px 0">
                <div style="padding:20px; text-align:center; color:#444">Synchronizing...</div>
            </div>
            <div style="border-top:1px solid var(--border); padding-top:15px">
                <button class="btn btn-auto" onclick="startAuto()">ENGAGE ALGO-GENESIS</button>
            </div>
        </div>
    </div>

    <script>
        let symbol = 'XAUTUSDT';
        let ws;
        let chart, candleSeries;

        function addLog(m, e=false) {
            const b = document.getElementById('log-box');
            b.innerHTML = `<div style="margin-bottom:4px; ${e?'color:var(--sell)':''}">[${new Date().toLocaleTimeString()}] ${m}</div>` + b.innerHTML;
        }

        function connectWS() {
            ws = new WebSocket('wss://ws.bitget.com/v2/ws/public');
            ws.onopen = () => {
                ['BTCUSDT', 'ETHUSDT', 'XAUTUSDT'].forEach(s => {
                    ws.send(JSON.stringify({ op: 'subscribe', args: [{instType:'SPOT', channel:'ticker', instId:s}, {instType:'SPOT', channel:'candle1m', instId:s}] }));
                });
                addLog("Lightning WS Latency Optimized.");
            };
            ws.onmessage = (e) => {
                const d = JSON.parse(e.data);
                if(d.data && d.arg) {
                    if(d.arg.channel === 'ticker') {
                        const t = d.data[0];
                        const el = document.getElementById('ws-'+d.arg.instId);
                        if(el) el.textContent = '$' + parseFloat(t.lastPr).toLocaleString();
                        if(d.arg.instId === symbol) {
                            document.getElementById('top-price').textContent = '$' + parseFloat(t.lastPr).toLocaleString();
                        }
                    }
                    if(d.arg.channel === 'candle1m' && d.arg.instId === symbol) {
                        const c = d.data[0];
                        candleSeries.update({ time:parseInt(c[0])/1000, open:parseFloat(c[1]), high:parseFloat(c[2]), low:parseFloat(c[3]), close:parseFloat(c[4]) });
                    }
                }
            };
            ws.onclose = () => setTimeout(connectWS, 2000);
        }

        async function updatePrecisionBalance() {
            try {
                const res = await fetch('/api/assets');
                const d = await res.json();
                const container = document.getElementById('balance-container');
                document.getElementById('sync-clock').textContent = "SYNC: " + new Date().toLocaleTimeString();
                
                if(d.data) {
                    container.innerHTML = '';
                    d.data.filter(a => (parseFloat(a.available) + parseFloat(a.frozen)) > 0).forEach(a => {
                        const total = (parseFloat(a.available) + parseFloat(a.frozen)).toFixed(4);
                        container.innerHTML += `
                            <div class="asset-box">
                                <div class="asset-row">
                                    <span class="a-coin">${a.coin}</span>
                                    <span class="a-val">${total}</span>
                                </div>
                                <div class="asset-row">
                                    <span class="a-sub">Available: ${parseFloat(a.available).toFixed(4)}</span>
                                    <span class="a-sub">Frozen: ${parseFloat(a.frozen).toFixed(4)}</span>
                                </div>
                            </div>`;
                    });
                }
            } catch(e) { console.error(e); }
        }

        async function trade(side) {
            const size = document.getElementById('o-size').value;
            if(!size) return addLog("Execution Aborted: Missing Size", true);
            
            addLog(`Broadcasting ${side.toUpperCase()}...`);
            const res = await fetch('/api/order', {
                method:'POST', headers:{'Content-Type':'application/json'},
                body: JSON.stringify({symbol, side, size, price: document.getElementById('o-price').value})
            });
            const d = await res.json();
            if(d.success) {
                addLog(`Engine: Order Filled.`);
                updatePrecisionBalance(); // Immediate Update on Success
            } else {
                addLog(`Engine Error: ${d.msg}`, true);
            }
        }

        function changeSym(s, el) {
            symbol = s;
            document.querySelectorAll('.ticker-item').forEach(i => i.classList.remove('active'));
            el.classList.add('active');
            document.getElementById('c-sym').textContent = s;
            candleSeries.setData([]);
            fetch(`/api/candles?symbol=${symbol}`).then(r => r.json()).then(d => {
                if(d.data) candleSeries.setData(d.data.map(c => ({time:parseInt(c[0])/1000, open:parseFloat(c[1]), high:parseFloat(c[2]), low:parseFloat(c[3]), close:parseFloat(c[4])})));
            });
        }

        function init() {
            chart = LightweightCharts.createChart(document.getElementById('chart'), {
                layout: { background: { color: '#000' }, textColor: '#8b949e' },
                grid: { vertLines: { color: '#0d1117' }, horzLines: { color: '#0d1117' } },
                timeScale: { borderColor: '#1d2129', timeVisible: true }
            });
            candleSeries = chart.addCandlestickSeries({ upColor: '#00d18e', downColor: '#ff3b69' });
            connectWS();
            updatePrecisionBalance();
            setInterval(updatePrecisionBalance, 3000); // Super Fast Refresh
            window.addEventListener('resize', () => chart.applyOptions({ width: document.getElementById('chart').clientWidth }));
        }

        init();
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
        @self.app.route("/api/candles")
        def candles(): return jsonify(self.api.get_candles(request.args.get("symbol", "XAUTUSDT")))
        @self.app.route("/api/assets")
        def assets(): return jsonify(self.api.get_assets())
        @self.app.route("/api/order", methods=["POST"])
        def order():
            d = request.json
            return jsonify(self.api.place_order(symbol=d['symbol'], side=d['side'], size=d['size'], price=d.get('price')))

    def start(self, ssl=False):
        kwargs = {"host": "0.0.0.0", "port": self.port, "debug": False}
        if ssl: kwargs["ssl_context"] = "adhoc"
        threading.Thread(target=lambda: self.app.run(**kwargs), daemon=True).start()
