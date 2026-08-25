import os
from dotenv import load_dotenv
from telebot import TeleBot, types
import requests
import time
import uuid
from constants import (
    HELP_PAGES, COOLDOWN_TIME_CRYPTO, COOLDOWN_TIME_TOP, COOLDOWN_TIME_FGI, CURRENCY_PAGES,
    SUPPORTED_CURRENCIES, CRYPTO_SYMBOLS, CMC_API_KEYS, TON_ADDRESS_REGEX, TOP_DEFAULT_LIMIT,
    TOP_MAX_LIMIT, DEV_USER_IDS
)
import crypto_api
from crypto_api import (
    get_crypto_prices, get_ton_token_info, get_top_cryptocurrencies, get_fear_greed_index,
    convert_currency, format_price, format_large_number
)
from alerts import is_triggered, start_alert_watcher
import storage
import re

# Load environment variables
load_dotenv()
bot = TeleBot(os.getenv("MAIN_KEY"))

# Global variables for caching and rate limiting
last_used_time = {}
cached_crypto_data = {}
last_sent_message_ids = {}

@bot.message_handler(commands=["start"])
def handle_start(message):
    """Handles the /start command."""
    if message.chat.type == "private":
        bot.send_message(message.chat.id, "**What's up!** Add me into a group to access my functionality", parse_mode='Markdown')
    else:
        bot.send_message(message.chat.id, "**Greetings!** I'm [CryptoTeller](https://t.me/crypteller_bot), your friend in the world of cryptocurrencies", parse_mode='Markdown', disable_web_page_preview=True)

def create_help_markup():
    """Creates the help menu pagination keyboard."""
    markup = types.InlineKeyboardMarkup()
    buttons = [
        types.InlineKeyboardButton(f"{i}️⃣", callback_data=f"help_page_{i}")
        for i in range(1, len(HELP_PAGES) + 1)
    ]
    return markup.row(*buttons)

@bot.message_handler(commands=["help"])
def handle_help(message):
    """Displays the help message in multiple pages."""
    markup = create_help_markup()
    bot.send_message(
        message.chat.id,
        HELP_PAGES[1],
        parse_mode='Markdown',
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("help_page_"))
def handle_help_pagination(call):
    """Handles help message pagination."""
    page_num = int(call.data.split("_")[-1])

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=HELP_PAGES[page_num],
        parse_mode='Markdown',
        reply_markup=create_help_markup()
    )

