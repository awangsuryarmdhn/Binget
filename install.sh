#!/bin/bash
# ╔══════════════════════════════════════════════════════════════╗
# ║  NITRO TRADER — VPS Auto-Installer                         ║
# ║  One-command setup for Ubuntu/Debian VPS                    ║
# ╚══════════════════════════════════════════════════════════════╝
#
# Usage:
#   curl -sSL https://raw.githubusercontent.com/YOUR_USER/Binget/main/install.sh | bash
#   OR
#   wget -qO- https://raw.githubusercontent.com/YOUR_USER/Binget/main/install.sh | bash
#   OR
#   bash install.sh
#
set -e

# ─── Colors ──────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ─── Config ──────────────────────────────────────
INSTALL_DIR="$HOME/nitro-trader"
REPO_URL="https://github.com/YOUR_USER/Binget.git"
PYTHON_MIN="3.10"
SERVICE_NAME="nitro-trader"

print_banner() {
    echo -e "${CYAN}${BOLD}"
    echo "    _   _ ___ _____ ____   ___    _____ ____      _    ____  _____ ____  "
    echo '   | \ | |_ _|_   _|  _ \ / _ \  |_   _|  _ \   / \  |  _ \| ____|  _ \ '
    echo '   |  \| || |  | | | |_) | | | |   | | | |_) | / _ \ | | | |  _| | |_) |'
    echo '   | |\  || |  | | |  _ <| |_| |   | | |  _ < / ___ \| |_| | |___|  _ < '
    echo '   |_| \_|___|_|_| |_| \_\\___/    |_| |_| \_/_/   \_|____/|_____|_| \_\'
    echo -e "${NC}"
    echo -e "${CYAN}              VPS Auto-Installer v2.0${NC}"
    echo ""
}

log_step() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[!]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

log_info() {
    echo -e "${CYAN}[>]${NC} $1"
}

# ─── Check Root ──────────────────────────────────
check_root() {
    if [ "$EUID" -eq 0 ]; then
        log_warn "Running as root — will install for root user"
    fi
}

# ─── Detect OS ───────────────────────────────────
detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
        VER=$VERSION_ID
    elif [ -f /etc/debian_version ]; then
        OS="debian"
    elif [ -f /etc/redhat-release ]; then
        OS="centos"
    else
        OS="unknown"
    fi
    log_step "Detected OS: $OS $VER"
}

# ─── Install System Dependencies ─────────────────
install_deps() {
    log_info "Installing system dependencies..."
    
    case $OS in
        ubuntu|debian)
            apt-get update -qq
            apt-get install -y -qq python3 python3-pip python3-venv git tmux curl wget > /dev/null 2>&1
            ;;
        centos|rhel|fedora|rocky|alma)
            yum install -y python3 python3-pip git tmux curl wget > /dev/null 2>&1
            ;;
        arch|manjaro)
            pacman -Sy --noconfirm python python-pip git tmux > /dev/null 2>&1
            ;;
        *)
            log_warn "Unknown OS — trying apt-get..."
            apt-get update -qq && apt-get install -y -qq python3 python3-pip python3-venv git tmux > /dev/null 2>&1
            ;;
    esac
    
    log_step "System dependencies installed"
}

# ─── Check Python Version ────────────────────────
check_python() {
    if command -v python3 &> /dev/null; then
        PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
        log_step "Python $PY_VER found"
    else
        log_error "Python3 not found! Installing..."
        install_deps
    fi
}

# ─── Clone/Update Repository ─────────────────────
setup_repo() {
    if [ -d "$INSTALL_DIR" ]; then
        log_info "Updating existing installation..."
        cd "$INSTALL_DIR"
        git pull --ff-only 2>/dev/null || {
            log_warn "Git pull failed — doing fresh clone"
            cd "$HOME"
            rm -rf "$INSTALL_DIR"
            git clone "$REPO_URL" "$INSTALL_DIR"
        }
    else
        log_info "Cloning repository..."
        git clone "$REPO_URL" "$INSTALL_DIR"
    fi
    cd "$INSTALL_DIR"
    log_step "Repository ready at $INSTALL_DIR"
}

# ─── Setup Python Virtual Environment ────────────
setup_venv() {
    log_info "Setting up Python virtual environment..."
    
    if [ ! -d "$INSTALL_DIR/venv" ]; then
        python3 -m venv "$INSTALL_DIR/venv"
    fi
    
    source "$INSTALL_DIR/venv/bin/activate"
    pip install --upgrade pip -q
    pip install -r "$INSTALL_DIR/requirements.txt" -q
    
    log_step "Python dependencies installed"
}

# ─── Setup Environment File ──────────────────────
setup_env() {
    if [ -f "$INSTALL_DIR/.env" ]; then
        log_step ".env file exists — keeping current config"
        return
    fi
    
    echo ""
    echo -e "${BOLD}${CYAN}═══ API CONFIGURATION ═══${NC}"
    echo ""
    
    read -p "  Bitget API Key: " API_KEY
    read -p "  Bitget Secret Key: " SECRET_KEY
    read -p "  Bitget Passphrase: " PASSPHRASE
    read -p "  Default Symbol [BTCUSDT_SPBL]: " SYMBOL
    SYMBOL=${SYMBOL:-BTCUSDT_SPBL}
    read -p "  Trade Mode (light/full) [light]: " MODE
    MODE=${MODE:-light}
    read -p "  Web Dashboard Port [8888]: " PORT
    PORT=${PORT:-8888}
    
    cat > "$INSTALL_DIR/.env" << EOF
# NITRO TRADER — Auto-generated config
BITGET_API_KEY=$API_KEY
BITGET_SECRET_KEY=$SECRET_KEY
BITGET_PASSPHRASE=$PASSPHRASE
BITGET_API_URL=https://api.bitget.com
DEFAULT_SYMBOL=$SYMBOL
TRADE_MODE=$MODE
WEB_DASHBOARD_PORT=$PORT
ENABLE_WEB_DASHBOARD=true
EOF
    
    chmod 600 "$INSTALL_DIR/.env"
    log_step ".env file created with secure permissions"
}

