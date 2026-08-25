```python
# .------------------------------------------------------------------------------------------------------------.
# |                                                                                                            |
# |                                                                                                            |
# |                        ██████╗  ██████╗ ██████╗    ██████╗ ███████╗██╗   ██╗                               |
# |                        ██╔══██╗██╔════╝ ██╔══██╗   ██╔══██╗██╔════╝██║   ██║                               |
# |                        ██████╔╝██║  ███╗██████╔╝   ██║  ██║█████╗  ██║   ██║                               |
# |                        ██╔══██╗██║   ██║██╔══██╗   ██║  ██║██╔══╝  ╚██╗ ██╔╝                               |
# |                        ██║  ██║╚██████╔╝██████╔╝██╗██████╔╝███████╗ ╚████╔╝                                |
# |                        ╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚═╝╚═════╝ ╚══════╝  ╚═══╝                                 |
# |                                                                                                            |
# |                                                                                                            |
# |                                                                                                            |
# |    █████╗█████╗█████╗█████╗█████╗█████╗█████╗█████╗█████╗█████╗█████╗█████╗█████╗█████╗█████╗█████╗        |
# |    ╚════╝╚════╝╚════╝╚════╝╚════╝╚════╝╚════╝╚════╝╚════╝╚════╝╚════╝╚════╝╚════╝╚════╝╚════╝╚════╝        |
# |                                                                                                            |
# |                                                                                                            |
# |                                                                                                            |
# |     ██████╗██████╗ ██╗   ██╗██████╗ ████████╗ ██████╗ ████████╗███████╗██╗     ██╗     ███████╗██████╗     |
# |    ██╔════╝██╔══██╗╚██╗ ██╔╝██╔══██╗╚══██╔══╝██╔═══██╗╚══██╔══╝██╔════╝██║     ██║     ██╔════╝██╔══██╗    |
# |    ██║     ██████╔╝ ╚████╔╝ ██████╔╝   ██║   ██║   ██║   ██║   █████╗  ██║     ██║     █████╗  ██████╔╝    |
# |    ██║     ██╔══██╗  ╚██╔╝  ██╔═══╝    ██║   ██║   ██║   ██║   ██╔══╝  ██║     ██║     ██╔══╝  ██╔══██╗    |
# |    ╚██████╗██║  ██║   ██║   ██║        ██║   ╚██████╔╝   ██║   ███████╗███████╗███████╗███████╗██║  ██║    |
# |     ╚═════╝╚═╝  ╚═╝   ╚═╝   ╚═╝        ╚═╝    ╚═════╝    ╚═╝   ╚══════╝╚══════╝╚══════╝╚══════╝╚═╝  ╚═╝    |
# |                                                                                                            |
# |                                                                                                            |
# '------------------------------------------------------------------------------------------------------------'
```
# CryptoTeller Bot

CryptoTeller is a Telegram bot designed to provide real-time cryptocurrency prices and currency conversion rates. It supports multiple cryptocurrencies and fiat currencies, and it can be used in both private chats and groups. The bot uses CoinMarketCap and ExchangeRate-API to fetch the latest data.

## Features

- **Real-time Cryptocurrency Prices**: Get the latest prices for popular cryptocurrencies like Bitcoin (BTC), Ethereum (ETH), and more.
- **Market Leaderboard**: `/top` lists the highest ranked coins by market cap with 24h changes.
- **Currency Conversion**: Convert between various fiat currencies and cryptocurrencies, inline or with `/convert`.
- **Price Alerts**: `/alert BTC > 100000` pings you in the chat as soon as the target is hit. Alerts survive restarts.
- **Portfolio Tracking**: `/portfolio add BTC 0.5` keeps your holdings and shows current value, 24h change and P/L.
- **Market Sentiment**: `/fgi` shows the Crypto Fear & Greed Index.
- **Pagination**: Navigate through multiple pages of cryptocurrency data.
- **API Key Rotation**: Automatically rotate through multiple API keys to avoid rate limits.
- **Caching**: Prices, exchange rates and market data are cached, so repeated commands cost no extra API credits.
- **(TON) Address Detection**: Automatically detects TON contract addresses in messages and provides token details and a DS link.

