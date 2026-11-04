"""TradeLog local MT5 bridge. Read-only: no trading/order APIs are called."""
from __future__ import annotations

import json
import secrets
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

HOST = "127.0.0.1"
PORT = 8765
ALLOWED_ORIGINS = {
    "https://mohamedtpsb16-debug.github.io",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
}
TOKEN = secrets.token_urlsafe(32)


def mt5_module():
    try:
        import MetaTrader5 as mt5
        return mt5
    except ImportError as exc:
        raise RuntimeError("Package MetaTrader5 missing. Run install.bat first.") from exc


def connect():
    mt5 = mt5_module()
    if not mt5.initialize():
        raise RuntimeError(f"MT5 initialization failed: {mt5.last_error()}")
    return mt5


def account_status():
    mt5 = connect()
    try:
        account = mt5.account_info()
        terminal = mt5.terminal_info()
        if account is None:
            raise RuntimeError(f"Cannot read MT5 account: {mt5.last_error()}")
        return {
            "connected": True,
            "terminal_connected": bool(terminal.connected) if terminal else False,
            "trade_allowed": bool(terminal.trade_allowed) if terminal else None,
            "account_login_masked": ("*" * max(0, len(str(account.login)) - 3)) + str(account.login)[-3:],
            "server": str(account.server),
            "currency": str(account.currency),
            "mode": "read_only",
        }
    finally:
        mt5.shutdown()


def read_history(days: int = 90):
    if not 1 <= days <= 365:
        raise ValueError("days must be between 1 and 365")
    mt5 = connect()
    try:
        end = datetime.now()
        start = end - timedelta(days=days)
        deals = mt5.history_deals_get(start, end)
        if deals is None:
            raise RuntimeError(f"MT5 history retrieval failed: {mt5.last_error()}")
        rows = []
        for d in deals:
            rows.append({
                "ticket": int(d.ticket),
                "order": int(d.order),
                "position_id": int(d.position_id),
                "time": int(d.time),
                "time_utc": datetime.fromtimestamp(int(d.time), timezone.utc).isoformat(),
                "symbol": str(d.symbol),
                "type": int(d.type),
                "entry": int(d.entry),
                "volume": float(d.volume),
                "price": float(d.price),
                "commission": float(d.commission),
                "swap": float(d.swap),
                "profit": float(d.profit),
                "fee": float(d.fee),
                "comment": str(d.comment),
                "external_id": str(d.external_id),
            })
        return {"mode": "read_only", "from": start.isoformat(), "to": end.isoformat(),
                "count": len(rows), "deals": rows}
    finally:
        mt5.shutdown()


class Handler(BaseHTTPRequestHandler):
    server_version = "TradeLogLocalBridge/0.1"

    def send_json(self, status, payload):
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        origin = self.headers.get("Origin", "")
        if origin in ALLOWED_ORIGINS:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
            self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.end_headers()
        self.wfile.write(raw)

    def do_OPTIONS(self):
        origin = self.headers.get("Origin", "")
        if origin not in ALLOWED_ORIGINS:
            self.send_json(403, {"error": "Origin not allowed"})
            return
        self.send_json(204, {})

    def do_GET(self):
        origin = self.headers.get("Origin", "")
        if origin and origin not in ALLOWED_ORIGINS:
            self.send_json(403, {"error": "Origin not allowed"})
            return
        if self.headers.get("Authorization") != f"Bearer {TOKEN}":
            self.send_json(401, {"error": "Unauthorized"})
            return
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/health":
                self.send_json(200, {"service": "TradeLog MT5 bridge", "mode": "read_only"})
            elif parsed.path == "/status":
                self.send_json(200, account_status())
            elif parsed.path == "/history":
                days = int(parse_qs(parsed.query).get("days", ["90"])[0])
                self.send_json(200, read_history(days))
            else:
                self.send_json(404, {"error": "Not found"})
        except Exception as exc:
            self.send_json(503, {"error": str(exc)})

    def log_message(self, fmt, *args):
        print("[TradeLog bridge]", fmt % args)


if __name__ == "__main__":
    print("TradeLog MT5 bridge — READ ONLY")
    print(f"Listening only on http://{HOST}:{PORT}")
    print("Pairing token (keep private; enter it only in TradeLog on this PC):")
    print(TOKEN)
    print("Keep MT5 open and logged in. Press Ctrl+C to stop.")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