# ─── Setup Firewall ──────────────────────────────
setup_firewall() {
    if command -v ufw &> /dev/null; then
        log_info "Configuring firewall..."
        ufw allow 8888/tcp > /dev/null 2>&1 || true
        log_step "Port 8888 opened in UFW"
    elif command -v firewall-cmd &> /dev/null; then
        firewall-cmd --permanent --add-port=8888/tcp > /dev/null 2>&1 || true
        firewall-cmd --reload > /dev/null 2>&1 || true
        log_step "Port 8888 opened in firewalld"
    else
        log_warn "No firewall detected — make sure port 8888 is open"
    fi
}

# ─── Create Systemd Service ──────────────────────
create_service() {
    log_info "Creating systemd service..."
    
    PYTHON_PATH="$INSTALL_DIR/venv/bin/python3"
    
    cat > /etc/systemd/system/${SERVICE_NAME}.service << EOF
[Unit]
Description=NITRO TRADER - Bitget Trading Bot
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=$INSTALL_DIR
ExecStart=$PYTHON_PATH $INSTALL_DIR/bot.py
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    systemctl enable ${SERVICE_NAME} > /dev/null 2>&1
    
    log_step "Systemd service created and enabled"
}

# ─── Create Management Scripts ───────────────────
create_scripts() {
    # Start script
    cat > "$INSTALL_DIR/nitro" << 'SCRIPT'
#!/bin/bash
# NITRO TRADER — Management CLI
INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE="nitro-trader"

case "$1" in
    start)
        echo "Starting NITRO TRADER..."
        source "$INSTALL_DIR/venv/bin/activate"
        cd "$INSTALL_DIR"
        python3 bot.py
        ;;
    start-bg)
        echo "Starting NITRO TRADER in background..."
        systemctl start $SERVICE
        echo "Started! Web dashboard: http://$(hostname -I | awk '{print $1}'):8888"
        ;;
    stop)
        echo "Stopping NITRO TRADER..."
        systemctl stop $SERVICE
        echo "Stopped."
        ;;
    restart)
        echo "Restarting..."
        systemctl restart $SERVICE
        echo "Restarted! Web: http://$(hostname -I | awk '{print $1}'):8888"
        ;;
    status)
        systemctl status $SERVICE
        ;;
    logs)
        journalctl -u $SERVICE -f --no-pager
        ;;
    tmux)
        echo "Starting in tmux session..."
        source "$INSTALL_DIR/venv/bin/activate"
        cd "$INSTALL_DIR"
        tmux new-session -d -s nitro "python3 bot.py"
        echo "Started in tmux! Attach with: tmux attach -t nitro"
        echo "Web dashboard: http://$(hostname -I | awk '{print $1}'):8888"
        ;;
    update)
        echo "Updating NITRO TRADER..."
        cd "$INSTALL_DIR"
        git pull
        source "$INSTALL_DIR/venv/bin/activate"
        pip install -r requirements.txt -q
        echo "Updated! Restart with: ./nitro restart"
        ;;
    *)
        echo ""
        echo "  NITRO TRADER — Management CLI"
        echo "  ────────────────────────────────"
        echo "  Usage: ./nitro <command>"
        echo ""
        echo "  Commands:"
        echo "    start      Start interactive CLI"
        echo "    start-bg   Start as background service"
        echo "    stop       Stop background service"
        echo "    restart    Restart background service"
        echo "    status     Show service status"
        echo "    logs       Follow live logs"
        echo "    tmux       Start in tmux session"
        echo "    update     Update from GitHub"
        echo ""
        ;;
esac
SCRIPT
    
    chmod +x "$INSTALL_DIR/nitro"
    
    # Create symlink for global access
    ln -sf "$INSTALL_DIR/nitro" /usr/local/bin/nitro 2>/dev/null || true
    
    log_step "Management scripts created"
}

# ─── Print Summary ───────────────────────────────
print_summary() {
    IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "YOUR_VPS_IP")
    
    echo ""
    echo -e "${GREEN}${BOLD}══════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}${BOLD}  NITRO TRADER — Installation Complete!${NC}"
    echo -e "${GREEN}${BOLD}══════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "  ${BOLD}Install Location:${NC}  $INSTALL_DIR"
    echo -e "  ${BOLD}Web Dashboard:${NC}     http://$IP:8888"
    echo ""
    echo -e "  ${CYAN}${BOLD}Quick Start Commands:${NC}"
    echo -e "  ──────────────────────────────────────"
    echo -e "  ${GREEN}./nitro start${NC}       Start interactive CLI"
    echo -e "  ${GREEN}./nitro start-bg${NC}    Run as background service"
    echo -e "  ${GREEN}./nitro tmux${NC}        Start in tmux (recommended)"
    echo -e "  ${GREEN}./nitro logs${NC}        View live logs"
    echo -e "  ${GREEN}./nitro update${NC}      Pull latest from GitHub"
    echo ""
    echo -e "  ${YELLOW}Tip: Use 'tmux attach -t nitro' to reconnect${NC}"
    echo ""
}

# ═══════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════

print_banner
check_root
detect_os
install_deps
check_python
setup_repo
setup_venv
setup_env
setup_firewall

# Only create systemd service if running as root
if [ "$EUID" -eq 0 ]; then
    create_service
else
    log_warn "Not root — skipping systemd service (use ./nitro tmux instead)"
fi

create_scripts
print_summary
