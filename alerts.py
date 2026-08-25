"""Background watcher that fires price alerts created with /alert."""

import threading
import time

import storage
from constants import ALERT_CHECK_INTERVAL
from crypto_api import get_crypto_prices


def is_triggered(alert, price):
    """Checks a single alert against the current price."""
    if alert["direction"] == "above":
        return price >= alert["target"]
    return price <= alert["target"]


def check_alerts_once(notify):
    """Checks every stored alert once and notifies about the triggered ones.

    Args:
        notify (callable): Called as notify(alert, price) for each fired alert.
    """
    alerts = storage.get_alerts()
    if not alerts:
        return

    # One API call for all watched symbols (the price cache is shared with /crypto).
    symbols = sorted({alert["symbol"] for alert in alerts})
    prices = get_crypto_prices(symbols)

    triggered = []
    for alert in alerts:
        price_data = prices.get(alert["symbol"])
        if not price_data or price_data.get("price") is None:
            continue
        price = price_data["price"]
        if is_triggered(alert, price):
            triggered.append((alert, price))

    if not triggered:
        return

    # Drop the alerts first: a failing notification must not re-fire forever.
    storage.remove_alerts_by_id([alert["id"] for alert, _ in triggered])
    for alert, price in triggered:
        try:
            notify(alert, price)
        except Exception as e:
            print(f"Could not deliver alert {alert['id']}: {e}")


def _watch(notify, interval):
    while True:
        try:
            check_alerts_once(notify)
        except Exception as e:
            print(f"Alert watcher error: {e}")
        time.sleep(interval)


def start_alert_watcher(notify, interval=ALERT_CHECK_INTERVAL):
    """Starts the watcher in a daemon thread so it dies with the bot."""
    thread = threading.Thread(
        target=_watch,
        args=(notify, interval),
        name="alert-watcher",
        daemon=True,
    )
    thread.start()
    print(f"Alert watcher started (every {interval}s)")
    return thread
