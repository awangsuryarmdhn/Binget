"""
╔══════════════════════════════════════════════════════════════╗
║  BITGET API AUTHENTICATION & SIGNATURE ENGINE               ║
║  HMAC-SHA256 signature generation per Bitget V1 Spot API    ║
╚══════════════════════════════════════════════════════════════╝
"""

import hmac
import hashlib
import base64
import time
import json
from urllib.parse import urlencode


class BitgetAuth:
    """Handles all authentication and signature generation for Bitget API."""

    def __init__(self, api_key: str, secret_key: str, passphrase: str):
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase

    def get_timestamp(self) -> str:
        """Get current timestamp in milliseconds."""
        return str(int(time.time() * 1000))

    def sign(self, timestamp: str, method: str, request_path: str,
             query_string: str = "", body: str = "") -> str:
        """
        Generate HMAC-SHA256 signature for Bitget API.
        
        Signature format:
          - When queryString is empty:  timestamp + METHOD + requestPath + body
          - When queryString is present: timestamp + METHOD + requestPath + "?" + queryString + body
        """
        method = method.upper()

        if query_string:
            message = f"{timestamp}{method}{request_path}?{query_string}{body}"
        else:
            message = f"{timestamp}{method}{request_path}{body}"

        mac = hmac.new(
            self.secret_key.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        )
        signature = base64.b64encode(mac.digest()).decode('utf-8')
        return signature

    def get_headers(self, method: str, request_path: str,
                    query_string: str = "", body: str = "") -> dict:
        """Generate complete authenticated headers for a request."""
        timestamp = self.get_timestamp()
        signature = self.sign(timestamp, method, request_path, query_string, body)

        return {
            "ACCESS-KEY": self.api_key,
            "ACCESS-SIGN": signature,
            "ACCESS-TIMESTAMP": timestamp,
            "ACCESS-PASSPHRASE": self.passphrase,
            "Content-Type": "application/json",
            "locale": "en-US"
        }

    def get_public_headers(self) -> dict:
        """Headers for public (unauthenticated) endpoints."""
        return {
            "Content-Type": "application/json",
            "locale": "en-US"
        }
