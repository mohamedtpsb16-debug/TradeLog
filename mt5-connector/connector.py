"""TradeLog local MT5 bridge. Read-only: no trading/order APIs are called."""
from __future__ import annotations

import json
import secrets
import threading
from contextlib import contextmanager
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
MT5_LOCK = threading.RLock()


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


@contextmanager
def selected_account(login: int | None = None, server: str | None = None):
    """Select a saved MT5 account temporarily, verify it, then restore the prior account."""
    with MT5_LOCK:
        mt5 = connect()
        original = mt5.account_info()
        if original is None:
            mt5.shutdown()
            raise RuntimeError(f"Cannot read current MT5 account: {mt5.last_error()}")
        original_login = int(original.login)
        original_server = str(original.server)
        changed = False
        try:
            if login is not None:
                if not server:
                    raise ValueError("Le serveur MT5 est obligatoire.")
                if original_login != login or original_server.casefold() != server.casefold():
                    if not mt5.login(login, server=server):
                        raise RuntimeError(
                            "MT5 ne peut pas ouvrir ce compte. Vérifie le numéro, le serveur "
                            "et que le mot de passe est enregistré dans MT5. "
                            f"Détail : {mt5.last_error()}"
                        )
                    changed = True
            account = mt5.account_info()
            if account is None:
                raise RuntimeError(f"Lecture du compte MT5 impossible : {mt5.last_error()}")
            if login is not None and (
                int(account.login) != login or str(account.server).casefold() != server.casefold()
            ):
                raise RuntimeError("Le compte MT5 actif ne correspond pas au compte demandé. Lecture bloquée.")
            yield mt5, account, mt5.terminal_info()
        finally:
            restore_error = None
            if changed:
                if not mt5.login(original_login, server=original_server):
                    restore_error = f"Impossible de rétablir le compte MT5 initial : {mt5.last_error()}"
                else:
                    restored = mt5.account_info()
                    if restored is None or int(restored.login) != original_login or str(restored.server).casefold() != original_server.casefold():
                        restore_error = "Le rétablissement du compte MT5 initial n’a pas pu être confirmé."
            mt5.shutdown()
            if restore_error:
                raise RuntimeError("ALERTE — " + restore_error + " Vérifie le compte affiché dans MT5.")


def account_status(login: int | None = None, server: str | None = None):
    with selected_account(login, server) as (mt5, account, terminal):
        return {
            "connected": True,
            "terminal_connected": bool(terminal.connected) if terminal else False,
            "trade_allowed": bool(terminal.trade_allowed) if terminal else None,
            "account_login_masked": ("*" * max(0, len(str(account.login)) - 3)) + str(account.login)[-3:],
            "account_login": int(account.login),
            "server": str(account.server),
            "currency": str(account.currency),
            "mode": "read_only",
            "original_account_restored": True,
        }


def read_history(days: int = 90, login: int | None = None, server: str | None = None):
    if not 1 <= days <= 365:
        raise ValueError("days must be between 1 and 365")
    with selected_account(login, server) as (mt5, account, terminal):
        end = datetime.now()
        start = end - timedelta(days=days)
        deals = mt5.history_deals_get(start, end)
        if deals is None:
            raise RuntimeError(f"MT5 history retrieval failed: {mt5.last_error()}")
        rows = []
        for d in deals:
            rows.append({
                "ticket": int(d.ticket), "order": int(d.order), "position_id": int(d.position_id),
                "time": int(d.time), "time_utc": datetime.fromtimestamp(int(d.time), timezone.utc).isoformat(),
                "symbol": str(d.symbol), "type": int(d.type), "entry": int(d.entry),
                "volume": float(d.volume), "price": float(d.price), "commission": float(d.commission),
                "swap": float(d.swap), "profit": float(d.profit), "fee": float(d.fee),
                "comment": str(d.comment), "external_id": str(d.external_id),
            })
        return {
            "mode": "read_only", "account_login": int(account.login), "server": str(account.server),
            "currency": str(account.currency), "original_account_restored": True,
            "from": start.isoformat(), "to": end.isoformat(), "count": len(rows), "deals": rows,
        }


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
            if self.headers.get("Access-Control-Request-Private-Network") == "true":
                self.send_header("Access-Control-Allow-Private-Network", "true")
        self.end_headers()
        self.wfile.write(raw)

    def do_OPTIONS(self):
        origin = self.headers.get("Origin", "")
        if origin not in ALLOWED_ORIGINS:
            self.send_json(403, {"error": "Origin not allowed"})
            return
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        if self.headers.get("Access-Control-Request-Private-Network") == "true":
            self.send_header("Access-Control-Allow-Private-Network", "true")
        self.end_headers()

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
                query = parse_qs(parsed.query)
                login = int(query["login"][0]) if query.get("login") else None
                server = query.get("server", [None])[0]
                self.send_json(200, account_status(login, server))
            elif parsed.path == "/history":
                query = parse_qs(parsed.query)
                days = int(query.get("days", ["90"])[0])
                login = int(query["login"][0]) if query.get("login") else None
                server = query.get("server", [None])[0]
                self.send_json(200, read_history(days, login, server))
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
