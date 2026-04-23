#!/bin/bash
# VPS Quick Start Script
echo "⚡ NITRO TRADER — Starting on VPS..."
echo "Web Dashboard will be available at http://$(hostname -I | awk '{print $1}'):8888"
echo ""
python3 bot.py