@bot.message_handler(commands=["crypto"])
def get_crypto_price(message):
    """Fetches and displays cryptocurrency prices."""
    global cached_crypto_data
    chat_id = str(message.chat.id)

    if message.chat.type in ("group", "supergroup"):
        if chat_id not in last_used_time or time.time() - last_used_time[chat_id] >= COOLDOWN_TIME_CRYPTO:
            try:
                # Fetch all currencies at once
                all_currencies = [symbol for page in CURRENCY_PAGES for symbol in page]
                cached_crypto_data = get_crypto_prices(all_currencies)
                last_used_time[chat_id] = time.time()

                # Display first page by default
                page1_data = get_current_page_data(0)
                message_text_page1 = format_price_message(page1_data)
                markup = create_pagination_keyboard(1)
                sent_message = bot.send_message(chat_id, message_text_page1, parse_mode='Markdown', disable_web_page_preview=True, reply_markup=markup)

                if chat_id in last_sent_message_ids:
                    try:
                        bot.delete_message(chat_id, last_sent_message_ids[chat_id])
                    except Exception as e:
                        # An old message may already be gone or too old to delete
                        print(f"Could not delete previous price message: {e}")
                last_sent_message_ids[chat_id] = sent_message.message_id
            except requests.exceptions.RequestException as e:
                print(e)
                bot.send_message(chat_id, "Error fetching prices. Please try again.")
        else:
            remaining_time = COOLDOWN_TIME_CRYPTO - (time.time() - last_used_time[chat_id])
            minutes = int(remaining_time // 60)
            seconds = int(remaining_time % 60)
            cooldown_text = f'*Command on cooldown.* Values will refresh in: *{minutes}* minutes *{seconds}* seconds'
            bot.send_message(chat_id, cooldown_text, parse_mode='Markdown')

def get_current_page_data(page):
    """Retrieves data for the specified page."""
    return {k: cached_crypto_data.get(k) for k in CURRENCY_PAGES[page] if k in cached_crypto_data}

def format_price_message(data):
    """Formats the cryptocurrency price message."""
    message_lines = []
    for symbol, values in data.items():
        try:
            price = values["price"]
            change_24h = values["percent_change_24h"]
            message_lines.append(f"• *${symbol}*:  {format_price(price)}_$_ *({change_24h:+.2f}%)*")
        except (TypeError, KeyError) as e:
            # If there's a formatting issue or missing data, skip or provide a fallback
            message_lines.append(f"• *${symbol}*:  Data not available")
            print(f"Skipping formatting issue for {symbol}: {e}")

    message_text = (
        "Current cryptocurrency prices:\n\n"
        + "\n".join(message_lines) +
        f"\n\n  ∟  Prices from: *CoinMarketCap*\n    🤍 Sponsor: None"
    )
    return message_text

def create_pagination_keyboard(current_page):
    """Creates a pagination keyboard for navigating between pages."""
    markup = types.InlineKeyboardMarkup()
    left_button = types.InlineKeyboardButton("⬅️", callback_data="prev_page")
    page_button = types.InlineKeyboardButton(f"{current_page}️⃣", callback_data=f"page_{current_page}")
    right_button = types.InlineKeyboardButton("➡️", callback_data="next_page")
    markup.row(left_button, page_button, right_button)
    return markup

@bot.callback_query_handler(func=lambda call: call.data in ("prev_page", "next_page") or re.fullmatch(r"page_\d+", call.data))
def handle_pagination(call):
    """Handles pagination for cryptocurrency prices."""
    chat_id = call.message.chat.id
    message_id = call.message.message_id

    # The page button is labelled like "2️⃣", so keep the digits only
    current_page = int(re.sub(r"\D", "", call.message.reply_markup.keyboard[0][1].text) or 1) - 1

    if call.data == "prev_page":
        page = max(0, current_page - 1)
    elif call.data == "next_page":
        page = min(len(CURRENCY_PAGES) - 1, current_page + 1)
    else:
        page = current_page

    data = get_current_page_data(page)
    message_text = format_price_message(data)
    markup = create_pagination_keyboard(page + 1)
    bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=message_text, parse_mode='Markdown', reply_markup=markup, disable_web_page_preview=True)

@bot.message_handler(commands=["api"])
def get_current_key(message):
    """Displays the currently used API key (restricted when DEV_USER_IDS is set)."""
    if not is_developer(message.from_user.id):
        return
    try:
        key_names = ["ALPHA", "BRAVO", "CHARLIE", "DELTA", "ECHO", "FOXTROT", "GOLF"]

        # Check if the rotating key index is within the range of available keys
        if 0 <= crypto_api.current_api_key_index < len(CMC_API_KEYS):
            current_key_name = key_names[crypto_api.current_api_key_index] if crypto_api.current_api_key_index < len(key_names) else f"KEY {crypto_api.current_api_key_index + 1}"
            bot.send_message(message.chat.id, f"*Current API Key:* {current_key_name} (#{crypto_api.current_api_key_index + 1})", parse_mode='Markdown')
        else:
            bot.send_message(message.chat.id, "Error: API key index is out of range.", parse_mode='Markdown')
    except Exception as e:
        bot.send_message(message.chat.id, "`Error: Failed to check current API key.`", parse_mode='Markdown')
        print(f"Error checking API key: {e}")

@bot.message_handler(commands=["devblog"])
def share_dev_channel(message):
    """Shares the development blog channel."""
    try:
        bot.reply_to(message, "• [ʀɢʙ.ᴅᴇᴠ](https://t.me/rgbdevelopment) - Your key to knowledge.", parse_mode='Markdown')
    except:
        bot.send_message(message.chat.id, "`Error: Could not access desired function.`", parse_mode='Markdown')

