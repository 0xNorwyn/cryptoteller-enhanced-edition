"""Offline smoke test for CryptoTeller.

Run it with:
    python tests/smoke_test.py

No API keys, no bot token and no network access are required: requests.get is
replaced with canned responses, and the bot's send methods are captured.
"""
import os
import sys
import shutil
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if hasattr(sys.stdout, "reconfigure"):  # keep emoji printable on Windows consoles
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

os.environ["MAIN_KEY"] = "123456:FAKE_TOKEN"

import requests

PRICES = {
    "BTC": (100000.0, 2.5),
    "ETH": (3500.0, -1.25),
    "TON": (5.1234, 0.75),
    "SOL": (200.0, 3.0),
    "DOGE": (0.0000123, -5.0),
}


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(f"HTTP {self.status_code}", response=self)


def fake_get(url, params=None, headers=None, timeout=None):
    params = params or {}
    if "quotes/latest" in url:
        data = {}
        for symbol in params.get("symbol", "").split(","):
            if symbol in PRICES:
                price, change = PRICES[symbol]
                data[symbol] = {"quote": {"USD": {"price": price, "percent_change_24h": change}}}
        return FakeResponse({"data": data})
    if "listings/latest" in url:
        data = []
        for rank, (symbol, (price, change)) in enumerate(PRICES.items(), start=1):
            data.append({
                "cmc_rank": rank,
                "symbol": symbol,
                "name": symbol.title(),
                "quote": {"USD": {
                    "price": price,
                    "percent_change_24h": change,
                    "market_cap": price * 19_000_000,
                    "volume_24h": price * 1000,
                }},
            })
        return FakeResponse({"data": data})
    if "exchangerate-api.com" in url:
        return FakeResponse({"result": "success", "conversion_rate": 80.0})
    if "alternative.me" in url:
        return FakeResponse({"data": [{"value": "72", "value_classification": "Greed", "timestamp": "1756080000"}]})
    if "dexscreener" in url:
        return FakeResponse({"pairs": [{
            "chainId": "ton", "baseToken": {"name": "Test Token", "symbol": "TEST"},
            "priceUsd": "0.0123", "priceChange": {"h1": 1.0, "h24": -2.0},
            "volume": {"h24": 1_500_000}, "liquidity": {"usd": 250_000},
            "fdv": 12_300_000_000, "pairCreatedAt": 1_700_000_000_000, "url": "https://dexscreener.com/ton/x",
        }]})
    raise AssertionError(f"Unexpected URL requested: {url}")


requests.get = fake_get

import constants
import crypto_api
import storage
import alerts

DATA_DIR = tempfile.mkdtemp(prefix="crypteller-test-")
storage.DATA_DIR = DATA_DIR

import cryptoTeller as bot_module

failures = []
sent = []