## Commands

- **/start**: Starts a conversation with the bot.
- **/crypto**: Displays the current prices of supported cryptocurrencies.
- **/top** `[1-25]`: Shows the top coins by market cap (defaults to 10).
- **/convert** `[amount] CUR1 [to] CUR2`: Converts currencies, e.g. `/convert 100 USD BTC`.
- **/fgi**: Shows the Crypto Fear & Greed Index.
- **/alert** `SYMBOL [> | <] PRICE`: Creates a price alert, e.g. `/alert TON < 4`. Without an operator the direction is picked automatically.
- **/alerts**: Lists your active alerts in the current chat.
- **/delalert** `<id> | all`: Removes one alert, or all of them.
- **/portfolio** `[add | remove | clear]`: Tracks your holdings, e.g. `/portfolio add BTC 0.5 60000`.
- **/help**: Displays a list of available commands and their descriptions.
- **/api**: (Developer Only) Shows the currently used API key.
- **/devblog**: Shares the development channel.

### Inline mode

Type `@crypteller_bot 100 USD BTC` in any chat to convert without adding the bot.

## Setup

### Prerequisites

- Python 3.7 or higher
- A Telegram bot token (obtainable from [BotFather](https://t.me/BotFather))
- CoinMarketCap API key(s) (available from [CoinMarketCap](https://coinmarketcap.com/api/))
- ExchangeRate-API key(s) (available from [ExchangeRate-API](https://www.exchangerate-api.com/))

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/RGB-Outl4w/CryptoTeller.git
   cd CryptoTeller
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the root directory and add your Telegram bot token:
   ```plaintext
   MAIN_KEY=your_telegram_bot_token
   ```

4. Update the `constants.py` file with your CoinMarketCap and ExchangeRate-API keys.

### Running the Bot

To start the bot, run:
```bash
python cryptoTeller.py
```

### Tests

The repository ships with an offline smoke test that fakes every API call, so it needs
no keys, no bot token and no network:

```bash
python tests/smoke_test.py
```

## Configuration

All settings live in `constants.py`:

- **CoinMarketCap API Keys**: Add your API keys to the `CMC_API_KEYS` list.
- **ExchangeRate-API Keys**: Add your API keys to the `EXCHANGE_RATE_API_KEYS` list.
- **Developer commands**: Add your Telegram user ID to `DEV_USER_IDS` to restrict `/api` to yourself. An empty list keeps it open to everyone.
- **Cooldowns**: `COOLDOWN_TIME_CRYPTO`, `COOLDOWN_TIME_TOP` and `COOLDOWN_TIME_FGI` (seconds, per chat).
- **Leaderboard**: `TOP_DEFAULT_LIMIT` / `TOP_MAX_LIMIT` control how many coins `/top` may show.
- **Alerts**: `ALERT_CHECK_INTERVAL` sets how often prices are checked, `MAX_ALERTS_PER_USER` how many alerts a user may keep per chat.
- **Portfolio**: `MAX_PORTFOLIO_ENTRIES` limits how many coins a user can track.

### Data storage

Alerts and portfolios are stored as JSON in the `DATA_DIR` folder (`data/` by default), created
automatically on first write. The folder is git-ignored — back it up if you care about the contents.

## Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue if you have any suggestions or find any bugs.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.

## Acknowledgments

- [CoinMarketCap](https://coinmarketcap.com/) for providing the cryptocurrency data.
- [ExchangeRate-API](https://www.exchangerate-api.com/) for providing the currency conversion rates.
- [pyTelegramBotAPI](https://github.com/eternnoir/pyTelegramBotAPI) for the Telegram bot library.

## Support

If you find this project useful, consider supporting it by donating or becoming a sponsor. Your support helps keep the project alive and continuously improved.

[![Donate](https://img.shields.io/badge/Donate-Boosty-orange.svg)](https://boosty.to/rgboutlaw/donate)