# --- Shared helpers ----------------------------------------------------------

def escape_markdown(text):
    """Escapes characters Telegram's legacy Markdown would treat as formatting."""
    return re.sub(r"([_*`\[\]])", r"\\\1", str(text))


def cooldown_remaining(bucket, chat_id, cooldown):
    """Returns how many seconds are left before a command may run again."""
    last_used = bucket.get(chat_id)
    if last_used is None:
        return 0
    return max(0, cooldown - (time.time() - last_used))


def format_cooldown_text(remaining):
    """Builds the 'command on cooldown' notice."""
    minutes = int(remaining // 60)
    seconds = int(remaining % 60)
    if minutes:
        return f"*Command on cooldown.* Try again in *{minutes}* min *{seconds}* sec"
    return f"*Command on cooldown.* Try again in *{seconds}* sec"


def command_argument(message):
    """Returns everything after the command itself, or an empty string."""
    parts = message.text.split(maxsplit=1)
    return parts[1].strip() if len(parts) > 1 else ""


def is_developer(user_id):
    """An empty DEV_USER_IDS list keeps developer commands open to everyone."""
    return not DEV_USER_IDS or user_id in DEV_USER_IDS


# --- Top coins by market cap -------------------------------------------------

last_top_time = {}

@bot.message_handler(commands=["top"])
def handle_top(message):
    """Displays the highest ranked cryptocurrencies by market cap."""
    chat_id = str(message.chat.id)
    remaining = cooldown_remaining(last_top_time, chat_id, COOLDOWN_TIME_TOP)
    if remaining:
        bot.reply_to(message, format_cooldown_text(remaining), parse_mode='Markdown')
        return

    limit = TOP_DEFAULT_LIMIT
    argument = command_argument(message)
    if argument:
        try:
            limit = int(argument.split()[0])
        except ValueError:
            bot.reply_to(message, f"*Usage:* `/top [1-{TOP_MAX_LIMIT}]`", parse_mode='Markdown')
            return

    coins = get_top_cryptocurrencies(limit)
    if not coins:
        bot.reply_to(message, "⚠️ Could not fetch market data. Please try again later.", parse_mode='Markdown')
        return

    last_top_time[chat_id] = time.time()
    lines = []
    for coin in coins:
        change_24h = coin["percent_change_24h"]
        trend = "🟢" if change_24h >= 0 else "🔴"
        lines.append(
            f"`{coin['rank']:>2}.` {trend} *${escape_markdown(coin['symbol'])}* — "
            f"{format_price(coin['price'])}_$_ *({change_24h:+.2f}%)*  ∙  MC ${format_large_number(coin['market_cap'])}"
        )

    message_text = (
        f"🏆 *Top {len(coins)} by market cap*\n\n"
        + "\n".join(lines)
        + "\n\n  ∟  Prices from: *CoinMarketCap*"
    )
    bot.send_message(message.chat.id, message_text, parse_mode='Markdown', disable_web_page_preview=True)


# --- Fear & Greed index ------------------------------------------------------

last_fgi_time = {}

@bot.message_handler(commands=["fgi", "feargreed"])
def handle_fear_greed(message):
    """Displays the Crypto Fear & Greed Index."""
    chat_id = str(message.chat.id)
    remaining = cooldown_remaining(last_fgi_time, chat_id, COOLDOWN_TIME_FGI)
    if remaining:
        bot.reply_to(message, format_cooldown_text(remaining), parse_mode='Markdown')
        return

    index = get_fear_greed_index()
    if not index:
        bot.reply_to(message, "⚠️ Could not fetch the Fear & Greed Index. Please try again later.", parse_mode='Markdown')
        return

    last_fgi_time[chat_id] = time.time()
    value = max(0, min(100, index["value"]))
    if value < 25:
        mood_emoji = "😱"
    elif value < 45:
        mood_emoji = "😨"
    elif value <= 55:
        mood_emoji = "😐"
    elif value <= 75:
        mood_emoji = "🙂"
    else:
        mood_emoji = "🤑"

    filled = round(value / 10)
    gauge = "█" * filled + "░" * (10 - filled)
    message_text = (
        f"{mood_emoji} *Crypto Fear & Greed Index*\n\n"
        f"`{gauge}`  *{value}/100*\n"
        f"Market mood: *{escape_markdown(index['classification'])}*\n\n"
        f"_Updated: {index['updated'].strftime('%Y-%m-%d %H:%M UTC')}_\n"
        f"  ∟  Data from: *alternative.me*"
    )
    bot.send_message(message.chat.id, message_text, parse_mode='Markdown', disable_web_page_preview=True)


# --- Currency conversion -----------------------------------------------------

CONVERSION_REGEX = re.compile(r"^(?:(\d*\.?\d+)\s+)?([A-Z]{3,5})\s+(?:TO\s+)?([A-Z]{3,5})$")


def parse_conversion_query(text):
    """Parses '[amount] CUR1 [to] CUR2'. Returns (amount, from, to) or None."""
    normalized = " ".join(text.strip().upper().replace(",", ".").split())
    match = CONVERSION_REGEX.match(normalized)
    if not match:
        return None

    amount_str, from_currency, to_currency = match.groups()
    try:
        amount = float(amount_str) if amount_str else 1.0
    except ValueError:
        return None
    return amount, from_currency, to_currency


def format_currency_amount(amount, currency):
    """Formats an amount with the icon and precision matching its currency."""
    if currency in CRYPTO_SYMBOLS:
        return f"🪙 {amount:,.6f} ${currency}"
    return f"💸 {amount:,.2f} {currency}"


def build_conversion_text(query):
    """Turns a raw conversion query into a result line.

    Returns:
        tuple: (result text, None) on success, or (None, error message).
    """
    parsed = parse_conversion_query(query)
    if not parsed:
        return None, "Invalid format. Use: [amount] CUR1 [to] CUR2"

    amount, from_currency, to_currency = parsed
    for currency in (from_currency, to_currency):
        if currency not in SUPPORTED_CURRENCIES:
            return None, f"Unsupported currency: {currency}"

    converted, error = convert_currency(amount, from_currency, to_currency)
    if error:
        return None, error
    return (
        f"{format_currency_amount(amount, from_currency)} = "
        f"{format_currency_amount(converted, to_currency)}"
    ), None


@bot.message_handler(commands=["convert"])
def handle_convert(message):
    """Converts currencies straight in the chat (same syntax as the inline mode)."""
    query = command_argument(message)
    if not query:
        bot.reply_to(
            message,
            "*Usage:* `/convert 100 USD BTC`\n"
            "Also works inline: `@crypteller_bot 100 USD BTC`",
            parse_mode='Markdown'
        )
        return

    result_text, error_message = build_conversion_text(query)
    bot.reply_to(message, result_text or f"⚠️ {error_message}", parse_mode='Markdown')


# --- Price alerts ------------------------------------------------------------

ALERT_REGEX = re.compile(r"^([A-Za-z]{2,10})(>=|<=|>|<|=)?([0-9]*\.?[0-9]+)$")

ALERT_USAGE = (
    "*Usage:*\n"
    "• `/alert BTC > 100000` - fires when the price rises above\n"
    "• `/alert TON < 4` - fires when the price drops below\n"
    "• `/alert SOL 250` - direction is picked automatically\n\n"
    "`/alerts` lists them, `/delalert <id>` removes one."
)


@bot.message_handler(commands=["alert"])
def handle_alert(message):
    """Creates a price alert that fires in the current chat."""
    argument = command_argument(message)
    if not argument:
        bot.reply_to(message, ALERT_USAGE, parse_mode='Markdown')
        return

    match = ALERT_REGEX.match(argument.replace(" ", "").replace(",", "."))
    if not match:
        bot.reply_to(message, ALERT_USAGE, parse_mode='Markdown')
        return

    symbol = match.group(1).upper()
    operator = match.group(2)
    try:
        target = float(match.group(3))
    except ValueError:
        bot.reply_to(message, ALERT_USAGE, parse_mode='Markdown')
        return

    if target <= 0:
        bot.reply_to(message, "⚠️ The target price must be greater than zero.", parse_mode='Markdown')
        return

    price_data = get_crypto_prices([symbol]).get(symbol)
    if not price_data or price_data.get("price") is None:
        bot.reply_to(message, f"⚠️ Unknown or unsupported coin: *${escape_markdown(symbol)}*", parse_mode='Markdown')
        return

    current_price = price_data["price"]
    if operator in (">", ">="):
        direction = "above"
    elif operator in ("<", "<="):
        direction = "below"
    else:
        # No operator given: watch the side the price has yet to reach.
        direction = "above" if target > current_price else "below"

    if is_triggered({"direction": direction, "target": target}, current_price):
        bot.reply_to(
            message,
            f"⚠️ That condition is already met — *${escape_markdown(symbol)}* is at "
            f"*{format_price(current_price)}_$_* right now.",
            parse_mode='Markdown'
        )
        return

    alert, error_message = storage.add_alert(
        chat_id=message.chat.id,
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        symbol=symbol,
        direction=direction,
        target=target,
    )
    if error_message:
        bot.reply_to(message, f"⚠️ {error_message}", parse_mode='Markdown')
        return

    condition = "📈 rises above" if direction == "above" else "📉 drops below"
    bot.reply_to(
        message,
        f"🔔 Alert `{alert['id']}` created.\n\n"
        f"I'll ping you here when *${escape_markdown(symbol)}* {condition} "
        f"*{format_price(target)}_$_*.\n"
        f"Current price: *{format_price(current_price)}_$_*",
        parse_mode='Markdown'
    )


@bot.message_handler(commands=["alerts"])
def handle_alerts_list(message):
    """Lists the alerts a user has in the current chat."""
    user_alerts = storage.get_user_alerts(message.chat.id, message.from_user.id)
    if not user_alerts:
        bot.reply_to(
            message,
            "You have no active alerts here.\nCreate one with `/alert BTC > 100000`",
            parse_mode='Markdown'
        )
        return

    lines = []
    for alert in user_alerts:
        sign = "≥" if alert["direction"] == "above" else "≤"
        lines.append(
            f"• `{alert['id']}` — *${escape_markdown(alert['symbol'])}* {sign} "
            f"*{format_price(alert['target'])}_$_*"
        )

    bot.reply_to(
        message,
        "🔔 *Your active alerts*\n\n" + "\n".join(lines) + "\n\n_Remove one with_ `/delalert <id>`",
        parse_mode='Markdown'
    )


@bot.message_handler(commands=["delalert"])
def handle_delete_alert(message):
    """Removes one alert, or all of them."""
    argument = command_argument(message)
    alert_id = argument.split()[0].lower() if argument else ""
    if not alert_id:
        bot.reply_to(message, "*Usage:* `/delalert <id>` or `/delalert all`", parse_mode='Markdown')
        return

    if alert_id == "all":
        removed = storage.remove_user_alerts(message.chat.id, message.from_user.id)
        if removed:
            bot.reply_to(message, f"🗑 Removed *{removed}* alert(s).", parse_mode='Markdown')
        else:
            bot.reply_to(message, "You have no active alerts here.", parse_mode='Markdown')
        return

    if storage.remove_alert(message.chat.id, message.from_user.id, alert_id):
        bot.reply_to(message, f"🗑 Alert `{alert_id}` removed.", parse_mode='Markdown')
    else:
        bot.reply_to(message, f"⚠️ No alert `{escape_markdown(alert_id)}` of yours found here.", parse_mode='Markdown')


def notify_alert(alert, price):
    """Sends a fired alert back to the chat it was created in."""
    if alert.get("username"):
        mention = f"@{escape_markdown(alert['username'])}"
    else:
        # Users without a @username still get a tappable mention
        name = escape_markdown(alert.get("first_name") or "trader")
        mention = f"[{name}](tg://user?id={alert['user_id']})"
    condition = "rose above" if alert["direction"] == "above" else "dropped below"
    trend = "📈" if alert["direction"] == "above" else "📉"
    bot.send_message(
        alert["chat_id"],
        f"{trend} *Price alert* — {mention}\n\n"
        f"*${escape_markdown(alert['symbol'])}* {condition} *{format_price(alert['target'])}_$_*\n"
        f"Current price: *{format_price(price)}_$_*\n\n"
        f"_Alert_ `{alert['id']}` _has been removed._",
        parse_mode='Markdown'
    )


# --- Portfolio ---------------------------------------------------------------

PORTFOLIO_USAGE = (
    "*Usage:*\n"
    "• `/portfolio` - shows your holdings\n"
    "• `/portfolio add BTC 0.5` - adds or updates a coin\n"
    "• `/portfolio add BTC 0.5 60000` - also stores the buy price\n"
    "• `/portfolio remove BTC` - drops a coin\n"
    "• `/portfolio clear` - wipes everything"
)


def parse_number(raw):
    """Parses a user supplied number, accepting both '1.5' and '1,5'."""
    try:
        return float(raw.replace(",", "."))
    except (TypeError, ValueError, AttributeError):
        return None


def send_portfolio(message):
    """Renders the user's holdings with current value, 24h change and P/L."""
    holdings = storage.get_portfolio(message.from_user.id)
    if not holdings:
        bot.reply_to(
            message,
            "💼 Your portfolio is empty.\n\nAdd a coin with `/portfolio add BTC 0.5`",
            parse_mode='Markdown'
        )
        return

    symbols = sorted(holdings)
    prices = get_crypto_prices(symbols)

    lines = []
    total_value = 0.0
    value_24h_ago = 0.0
    invested_value = 0.0
    invested_now = 0.0

    for symbol in symbols:
        entry = holdings[symbol]
        amount = entry.get("amount") or 0.0
        price_data = prices.get(symbol)
        if not price_data or price_data.get("price") is None:
            lines.append(f"• *${escape_markdown(symbol)}* — {amount:,.6f} _(price unavailable)_")
            continue

        price = price_data["price"]
        change_24h = price_data.get("percent_change_24h") or 0.0
        value = amount * price
        total_value += value

        # Reconstruct yesterday's value so the total change stays weighted.
        divisor = 1 + change_24h / 100
        value_24h_ago += value / divisor if divisor > 0 else value

        trend = "🟢" if change_24h >= 0 else "🔴"
        line = (
            f"• {trend} *${escape_markdown(symbol)}* — {amount:,.6f} ≈ *${value:,.2f}* "
            f"*({change_24h:+.2f}%)*"
        )

        buy_price = entry.get("buy_price")
        if buy_price:
            invested_value += amount * buy_price
            invested_now += value
            pnl_percent = (price / buy_price - 1) * 100
            line += f"\n   ∟ buy {format_price(buy_price)}_$_ → P/L *{pnl_percent:+.2f}%*"
        lines.append(line)

    summary = [f"💰 *Total: ${total_value:,.2f}*"]
    if value_24h_ago > 0:
        total_change = (total_value / value_24h_ago - 1) * 100
        summary[0] += f" *({total_change:+.2f}% / 24h)*"
    if invested_value > 0:
        pnl_percent = (invested_now / invested_value - 1) * 100
        summary.append(
            f"📊 P/L on tracked buys: *{pnl_percent:+.2f}%* (${invested_now - invested_value:+,.2f})"
        )

    bot.reply_to(
        message,
        "💼 *Your portfolio*\n\n" + "\n".join(lines) + "\n\n" + "\n".join(summary),
        parse_mode='Markdown'
    )


def add_holding(message, args):
    """Handles '/portfolio add SYMBOL AMOUNT [BUY_PRICE]'."""
    if len(args) < 2:
        bot.reply_to(message, PORTFOLIO_USAGE, parse_mode='Markdown')
        return

    symbol = args[0].upper()
    amount = parse_number(args[1])
    if amount is None or amount <= 0:
        bot.reply_to(message, "⚠️ The amount must be a positive number.", parse_mode='Markdown')
        return

    buy_price = None
    if len(args) > 2:
        buy_price = parse_number(args[2])
        if buy_price is None or buy_price <= 0:
            bot.reply_to(message, "⚠️ The buy price must be a positive number.", parse_mode='Markdown')
            return

    price_data = get_crypto_prices([symbol]).get(symbol)
    if not price_data or price_data.get("price") is None:
        bot.reply_to(message, f"⚠️ Unknown or unsupported coin: *${escape_markdown(symbol)}*", parse_mode='Markdown')
        return

    saved, error_message = storage.set_holding(message.from_user.id, symbol, amount, buy_price)
    if not saved:
        bot.reply_to(message, f"⚠️ {error_message}", parse_mode='Markdown')
        return

    value = amount * price_data["price"]
    bot.reply_to(
        message,
        f"✅ Saved *{amount:,.6f} ${escape_markdown(symbol)}* ≈ *${value:,.2f}*\n"
        f"_See everything with_ `/portfolio`",
        parse_mode='Markdown'
    )


@bot.message_handler(commands=["portfolio"])
def handle_portfolio(message):
    """Entry point for every portfolio sub-command."""
    args = message.text.split()[1:]
    action = args[0].lower() if args else "show"

    if action in ("add", "set"):
        add_holding(message, args[1:])
    elif action in ("remove", "rm", "del", "delete"):
        if len(args) < 2:
            bot.reply_to(message, "*Usage:* `/portfolio remove BTC`", parse_mode='Markdown')
            return
        symbol = args[1].upper()
        if storage.remove_holding(message.from_user.id, symbol):
            bot.reply_to(message, f"🗑 Removed *${escape_markdown(symbol)}* from your portfolio.", parse_mode='Markdown')
        else:
            bot.reply_to(message, f"⚠️ *${escape_markdown(symbol)}* is not in your portfolio.", parse_mode='Markdown')
    elif action == "clear":
        removed = storage.clear_portfolio(message.from_user.id)
        if removed:
            bot.reply_to(message, f"🗑 Portfolio cleared (*{removed}* coin(s) removed).", parse_mode='Markdown')
        else:
            bot.reply_to(message, "💼 Your portfolio is already empty.", parse_mode='Markdown')
    elif action == "help":
        bot.reply_to(message, PORTFOLIO_USAGE, parse_mode='Markdown')
    elif action == "show":
        send_portfolio(message)
    else:
        bot.reply_to(message, PORTFOLIO_USAGE, parse_mode='Markdown')


@bot.inline_handler(lambda query: len(query.query) > 0)
def handle_inline_query(inline_query):
    """Handles inline queries for currency and cryptocurrency conversions."""
    try:
        result_text, error_message = build_conversion_text(inline_query.query)

        if result_text:
            result = types.InlineQueryResultArticle(
                id=str(uuid.uuid4()),
                title=result_text,
                input_message_content=types.InputTextMessageContent(
                    message_text=result_text,
                    parse_mode='Markdown'
                ),
                thumbnail_url="https://i.imgur.com/ubbkPd7.jpeg"
            )
            bot.answer_inline_query(inline_query.id, [result], cache_time=60) # Cache inline result for 1 min
        else:
            bot.answer_inline_query(inline_query.id, [], switch_pm_text=error_message or "Conversion failed.")

    except Exception as e:
        print(f"Error in inline query handler: {e}")
        bot.answer_inline_query(inline_query.id, [], switch_pm_text="An error occurred.")

@bot.message_handler(func=lambda message: True)
def handle_contract_address(message):
    """Detects TON contract addresses and fetches token info."""
    if not message.text:
        return

    matches = re.findall(TON_ADDRESS_REGEX, message.text)
    if not matches:
        return

    # Process only the first found address to avoid spam
    address = matches[0]

    response_text, error_message = get_ton_token_info(address)

    if response_text:
        # Send the formatted message
        bot.reply_to(message, response_text, parse_mode='Markdown', disable_web_page_preview=True)
    elif error_message:
        # Notify user about the error
        bot.reply_to(message, error_message, parse_mode='Markdown')

# Start polling
if __name__ == "__main__":
    print("Bot is running...")
    start_alert_watcher(notify_alert)
    bot.polling(none_stop=True)
