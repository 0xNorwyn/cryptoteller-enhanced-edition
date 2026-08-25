# CoinMarketCap API keys (replace with your own keys)
CMC_API_KEYS = [
    "your_coinmarketcap_api_key_1",
    "your_coinmarketcap_api_key_2",
    # Add more keys as needed
]

# ExchangeRate-API keys (replace with your own keys)
EXCHANGE_RATE_API_KEYS = [
    "your_exchangerate_api_key_1",
    "your_exchangerate_api_key_2",
    # Add more keys as needed
]

# Telegram user IDs allowed to run developer-only commands (e.g. /api).
# Leave the list empty to keep those commands open to everyone.
DEV_USER_IDS = []

# Sponsors and donators (replace with your own sponsors/donators)
SPONSORS_AND_DONATORS = (
    "[Sponsor Name](https://example.com)",  # Example sponsor
    # Add more sponsors/donators as needed
)

# Currency pages for pagination
CURRENCY_PAGES = [
    ["TON", "BTC", "ETH", "SUI", "USDT", "SOL"],
    ["NOT", "PUNK", "ARBUZ", "DOGE", "SHIT", "DOGS"],
    ["REDO", "DUREV", "WALL", "STON", "GRAM", "RAFF"]
]

# Supported currencies for conversion
SUPPORTED_CURRENCIES = [
    "USD", "RUB", "EUR", "GBP", "JPY", "KZT", "UAH",
    "TON", "BTC", "ETH", "DOGE", "DOGS", "NOT", "SOL", "STON", "GRAM", "SUI"
]

# Cryptocurrency symbols
CRYPTO_SYMBOLS = ["TON", "BTC", "ETH", "DOGE", "DOGS", "NOT", "SOL", "STON", "GRAM", "SUI"]

# Regex for TON contract addresses (adjust as needed)
# Matches Base64url (EQ/UQ prefix) and the 48-char format
TON_ADDRESS_REGEX = r"\b(?:(?:EQ|UQ)[A-Za-z0-9_\-]{46}|[A-Za-z0-9]{48})\b"

# DexScreener API endpoint
DEXSCREENER_API_URL = "https://api.dexscreener.com/latest/dex/search?q={address}"

# CoinMarketCap API endpoints
CMC_QUOTES_URL = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
CMC_LISTINGS_URL = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"

# Crypto Fear & Greed Index (free, no API key required)
FEAR_GREED_API_URL = "https://api.alternative.me/fng/?limit=1"

# Cooldown times for commands (in seconds)
COOLDOWN_TIME_CRYPTO = 10  # Cooldown for /crypto command
COOLDOWN_TIME_TOP = 300    # Cooldown for /top command
COOLDOWN_TIME_FGI = 60     # Cooldown for /fgi command

# /top command limits
TOP_DEFAULT_LIMIT = 10
TOP_MAX_LIMIT = 25

# Price alerts
# The watcher re-uses the crypto price cache, so checking more often than
# CRYPTO_CACHE_DURATION (5 min) would not produce fresher data.
ALERT_CHECK_INTERVAL = 300  # Seconds between price alert checks
MAX_ALERTS_PER_USER = 10    # Alerts a single user may keep per chat

# Portfolio
MAX_PORTFOLIO_ENTRIES = 30  # Distinct coins a single user may track

# Directory where alerts/portfolios are persisted (created on first write)
DATA_DIR = "data"

HELP_PAGES = {
    1: """
**📋 Commands & Features**

• **/start** - Starts a conversation with me
• **/crypto** - Shows cryptocurrency prices with real-time updates
• **/top** - Top coins by market cap
• **/convert** - Converts currencies right in the chat
• **/fgi** - Crypto Fear & Greed Index
• **/alert** - Sets a price alert
• **/portfolio** - Tracks your holdings
• **/help** - Displays this help message
• **/api** - **[DEV ONLY]** Shows currently used API key
• **/devblog** - Get link to our development channel

*Page 1/5* - Use buttons below to navigate
""",
    2: """
**📊 Market Data**

**/crypto** - price board with 24h changes
• Multiple page navigation
• Auto-refresh cooldown system

**/top** `[amount]` - top coins by market cap
*Examples:* `/top`, `/top 25`

**/fgi** - Crypto Fear & Greed Index
• Market sentiment from 0 (extreme fear) to 100 (extreme greed)

*Page 2/5* - Use buttons below to navigate
""",
    3: """
**💱 Currency Conversion**

In any chat, type:
`@crypteller_bot [amount] CUR1 [to] CUR2`

*Examples:*
• `@crypteller_bot 100 USD BTC`
• `@crypteller_bot BTC EUR`
• `@crypteller_bot 50 EUR USD`

The same works as a command:
• `/convert 100 USD BTC`
• `/convert 0.5 BTC to RUB`

Supports both crypto and fiat currencies!

*Page 3/5* - Use buttons below to navigate
""",
    4: """
**🔔 Price Alerts**

I will ping you in this chat as soon as a coin hits your target:

• `/alert BTC > 100000` - fires when the price rises above
• `/alert TON < 4` - fires when the price drops below
• `/alert SOL 250` - direction is picked automatically
• `/alerts` - lists your active alerts
• `/delalert <id>` - removes one alert
• `/delalert all` - removes all of them

Alerts are checked every few minutes and disappear once triggered.

*Page 4/5* - Use buttons below to navigate
""",
    5: """
**💼 Portfolio & 🔍 TON Tokens**

Track your holdings (private to your account):
• `/portfolio add BTC 0.5` - adds or updates a coin
• `/portfolio add BTC 0.5 60000` - stores the buy price for P/L
• `/portfolio remove BTC` - drops a coin
• `/portfolio clear` - wipes everything
• `/portfolio` - shows value, 24h change and P/L

**TON token detection**
Send any TON contract address in chat and I'll fetch price, volume,
liquidity, market cap and a DexScreener link.

*Page 5/5* - Use buttons below to navigate
"""
}
