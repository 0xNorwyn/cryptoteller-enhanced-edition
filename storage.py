"""Small JSON-file storage for price alerts and portfolios.

Everything is kept in memory and mirrored to ``DATA_DIR`` on every write, so a
bot restart does not lose user data. Writes are atomic (temp file + replace)
and guarded by a lock, because the alert watcher runs in its own thread.
"""

import json
import os
import threading
import uuid
from datetime import datetime, timezone

from constants import DATA_DIR, MAX_ALERTS_PER_USER, MAX_PORTFOLIO_ENTRIES

_lock = threading.RLock()
_cache = {}

ALERTS_FILE = "alerts"
PORTFOLIOS_FILE = "portfolios"


def _path(name):
    return os.path.join(DATA_DIR, f"{name}.json")


def _load(name, default):
    """Reads a JSON file once and keeps it cached in memory."""
    with _lock:
        if name in _cache:
            return _cache[name]
        try:
            with open(_path(name), "r", encoding="utf-8") as handle:
                _cache[name] = json.load(handle)
        except FileNotFoundError:
            _cache[name] = default
        except (json.JSONDecodeError, OSError) as e:
            print(f"Could not read {_path(name)}: {e}. Starting with empty data.")
            _cache[name] = default
        return _cache[name]


def _save(name, data):
    """Writes data atomically so a crash cannot leave a truncated file."""
    with _lock:
        _cache[name] = data
        try:
            os.makedirs(DATA_DIR, exist_ok=True)
            temp_path = _path(name) + ".tmp"
            with open(temp_path, "w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=2, ensure_ascii=False)
            os.replace(temp_path, _path(name))
        except OSError as e:
            print(f"Could not write {_path(name)}: {e}")


# --- Price alerts ------------------------------------------------------------

def get_alerts():
    """Returns every stored alert."""
    return list(_load(ALERTS_FILE, []))


def get_user_alerts(chat_id, user_id):
    """Returns the alerts a user created in a specific chat."""
    return [
        alert for alert in _load(ALERTS_FILE, [])
        if alert["chat_id"] == chat_id and alert["user_id"] == user_id
    ]


def add_alert(chat_id, user_id, username, first_name, symbol, direction, target):
    """Stores a new alert.

    Returns:
        tuple: (alert dict, None) on success, or (None, error message).
    """
    with _lock:
        alerts = _load(ALERTS_FILE, [])
        if len(get_user_alerts(chat_id, user_id)) >= MAX_ALERTS_PER_USER:
            return None, f"You already have {MAX_ALERTS_PER_USER} alerts here. Remove one first."

        alert = {
            "id": uuid.uuid4().hex[:6],
            "chat_id": chat_id,
            "user_id": user_id,
            "username": username,
            "first_name": first_name,
            "symbol": symbol,
            "direction": direction,
            "target": target,
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        alerts.append(alert)
        _save(ALERTS_FILE, alerts)
        return alert, None


def remove_alert(chat_id, user_id, alert_id):
    """Removes one alert owned by the user. Returns True if something was removed."""
    with _lock:
        alerts = _load(ALERTS_FILE, [])
        remaining = [
            alert for alert in alerts
            if not (alert["id"] == alert_id
                    and alert["chat_id"] == chat_id
                    and alert["user_id"] == user_id)
        ]
        if len(remaining) == len(alerts):
            return False
        _save(ALERTS_FILE, remaining)
        return True


def remove_user_alerts(chat_id, user_id):
    """Removes every alert a user has in a chat. Returns how many were removed."""
    with _lock:
        alerts = _load(ALERTS_FILE, [])
        remaining = [
            alert for alert in alerts
            if not (alert["chat_id"] == chat_id and alert["user_id"] == user_id)
        ]
        removed = len(alerts) - len(remaining)
        if removed:
            _save(ALERTS_FILE, remaining)
        return removed


def remove_alerts_by_id(alert_ids):
    """Removes alerts by id, used by the watcher after they fire."""
    with _lock:
        alert_ids = set(alert_ids)
        alerts = _load(ALERTS_FILE, [])
        remaining = [alert for alert in alerts if alert["id"] not in alert_ids]
        if len(remaining) != len(alerts):
            _save(ALERTS_FILE, remaining)


# --- Portfolios --------------------------------------------------------------

def get_portfolio(user_id):
    """Returns {symbol: {"amount": float, "buy_price": float|None}} for a user."""
    return dict(_load(PORTFOLIOS_FILE, {}).get(str(user_id), {}))


def set_holding(user_id, symbol, amount, buy_price=None):
    """Adds or updates a holding.

    Returns:
        tuple: (True, None) on success, or (False, error message).
    """
    with _lock:
        portfolios = _load(PORTFOLIOS_FILE, {})
        holdings = portfolios.setdefault(str(user_id), {})
        if symbol not in holdings and len(holdings) >= MAX_PORTFOLIO_ENTRIES:
            return False, f"Portfolio is limited to {MAX_PORTFOLIO_ENTRIES} coins."

        # Keep the previous buy price when the user does not pass a new one.
        previous = holdings.get(symbol, {})
        holdings[symbol] = {
            "amount": amount,
            "buy_price": buy_price if buy_price is not None else previous.get("buy_price"),
        }
        _save(PORTFOLIOS_FILE, portfolios)
        return True, None


def remove_holding(user_id, symbol):
    """Removes one coin from a portfolio. Returns True if it was there."""
    with _lock:
        portfolios = _load(PORTFOLIOS_FILE, {})
        holdings = portfolios.get(str(user_id), {})
        if symbol not in holdings:
            return False
        del holdings[symbol]
        if not holdings:
            portfolios.pop(str(user_id), None)
        _save(PORTFOLIOS_FILE, portfolios)
        return True


def clear_portfolio(user_id):
    """Wipes a user's portfolio. Returns how many coins were removed."""
    with _lock:
        portfolios = _load(PORTFOLIOS_FILE, {})
        removed = len(portfolios.pop(str(user_id), {}))
        if removed:
            _save(PORTFOLIOS_FILE, portfolios)
        return removed
