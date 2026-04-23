#!/bin/bash
# ╔══════════════════════════════════════════════════════════════╗
# ║  NITRO TRADER — VPS Quick Setup                            ║
# ║  Coexists with other services (openclaw, etc.)             ║
# ╚══════════════════════════════════════════════════════════════╝
#
# Usage:  bash setup_vps.sh
#
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="nitro-trader"

echo -e "${CYAN}${BOLD}"
echo "  ================================================="
echo "   NITRO TRADER — VPS Setup (No Conflict Mode)"
echo "  ================================================="
echo -e "${NC}"

# ─── Step 1: Check for port conflicts ────────────
echo -e "${CYAN}[1/6]${NC} Checking for port conflicts..."

DEFAULT_PORT=8888
PORT=$DEFAULT_PORT

# Check if port 8888 is in use (by openclaw or anything else)
if command -v ss &> /dev/null; then
    if ss -tlnp 2>/dev/null | grep -q ":${DEFAULT_PORT} "; then
        echo -e "${YELLOW}[!] Port ${DEFAULT_PORT} is already in use (possibly openclaw)${NC}"
        # Find next free port
        for p in 8889 8890 9000 9001 9090 7777; do
            if ! ss -tlnp 2>/dev/null | grep -q ":${p} "; then
                PORT=$p
                break
            fi
        done
        echo -e "${GREEN}[✓] Using port ${PORT} instead${NC}"
    else
        echo -e "${GREEN}[✓] Port ${DEFAULT_PORT} is free${NC}"
    fi
elif command -v netstat &> /dev/null; then
    if netstat -tlnp 2>/dev/null | grep -q ":${DEFAULT_PORT} "; then
        PORT=8889
        echo -e "${YELLOW}[!] Port ${DEFAULT_PORT} in use, using ${PORT}${NC}"
    else
        echo -e "${GREEN}[✓] Port ${DEFAULT_PORT} is free${NC}"
    fi
fi

# ─── Step 2: Install dependencies ────────────────
echo -e "${CYAN}[2/6]${NC} Installing dependencies..."

if command -v apt-get &> /dev/null; then
    sudo apt-get update -qq 2>/dev/null
    sudo apt-get install -y -qq python3 python3-pip python3-venv tmux 2>/dev/null
elif command -v yum &> /dev/null; then
    sudo yum install -y python3 python3-pip tmux 2>/dev/null
fi
echo -e "${GREEN}[✓] System dependencies ready${NC}"

# ─── Step 3: Setup venv ──────────────────────────
echo -e "${CYAN}[3/6]${NC} Setting up Python environment..."

if [ ! -d "$INSTALL_DIR/venv" ]; then
    python3 -m venv "$INSTALL_DIR/venv"
fi

source "$INSTALL_DIR/venv/bin/activate"
pip install --upgrade pip -q 2>/dev/null
pip install -r "$INSTALL_DIR/requirements.txt" -q 2>/dev/null
echo -e "${GREEN}[✓] Python dependencies installed${NC}"

# ─── Step 4: Setup .env ──────────────────────────
echo -e "${CYAN}[4/6]${NC} Configuring API credentials..."

if [ -f "$INSTALL_DIR/.env" ]; then
    echo -e "${GREEN}[✓] .env file already exists${NC}"
    echo -e "${YELLOW}    Edit with: nano $INSTALL_DIR/.env${NC}"
else
    echo ""
    echo -e "${BOLD}  Enter your Bitget API credentials:${NC}"
    echo ""
    read -p "  API Key: " API_KEY
    read -p "  Secret Key: " SECRET_KEY
    read -p "  Passphrase: " PASSPHRASE
    read -p "  Default Symbol [BTCUSDT_SPBL]: " SYMBOL
    SYMBOL=${SYMBOL:-BTCUSDT_SPBL}
    read -p "  Trade Mode (light/full) [light]: " MODE
    MODE=${MODE:-light}

    cat > "$INSTALL_DIR/.env" << EOF
# ══════════════════════════════════════════════════
# BITGET API CREDENTIALS
# ══════════════════════════════════════════════════
BITGET_API_KEY=${API_KEY}
BITGET_SECRET_KEY=${SECRET_KEY}
BITGET_PASSPHRASE=${PASSPHRASE}

# ══════════════════════════════════════════════════
# BOT SETTINGS
# ══════════════════════════════════════════════════
BITGET_API_URL=https://api.bitget.com
DEFAULT_SYMBOL=${SYMBOL}
TRADE_MODE=${MODE}

# ══════════════════════════════════════════════════
# VPS / REMOTE ACCESS
# ══════════════════════════════════════════════════
WEB_DASHBOARD_PORT=${PORT}
ENABLE_WEB_DASHBOARD=true
EOF

    chmod 600 "$INSTALL_DIR/.env"
    echo -e "${GREEN}[✓] .env created with secure permissions (chmod 600)${NC}"
fi

# ─── Step 5: Create systemd service ──────────────
echo -e "${CYAN}[5/6]${NC} Creating systemd service..."