def check(label, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    if not condition:
        failures.append(f"{label}: {detail}")
    print(f"[{status}] {label}" + (f" -> {detail}" if detail else ""))


# --- Fake bot: capture every outgoing message --------------------------------

def capture(kind):
    def _send(*args, **kwargs):
        text = args[1] if len(args) > 1 else kwargs.get("text", "")
        sent.append((kind, text))
        class Sent:
            message_id = 1
        return Sent()
    return _send


bot_module.bot.send_message = capture("send")
bot_module.bot.reply_to = capture("reply")
bot_module.bot.delete_message = lambda *a, **k: None
bot_module.bot.answer_inline_query = lambda *a, **k: sent.append(("inline", str(k)))


class FakeUser:
    id = 42
    username = "tester"
    first_name = "Tester"


class FakeChat:
    id = -1001
    type = "supergroup"


class FakeMessage:
    def __init__(self, text):
        self.text = text
        self.chat = FakeChat()
        self.from_user = FakeUser()


def run(handler, text):
    sent.clear()
    handler(FakeMessage(text))
    return sent[-1][1] if sent else ""


# --- Formatting helpers ------------------------------------------------------

check("format_price big", crypto_api.format_price(100000.0) == "100,000.00", crypto_api.format_price(100000.0))
check("format_price small", crypto_api.format_price(0.0000123) == "0.00001230", crypto_api.format_price(0.0000123))
check("format_price none", crypto_api.format_price(None) == "N/A")
check("format_large_number B", crypto_api.format_large_number(12_300_000_000) == "12.30B", crypto_api.format_large_number(12_300_000_000))
check("format_large_number small", crypto_api.format_large_number(999) == "999.00", crypto_api.format_large_number(999))
check("format_large_number junk", crypto_api.format_large_number(None) == "N/A")

# --- Conversion --------------------------------------------------------------

check("parse '100 usd btc'", bot_module.parse_conversion_query("100 usd btc") == (100.0, "USD", "BTC"))
check("parse 'btc to eur'", bot_module.parse_conversion_query("btc to eur") == (1.0, "BTC", "EUR"))
check("parse '0,5 BTC USD'", bot_module.parse_conversion_query("0,5 BTC USD") == (0.5, "BTC", "USD"))
check("parse garbage", bot_module.parse_conversion_query("hello world !") is None)

text, err = bot_module.build_conversion_text("1 BTC USD")
check("BTC->USD", "100,000.00 USD" in (text or ""), text or err)
text, err = bot_module.build_conversion_text("1 BTC RUB")
check("BTC->RUB (via USD rate 80)", "8,000,000.00 RUB" in (text or ""), text or err)
text, err = bot_module.build_conversion_text("100 USD BTC")
check("USD->BTC", "0.001000 $BTC" in (text or ""), text or err)
text, err = bot_module.build_conversion_text("1 BTC ETH")
check("BTC->ETH", "28.571429 $ETH" in (text or ""), text or err)
text, err = bot_module.build_conversion_text("1 XXX USD")
check("unsupported currency", err == "Unsupported currency: XXX", str(err))
check("/convert handler", "100,000.00 USD" in run(bot_module.handle_convert, "/convert 1 BTC USD"))
check("/convert usage", "Usage" in run(bot_module.handle_convert, "/convert"))

# --- /top and /fgi -----------------------------------------------------------

top_text = run(bot_module.handle_top, "/top 3")
check("/top renders 3 coins", top_text.count("\n•") + top_text.count("` 1.`") >= 1 and "Top 3 by market cap" in top_text, top_text[:80])
check("/top cooldown", "cooldown" in run(bot_module.handle_top, "/top").lower())
bot_module.last_top_time.clear()
check("/top bad argument", "Usage" in run(bot_module.handle_top, "/top abc"))
check("/top caps at max", len(crypto_api.get_top_cryptocurrencies(999)) <= constants.TOP_MAX_LIMIT)

fgi_text = run(bot_module.handle_fear_greed, "/fgi")
check("/fgi renders", "72/100" in fgi_text and "Greed" in fgi_text, fgi_text[:60])

# --- Alerts ------------------------------------------------------------------

created = run(bot_module.handle_alert, "/alert BTC > 120000")
check("alert created", "Alert" in created and "created" in created, created[:70])
check("alert already met", "already met" in run(bot_module.handle_alert, "/alert BTC > 90000"))
check("alert auto direction", "drops below" in run(bot_module.handle_alert, "/alert ETH 3000"))
check("alert unknown coin", "Unknown" in run(bot_module.handle_alert, "/alert NOSUCH 10"))
check("alert usage", "Usage" in run(bot_module.handle_alert, "/alert"))
check("alert bad input", "Usage" in run(bot_module.handle_alert, "/alert not an alert"))

listed = run(bot_module.handle_alerts_list, "/alerts")
check("alerts listed", listed.count("•") == 2, listed)
check("alerts stored", len(storage.get_user_alerts(-1001, 42)) == 2)

alert_id = storage.get_user_alerts(-1001, 42)[0]["id"]
check("delalert wrong id", "No alert" in run(bot_module.handle_delete_alert, "/delalert zzzzzz"))
check("delalert works", "removed" in run(bot_module.handle_delete_alert, f"/delalert {alert_id}"))
check("delalert all", "Removed" in run(bot_module.handle_delete_alert, "/delalert all"))
check("no alerts left", storage.get_user_alerts(-1001, 42) == [])

# Watcher: an alert that must fire, and one that must not
storage.add_alert(-1001, 42, "tester", "Tester", "BTC", "above", 90000.0)
storage.add_alert(-1001, 42, "tester", "Tester", "ETH", "below", 100.0)
sent.clear()
alerts.check_alerts_once(bot_module.notify_alert)
check("watcher fired once", len(sent) == 1, str(sent))
check("watcher message", "BTC" in sent[0][1] and "rose above" in sent[0][1], sent[0][1] if sent else "")
check("fired alert removed", len(storage.get_alerts()) == 1, str(storage.get_alerts()))
check("is_triggered below", alerts.is_triggered({"direction": "below", "target": 10}, 9) is True)
check("is_triggered above false", alerts.is_triggered({"direction": "above", "target": 10}, 9) is False)
storage.remove_user_alerts(-1001, 42)

# Persistence: reload from disk
storage.add_alert(-1001, 42, "tester", "Tester", "SOL", "above", 500.0)
storage._cache.clear()
check("alerts persisted to disk", len(storage.get_user_alerts(-1001, 42)) == 1, str(storage.get_alerts()))
storage.remove_user_alerts(-1001, 42)

# --- Portfolio ---------------------------------------------------------------

check("empty portfolio", "empty" in run(bot_module.handle_portfolio, "/portfolio"))
check("portfolio usage", "Usage" in run(bot_module.handle_portfolio, "/portfolio add"))
check("portfolio bad amount", "positive number" in run(bot_module.handle_portfolio, "/portfolio add BTC -1"))
check("portfolio unknown coin", "Unknown" in run(bot_module.handle_portfolio, "/portfolio add NOSUCH 1"))
check("portfolio add", "Saved" in run(bot_module.handle_portfolio, "/portfolio add BTC 0.5 60000"))
check("portfolio add second", "Saved" in run(bot_module.handle_portfolio, "/portfolio add ETH 2"))

view = run(bot_module.handle_portfolio, "/portfolio")
check("portfolio total", "Total: $57,000.00" in view, view)
check("portfolio P/L", "P/L" in view and "+66.67%" in view, view)
check("portfolio keeps buy price", storage.get_portfolio(42)["BTC"]["buy_price"] == 60000)
run(bot_module.handle_portfolio, "/portfolio add BTC 1")
check("amount updated, buy price kept", storage.get_portfolio(42)["BTC"] == {"amount": 1.0, "buy_price": 60000})
check("portfolio remove", "Removed" in run(bot_module.handle_portfolio, "/portfolio remove BTC"))
check("portfolio remove missing", "not in your portfolio" in run(bot_module.handle_portfolio, "/portfolio remove BTC"))
check("portfolio clear", "cleared" in run(bot_module.handle_portfolio, "/portfolio clear"))
check("portfolio empty again", storage.get_portfolio(42) == {})

# --- Misc --------------------------------------------------------------------

check("escape_markdown", bot_module.escape_markdown("a_b*c[d]") == r"a\_b\*c\[d\]", bot_module.escape_markdown("a_b*c[d]"))
check("is_developer open by default", bot_module.is_developer(999) is True)
bot_module.DEV_USER_IDS = [1]
check("is_developer restricted", bot_module.is_developer(999) is False)
bot_module.DEV_USER_IDS = []

ton_text, ton_err = crypto_api.get_ton_token_info("EQ" + "a" * 46)
check("TON token info", ton_text is not None and "Test Token" in ton_text, ton_err or "")
check("TON market cap compact", "12.30B" in (ton_text or ""), (ton_text or "")[:40])

check("help pages count", len(constants.HELP_PAGES) == 5)
markup = bot_module.create_help_markup()
check("help keyboard matches pages", len(markup.keyboard[0]) == 5, str(len(markup.keyboard[0])))

sent.clear()
bot_module.notify_alert({"chat_id": -1001, "user_id": 42, "username": None, "first_name": "Ann", "symbol": "BTC", "direction": "below", "target": 1.0, "id": "abc123"}, 0.5)
check("mention without username", "[Ann](tg://user?id=42)" in sent[-1][1], sent[-1][1])

shutil.rmtree(DATA_DIR, ignore_errors=True)

print("\n" + "=" * 60)
if failures:
    print(f"{len(failures)} FAILURE(S):")
    for failure in failures:
        print(" -", failure)
    sys.exit(1)
print("All checks passed.")
