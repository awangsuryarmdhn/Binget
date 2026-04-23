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
<title>NITRO TRADER — Bitget Dashboard</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0a0e17;color:#e0e6ed;font-family:'Segoe UI',system-ui,sans-serif;min-height:100vh}
.header{background:linear-gradient(135deg,#0d1117 0%,#161b22 100%);border-bottom:1px solid #21262d;padding:16px 24px;display:flex;align-items:center;gap:16px}
.header h1{font-size:20px;background:linear-gradient(90deg,#58a6ff,#bc8cff);-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-weight:700}
.badge{background:#238636;color:#fff;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:600}
.badge.offline{background:#da3633}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:16px;padding:20px}
.card{background:#161b22;border:1px solid #21262d;border-radius:12px;padding:20px;transition:transform .2s}
.card:hover{transform:translateY(-2px);border-color:#388bfd50}
.card h3{font-size:13px;text-transform:uppercase;letter-spacing:1.5px;color:#8b949e;margin-bottom:12px}
.stat{font-size:28px;font-weight:700;color:#58a6ff}
.stat.green{color:#3fb950}
.stat.red{color:#f85149}
.stat.gold{color:#d29922}
table{width:100%;border-collapse:collapse;margin-top:10px}
th{text-align:left;color:#8b949e;font-size:11px;text-transform:uppercase;letter-spacing:1px;padding:8px;border-bottom:1px solid #21262d}
td{padding:8px;font-size:13px;border-bottom:1px solid #21262d20}
.buy{color:#3fb950}.sell{color:#f85149}
.actions{padding:20px;display:flex;gap:12px;flex-wrap:wrap}
.btn{padding:10px 20px;border:1px solid #21262d;background:#21262d;color:#e0e6ed;border-radius:8px;cursor:pointer;font-size:13px;transition:all .2s}
.btn:hover{background:#30363d;border-color:#388bfd}
.btn.primary{background:#238636;border-color:#238636}.btn.primary:hover{background:#2ea043}
.btn.danger{background:#da3633;border-color:#da3633}.btn.danger:hover{background:#f85149}
.input{background:#0d1117;border:1px solid #21262d;color:#e0e6ed;padding:8px 12px;border-radius:6px;font-size:13px}
.input:focus{outline:none;border-color:#388bfd}
.footer{text-align:center;padding:20px;color:#484f58;font-size:12px;border-top:1px solid #21262d}
#log{background:#0d1117;border:1px solid #21262d;border-radius:8px;padding:12px;margin:0 20px;height:200px;overflow-y:auto;font-family:'Cascadia Code',monospace;font-size:12px;color:#7ee787}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.5}}
.live{animation:pulse 2s infinite;color:#3fb950;font-size:10px}
</style>
</head>
<body>
<div class="header">
  <h1>⚡ NITRO TRADER</h1>
  <span class="badge" id="status">CONNECTING...</span>
  <span class="live">● LIVE</span>
  <span style="flex:1"></span>
  <span style="color:#8b949e;font-size:12px" id="clock"></span>
</div>

<div class="grid" id="stats">
  <div class="card"><h3>💰 Portfolio Value</h3><div class="stat gold" id="portfolio">—</div></div>
  <div class="card"><h3>📊 XAUT/USDT</h3><div class="stat" id="btc-price">—</div></div>
  <div class="card"><h3>📈 24h Change</h3><div class="stat" id="change-24h">—</div></div>
  <div class="card"><h3>🔄 Open Orders</h3><div class="stat" id="open-orders">—</div></div>
</div>

<div class="grid">
  <div class="card">
    <h3>💼 Balances</h3>
    <table id="balances"><tr><th>Coin</th><th>Available</th><th>Frozen</th><th>Value (USDT)</th></tr></table>
  </div>
  <div class="card">
    <h3>📋 Recent Orders</h3>
    <table id="orders"><tr><th>Time</th><th>Side</th><th>Symbol</th><th>Price</th><th>Qty</th><th>Status</th></tr></table>
  </div>
</div>

<div class="actions">
  <input class="input" id="i-symbol" placeholder="Symbol (e.g. XAUTUSDT)" value="XAUTUSDT" style="width:200px">
  <input class="input" id="i-qty" placeholder="Quantity" style="width:120px">
  <input class="input" id="i-price" placeholder="Price (limit)" style="width:120px">
  <button class="btn primary" onclick="quickBuy()">🟢 BUY</button>
  <button class="btn danger" onclick="quickSell()">🔴 SELL</button>
  <button class="btn" onclick="cancelAll()">❌ Cancel All</button>
  <button class="btn" onclick="refreshAll()">🔄 Refresh</button>
</div>

<div id="log"></div>
<div class="footer">NITRO TRADER v2.0 — Bitget Spot Trading Bot — VPS Remote Dashboard</div>

<script>
const API = window.location.origin + '/api';
const log = (msg, type='info') => {
  const el = document.getElementById('log');
  const t = new Date().toLocaleTimeString();
  const colors = {info:'#8b949e',success:'#3fb950',error:'#f85149',trade:'#d29922'};
  el.innerHTML += `<div style="color:${colors[type]||'#8b949e'}">[${t}] ${msg}</div>`;
  el.scrollTop = el.scrollHeight;
};
setInterval(()=>{document.getElementById('clock').textContent=new Date().toLocaleString()},1000);

async function fetchJSON(url, opts={}) {
  try { const r = await fetch(url, opts); return await r.json(); }
  catch(e) { log('Request failed: '+e, 'error'); return null; }
}

async function refreshAll() {
  log('Refreshing dashboard...');
  // Ticker — V2 returns array in data, use first element
  const t = await fetchJSON(API+'/ticker?symbol=XAUTUSDT');
  if(t&&t.success&&t.data){
    // V2: data could be array or single object
    const td = Array.isArray(t.data) ? t.data[0] : t.data;
    if(td){
      document.getElementById('btc-price').textContent='$'+parseFloat(td.lastPr||td.close||0).toLocaleString();
      const ch = parseFloat(td.change24h||td.changeUtc24h||td.change||0) * 100;
      const el = document.getElementById('change-24h');
      el.textContent = (ch>=0?'+':'')+ch.toFixed(2)+'%';
      el.className = 'stat '+(ch>=0?'green':'red');
    }
  }
  // Balances
  const b = await fetchJSON(API+'/assets');
  if(b&&b.success&&b.data){
    const tb = document.getElementById('balances');
    let html = '<tr><th>Coin</th><th>Available</th><th>Frozen</th><th>Value</th></tr>';
    let total = 0;
    const assets = Array.isArray(b.data) ? b.data : [];
    assets.filter(a=>parseFloat(a.available||0)>0||parseFloat(a.frozen||0)>0).forEach(a=>{
      html += `<tr><td>${a.coin||a.coinName||'—'}</td><td>${parseFloat(a.available||0).toFixed(6)}</td><td>${parseFloat(a.frozen||0).toFixed(6)}</td><td>—</td></tr>`;
    });
    tb.innerHTML = html;
  }
  // Open orders
  const o = await fetchJSON(API+'/open-orders?symbol=XAUTUSDT');
  if(o&&o.success){
    const orders = Array.isArray(o.data) ? o.data : [];
    document.getElementById('open-orders').textContent = orders.length;
    if(orders.length > 0){
      const tb = document.getElementById('orders');
      let html = '<tr><th>Time</th><th>Side</th><th>Symbol</th><th>Price</th><th>Qty</th><th>Status</th></tr>';
      orders.slice(0,10).forEach(x=>{
        const cls = x.side==='buy'?'buy':'sell';
        html += `<tr><td>${new Date(parseInt(x.cTime||x.ctime)).toLocaleString()}</td><td class="${cls}">${x.side.toUpperCase()}</td><td>${x.symbol}</td><td>${x.price||x.priceAvg||'—'}</td><td>${x.size||x.quantity||'—'}</td><td>${x.status||'—'}</td></tr>`;
      });
      tb.innerHTML = html;
    }
  }
  document.getElementById('status').textContent = 'ONLINE';
  document.getElementById('status').className = 'badge';
  log('Dashboard refreshed', 'success');
}

async function quickBuy() {
  const sym = document.getElementById('i-symbol').value;
  const qty = document.getElementById('i-qty').value;
  const price = document.getElementById('i-price').value;
  if(!sym||!qty){log('Fill symbol and quantity','error');return;}
  const body = {symbol:sym, side:'buy', quantity:qty};
  if(price) body.price = price;
  body.orderType = price ? 'limit' : 'market';
  const r = await fetchJSON(API+'/order', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  if(r&&r.success) log('BUY order placed!','trade');
  else log('Order failed: '+(r?r.msg:'unknown'),'error');
  setTimeout(refreshAll, 1000);
}

async function quickSell() {
  const sym = document.getElementById('i-symbol').value;
  const qty = document.getElementById('i-qty').value;
  const price = document.getElementById('i-price').value;
  if(!sym||!qty){log('Fill symbol and quantity','error');return;}
  const body = {symbol:sym, side:'sell', quantity:qty};
  if(price) body.price = price;
  body.orderType = price ? 'limit' : 'market';
  const r = await fetchJSON(API+'/order', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  if(r&&r.success) log('SELL order placed!','trade');
  else log('Order failed: '+(r?r.msg:'unknown'),'error');
  setTimeout(refreshAll, 1000);
}

async function cancelAll() {
  const sym = document.getElementById('i-symbol').value;
  const r = await fetchJSON(API+'/cancel-all', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({symbol:sym})});
  if(r&&r.success) log('All orders cancelled','success');
  else log('Cancel failed','error');
  setTimeout(refreshAll, 1000);
}

// Auto-refresh
refreshAll();
setInterval(refreshAll, 15000);
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