PYTHON_PATH="$INSTALL_DIR/venv/bin/python3"
CURRENT_USER=$(whoami)

# Create service file (won't conflict with openclaw)
sudo tee /etc/systemd/system/${SERVICE_NAME}.service > /dev/null << EOF
[Unit]
Description=NITRO TRADER - Bitget Trading Bot
After=network-online.target
Wants=network-online.target
# Explicit: does NOT conflict with other services
Conflicts=

[Service]
Type=simple
User=${CURRENT_USER}
Group=${CURRENT_USER}
WorkingDirectory=${INSTALL_DIR}
ExecStart=${PYTHON_PATH} ${INSTALL_DIR}/bot.py --headless
Restart=always
RestartSec=15
StartLimitBurst=5
StartLimitIntervalSec=60
Environment=PYTHONUNBUFFERED=1
Environment=PYTHONIOENCODING=utf-8
StandardOutput=journal
StandardError=journal
SyslogIdentifier=${SERVICE_NAME}

# Resource limits (prevent eating all RAM)
MemoryMax=512M
CPUQuota=50%

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable ${SERVICE_NAME} 2>/dev/null
echo -e "${GREEN}[✓] Systemd service '${SERVICE_NAME}' created${NC}"

# ─── Step 6: Open firewall ───────────────────────
echo -e "${CYAN}[6/6]${NC} Configuring firewall..."

if command -v ufw &> /dev/null; then
    sudo ufw allow ${PORT}/tcp 2>/dev/null && echo -e "${GREEN}[✓] UFW: Port ${PORT} opened${NC}" || true
elif command -v firewall-cmd &> /dev/null; then
    sudo firewall-cmd --permanent --add-port=${PORT}/tcp 2>/dev/null
    sudo firewall-cmd --reload 2>/dev/null
    echo -e "${GREEN}[✓] Firewalld: Port ${PORT} opened${NC}"
fi

# ─── Show other running services ─────────────────
echo ""
echo -e "${CYAN}${BOLD}  ═══ RUNNING SERVICES CHECK ═══${NC}"

# Check for openclaw
if systemctl is-active --quiet openclaw 2>/dev/null; then
    OPENCLAW_PORT=$(ss -tlnp 2>/dev/null | grep openclaw | grep -oP ':\K\d+' | head -1)
    echo -e "  ${GREEN}● openclaw${NC}       running on port ${OPENCLAW_PORT:-unknown}"
elif pgrep -f openclaw > /dev/null 2>&1; then
    echo -e "  ${GREEN}● openclaw${NC}       running (process found)"
else
    echo -e "  ${YELLOW}○ openclaw${NC}       not detected"
fi

echo -e "  ${GREEN}● ${SERVICE_NAME}${NC}  port ${PORT} (web dashboard)"
echo ""

# ─── Print summary ───────────────────────────────
IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "YOUR_VPS_IP")

echo -e "${GREEN}${BOLD}══════════════════════════════════════════════════${NC}"
echo -e "${GREEN}${BOLD}  NITRO TRADER — Setup Complete!${NC}"
echo -e "${GREEN}${BOLD}══════════════════════════════════════════════════${NC}"
echo ""
echo -e "  ${BOLD}Dashboard:${NC}  http://${IP}:${PORT}"
echo ""
echo -e "  ${BOLD}Commands:${NC}"
echo -e "  ──────────────────────────────────────────"
echo -e "  ${GREEN}sudo systemctl start ${SERVICE_NAME}${NC}    Start bot"
echo -e "  ${GREEN}sudo systemctl stop ${SERVICE_NAME}${NC}     Stop bot"
echo -e "  ${GREEN}sudo systemctl restart ${SERVICE_NAME}${NC}  Restart bot"
echo -e "  ${GREEN}sudo systemctl status ${SERVICE_NAME}${NC}   Check status"
echo -e "  ${GREEN}journalctl -u ${SERVICE_NAME} -f${NC}        Live logs"
echo ""
echo -e "  ${YELLOW}The bot auto-restarts on crash (15s delay)${NC}"
echo -e "  ${YELLOW}The bot auto-starts on VPS reboot${NC}"
echo -e "  ${YELLOW}No conflicts with openclaw or other services${NC}"
echo ""
echo -e "  ${CYAN}Start now?${NC}"
read -p "  Start NITRO TRADER service? (y/n): " START_NOW
if [ "$START_NOW" = "y" ] || [ "$START_NOW" = "Y" ]; then
    sudo systemctl start ${SERVICE_NAME}
    sleep 2
    if systemctl is-active --quiet ${SERVICE_NAME}; then
        echo -e "  ${GREEN}[✓] NITRO TRADER is running!${NC}"
        echo -e "  ${GREEN}    Dashboard: http://${IP}:${PORT}${NC}"
    else
        echo -e "  ${RED}[!] Service didn't start. Check logs:${NC}"
        echo -e "  ${RED}    journalctl -u ${SERVICE_NAME} -n 20${NC}"
    fi
fi
echo ""
