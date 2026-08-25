import time
import requests
from datetime import datetime, timezone, timedelta
from constants import (
    CMC_API_KEYS, EXCHANGE_RATE_API_KEYS, DEXSCREENER_API_URL, CMC_QUOTES_URL,
    CMC_LISTINGS_URL, FEAR_GREED_API_URL, TOP_DEFAULT_LIMIT, TOP_MAX_LIMIT, CRYPTO_SYMBOLS
)

# Global variables for API key rotation
current_api_key_index = 0
current_exchange_rate_api_key_index = 0

# Caching dictionaries and timeouts
crypto_price_cache = {}
CRYPTO_CACHE_DURATION = timedelta(minutes=5) # Cache crypto prices for 5 minutes

exchange_rate_cache = {}
EXCHANGE_RATE_CACHE_DURATION = timedelta(hours=1) # Cache exchange rates for 1 hour

def get_crypto_prices(symbols):
    """
    Fetches the latest cryptocurrency prices from CoinMarketCap, using cache if available.

    Args:
        symbols (list): List of cryptocurrency symbols to fetch prices for.

    Returns:
        dict: A dictionary containing the prices and other details for the requested symbols.
    """
    global current_api_key_index, crypto_price_cache
    results = {}
    symbols_to_fetch = []
    now = datetime.now(timezone.utc)

    # Check cache first
    for symbol in symbols:
        if symbol in crypto_price_cache:
            cached_data, timestamp = crypto_price_cache[symbol]
            if now - timestamp < CRYPTO_CACHE_DURATION:
                results[symbol] = cached_data
            else:
                symbols_to_fetch.append(symbol)
        else:
            symbols_to_fetch.append(symbol)

    # Fetch missing symbols
    if symbols_to_fetch:
        url = CMC_QUOTES_URL
        params = {"symbol": ",".join(symbols_to_fetch), "convert": "USD"}
        headers = {"X-CMC_PRO_API_KEY": CMC_API_KEYS[current_api_key_index]}

        attempts = 0
        max_attempts = max(3, len(CMC_API_KEYS) * 2)
        while attempts < max_attempts:
            attempts += 1
            try:
                response = requests.get(url, params=params, headers=headers, timeout=10) # Added timeout
                response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

                if response.status_code == 200:
                    data = response.json().get("data", {})
                    fetch_time = datetime.now(timezone.utc)
                    for symbol in symbols_to_fetch:
                        if symbol in data and 'quote' in data[symbol] and 'USD' in data[symbol]['quote']:
                            price_data = data[symbol]["quote"]["USD"]
                            results[symbol] = price_data
                            crypto_price_cache[symbol] = (price_data, fetch_time) # Update cache
                        else:
                            # Handle cases where a specific symbol wasn't returned or data is incomplete
                            print(f"Warning: Data for symbol {symbol} not found or incomplete in API response.")
                            results[symbol] = None # Indicate data unavailable
                    break # Exit while loop on success

            except requests.exceptions.HTTPError as http_err:
                if response.status_code == 429:  # Rate limit
                    print(f"Rate limit hit for CMC API key index {current_api_key_index}. Switching key.")
                    # Try all available API keys before giving up
                    initial_key = current_api_key_index
                    while True:
                        switch_api_key()
                        if current_api_key_index == initial_key:
                            print("All API keys exhausted. Waiting 60 seconds before retry.")
                            time.sleep(60)  # Wait before retrying with first key
                        headers = {"X-CMC_PRO_API_KEY": CMC_API_KEYS[current_api_key_index]}
                        try:
                            response = requests.get(url, params=params, headers=headers, timeout=10)
                            response.raise_for_status()
                            if response.status_code == 200:
                                break
                        except requests.exceptions.HTTPError as retry_err:
                            if retry_err.response.status_code != 429:
                                raise  # Re-raise if it's not a rate limit error
                elif 400 <= response.status_code < 500:
                    print(f"Client error occurred: {http_err} - Status Code: {response.status_code}")
                    if response.status_code == 401:  # Unauthorized
                        switch_api_key()  # Try another key
                        headers = {"X-CMC_PRO_API_KEY": CMC_API_KEYS[current_api_key_index]}
                    else:
                        return results  # Return partial results for other client errors
                else:  # 500+ server errors
                    print(f"Server error occurred: {http_err} - Status Code: {response.status_code}")
                    time.sleep(2)  # Wait before retry on server error
            except requests.exceptions.RequestException as e:
                print(f"Error fetching crypto prices: {e}")
                retry_count = 0
                max_retries = 3
                retry_delay = 1  # Initial delay in seconds
                
                while retry_count < max_retries:
                    try:
                        print(f"Retrying request (attempt {retry_count + 1}/{max_retries})...")
                        time.sleep(retry_delay)
                        
                        # Switch API key before retry
                        switch_api_key()
                        headers = {"X-CMC_PRO_API_KEY": CMC_API_KEYS[current_api_key_index]}
                        
                        response = requests.get(url, params=params, headers=headers, timeout=10)
                        response.raise_for_status()
                        
                        if response.status_code == 200:
                            data = response.json().get("data", {})
                            fetch_time = datetime.now(timezone.utc)
                            for symbol in symbols_to_fetch:
                                if symbol in data and 'quote' in data[symbol] and 'USD' in data[symbol]['quote']:
                                    price_data = data[symbol]["quote"]["USD"]
                                    results[symbol] = price_data
                                    crypto_price_cache[symbol] = (price_data, fetch_time)
                            return results
                            
                    except requests.exceptions.RequestException as retry_error:
                        print(f"Retry attempt {retry_count + 1} failed: {retry_error}")
                        retry_count += 1
                        retry_delay *= 2  # Exponential backoff
                
                print("All retry attempts failed. Returning partial results.")
                break

    return results

def switch_api_key():
    """
    Switches to the next available CoinMarketCap API key.
    """
    global current_api_key_index
    current_api_key_index = (current_api_key_index + 1) % len(CMC_API_KEYS)

def get_currency_rate(from_currency, to_currency):
    """
    Fetches the currency conversion rate from ExchangeRate-API, using cache if available.

    Args:
        from_currency (str): The source currency code.
        to_currency (str): The target currency code.

    Returns:
        float: The conversion rate, or None if an error occurs or rate not found.
    """
    global current_exchange_rate_api_key_index, exchange_rate_cache
    cache_key = (from_currency, to_currency)
    now = datetime.now(timezone.utc)

    # Check cache
    if cache_key in exchange_rate_cache:
        rate, timestamp = exchange_rate_cache[cache_key]
        if now - timestamp < EXCHANGE_RATE_CACHE_DURATION:
            return rate

    # Fetch from API if not in cache or expired
    while True:
        current_api_key = EXCHANGE_RATE_API_KEYS[current_exchange_rate_api_key_index]
        try:
            url = f"https://v6.exchangerate-api.com/v6/{current_api_key}/pair/{from_currency}/{to_currency}"
            # Using the /pair endpoint is more direct
            response = requests.get(url, timeout=10) # Added timeout
            response.raise_for_status()

            data = response.json()
            if data.get("result") == "success":
                rate = data.get('conversion_rate')
                if rate is not None:
                    exchange_rate_cache[cache_key] = (float(rate), datetime.now(timezone.utc)) # Update cache
                    return float(rate)
                else:
                    print(f"Error: 'conversion_rate' not found in ExchangeRate-API response for {from_currency}/{to_currency}. Response: {data}")
                    return None # Rate not found in successful response
            elif data.get("error-type") == "invalid-key" or data.get("error-type") == "inactive-account":
                 print(f"ExchangeRate-API key {current_exchange_rate_api_key_index} is invalid or inactive. Switching key.")
                 switch_exchange_rate_api_key()
                 # Continue loop to retry with new key
            elif data.get("error-type") == "unsupported-code":
                 print(f"Error: Unsupported currency code used: {from_currency} or {to_currency}")
                 return None # Unsupported currency
            else:
                print(f"Error: ExchangeRate-API request failed. Response: {data}")
                error_type = data.get("error-type", "unknown")
                
                # Switch API key for specific error types that might benefit from using a different key
                if error_type in ["quota-reached", "plan-upgrade-required", "server-error"]:
                    print(f"Switching API key due to error: {error_type}")
                    switch_exchange_rate_api_key()
                    continue  # Retry with new key
                
                # For rate limiting, implement exponential backoff
                if error_type == "rate-limit-reached":
                    retry_delay = 2
                    max_retries = 3
                    for retry in range(max_retries):
                        print(f"Rate limit reached. Waiting {retry_delay} seconds before retry {retry + 1}/{max_retries}")
                        time.sleep(retry_delay)
                        retry_delay *= 2
                        switch_exchange_rate_api_key()
                        continue
                
                return None  # Failed for other unrecoverable reasons

        except requests.exceptions.RequestException as e:
            print(f"Error fetching exchange rate: {e}")
            retry_count = 0
            max_retries = 3
            retry_delay = 1  # Initial delay in seconds
            
            while retry_count < max_retries:
                try:
                    print(f"Retrying exchange rate request (attempt {retry_count + 1}/{max_retries})...")
                    time.sleep(retry_delay)
                    
                    # Switch API key before retry
                    switch_exchange_rate_api_key()
                    current_api_key = EXCHANGE_RATE_API_KEYS[current_exchange_rate_api_key_index]
                    
                    url = f"https://v6.exchangerate-api.com/v6/{current_api_key}/pair/{from_currency}/{to_currency}"
                    response = requests.get(url, timeout=10)
                    response.raise_for_status()
                    
                    data = response.json()
                    if data.get("result") == "success":
                        rate = data.get('conversion_rate')
                        if rate is not None:
                            exchange_rate_cache[cache_key] = (float(rate), datetime.now(timezone.utc))
                            return float(rate)
                    
                except requests.exceptions.RequestException as retry_error:
                    print(f"Retry attempt {retry_count + 1} failed: {retry_error}")
                    retry_count += 1
                    retry_delay *= 2  # Exponential backoff
            
            print("All retry attempts failed")
            return None  # Return None after all retries exhausted

def switch_exchange_rate_api_key():
    """
    Switches to the next available ExchangeRate-API key.
    """
    global current_exchange_rate_api_key_index
    current_exchange_rate_api_key_index = (current_exchange_rate_api_key_index + 1) % len(EXCHANGE_RATE_API_KEYS)

def format_large_number(num):
    """Formats big numbers in a compact way: 1.23T / 45.60B / 7.80M / 9.10K."""
    try:
        num = float(num)
    except (TypeError, ValueError):
        return "N/A"

    for threshold, suffix in ((1_000_000_000_000, "T"), (1_000_000_000, "B"),
                              (1_000_000, "M"), (1_000, "K")):
        if abs(num) >= threshold:
            return f"{num / threshold:.2f}{suffix}"
    return f"{num:,.2f}"


def format_price(value):
    """Formats a price with a precision that suits its magnitude."""
    if value is None:
        return "N/A"
    magnitude = abs(value)
    if magnitude >= 1000:
        return f"{value:,.2f}"
    if magnitude >= 1:
        return f"{value:,.4f}"
    if magnitude >= 0.0001:
        return f"{value:,.6f}"
    return f"{value:.8f}"


def calculate_age(timestamp_ms):
    if not timestamp_ms:
        return "N/A"
    dt_object = datetime.fromtimestamp(timestamp_ms / 1000, timezone.utc)
    now = datetime.now(timezone.utc)
    delta = now - dt_object
    days = delta.days
    hours = delta.seconds // 3600
    if days > 0:
        return f"{days}d"
    elif hours > 0:
        return f"{hours}h"
    else:
        return "<1h"

def get_ton_token_info(address):
    """Fetches TON token information from DexScreener using a contract address."""
    try:
        api_url = DEXSCREENER_API_URL.format(address=address)
        response = requests.get(api_url)
        response.raise_for_status() # Raise an exception for bad status codes
        data = response.json()

        if data and data.get('pairs'):
            # Filtering for TON pairs specifically
            ton_pairs = [p for p in data['pairs'] if p.get('chainId') == 'ton']
            if not ton_pairs:
                 print(f"No TON pair found for address: {address}")
                 return None, "No TON pair found."

            # Sort by liquidity or volume if needed, here just taking the first TON pair
            pair = ton_pairs[0]

            # Extract data
            base_token = pair.get('baseToken', {})
            token_name = base_token.get('name', 'N/A')
            token_symbol = base_token.get('symbol', 'N/A')
            price_usd_str = pair.get('priceUsd', '0')
            price_usd = float(price_usd_str) if price_usd_str else 0.0
            price_change_h1 = pair.get('priceChange', {}).get('h1', 0)
            price_change_h24 = pair.get('priceChange', {}).get('h24', 0)
            volume_h24 = pair.get('volume', {}).get('h24', 0)
            liquidity_usd = pair.get('liquidity', {}).get('usd', 0)
            market_cap = pair.get('fdv', 0) # Using FDV as Market Cap proxy
            pair_created_at = pair.get('pairCreatedAt') # Timestamp in ms
            dexscreener_url = pair.get('url', '#')

            # Calculate age
            age = calculate_age(pair_created_at)

            response_text = (
                f"💎 *{token_name} (${token_symbol})*\n"
                f"`{address}`\n\n"
                f"⛓️ Chain: TON | ⏳ Age: {age}\n\n"
                f"📊 *Token Stats*\n"
                f" ├─ Price: *${price_usd:.6f}*\n"
                f" ├─ 1H Change: {price_change_h1:+.2f}%\n"
                f" ├─ 24H Change: {price_change_h24:+.2f}%\n"
                f" ├─ Volume (24H): *${format_large_number(volume_h24)}*\n"
                f" ├─ Liquidity: *${format_large_number(liquidity_usd)}*\n"
                f" └─ Market Cap (FDV): *${format_large_number(market_cap)}*\n\n"
                f"🔗 [View on DexScreener]({dexscreener_url})"
            )
            return response_text, None # Success

        else:
            print(f"No pair data found on DexScreener for address: {address}")
            return None, f"⚠️ Could not find token information for address: `{address}`"

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from DexScreener for {address}: {e}")
        return None, "⚠️ Error fetching token data from DexScreener. Please try again later."
    except Exception as e:
        print(f"An unexpected error occurred while processing address {address}: {e}")
        return None, "⚠️ An unexpected error occurred while processing the address."


# Caches for the market-data helpers below
top_cryptocurrencies_cache = {}
TOP_CACHE_DURATION = timedelta(minutes=10)

fear_greed_cache = {}
FEAR_GREED_CACHE_DURATION = timedelta(minutes=30)


def _cmc_get(url, params):
    """Performs a CoinMarketCap request, rotating keys on auth/limit errors.

    Args:
        url (str): CoinMarketCap endpoint.
        params (dict): Query parameters.

    Returns:
        dict: The parsed JSON response, or None if every key failed.
    """
    for _ in range(max(1, len(CMC_API_KEYS))):
        headers = {"X-CMC_PRO_API_KEY": CMC_API_KEYS[current_api_key_index]}
        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            status_code = http_err.response.status_code if http_err.response is not None else None
            if status_code in (401, 402, 429):
                print(f"CMC key #{current_api_key_index + 1} rejected (HTTP {status_code}). Switching key.")
                switch_api_key()
                continue
            print(f"CoinMarketCap request failed: {http_err}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"CoinMarketCap request failed: {e}")
            time.sleep(1)
    print("All CoinMarketCap API keys failed for this request.")
    return None


def get_top_cryptocurrencies(limit=TOP_DEFAULT_LIMIT, convert="USD"):
    """Fetches the highest ranked coins by market cap, using cache if available.

    Args:
        limit (int): How many coins to return (capped at TOP_MAX_LIMIT).
        convert (str): Fiat currency the quotes are converted to.

    Returns:
        list: Coin dicts sorted by rank, or None when the request failed.
    """
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = TOP_DEFAULT_LIMIT
    limit = max(1, min(limit, TOP_MAX_LIMIT))

    now = datetime.now(timezone.utc)
    cached = top_cryptocurrencies_cache.get(convert)
    if cached and now - cached[1] < TOP_CACHE_DURATION:
        return cached[0][:limit]

    # Always request the maximum so a bigger /top does not cost another call.
    payload = _cmc_get(CMC_LISTINGS_URL, {
        "start": 1,
        "limit": TOP_MAX_LIMIT,
        "convert": convert,
        "sort": "market_cap",
    })
    if not payload or not payload.get("data"):
        return None

    coins = []
    for entry in payload["data"]:
        quote = entry.get("quote", {}).get(convert, {})
        if quote.get("price") is None:
            continue
        coins.append({
            "rank": entry.get("cmc_rank"),
            "symbol": entry.get("symbol", "?"),
            "name": entry.get("name", "?"),
            "price": quote.get("price"),
            "percent_change_24h": quote.get("percent_change_24h") or 0.0,
            "market_cap": quote.get("market_cap") or 0,
            "volume_24h": quote.get("volume_24h") or 0,
        })

    if not coins:
        return None

    top_cryptocurrencies_cache[convert] = (coins, datetime.now(timezone.utc))
    return coins[:limit]


def get_fear_greed_index():
    """Fetches the Crypto Fear & Greed Index (alternative.me, no API key needed).

    Returns:
        dict: {"value": int, "classification": str, "updated": datetime}, or None.
    """
    now = datetime.now(timezone.utc)
    cached = fear_greed_cache.get("latest")
    if cached and now - cached[1] < FEAR_GREED_CACHE_DURATION:
        return cached[0]

    try:
        response = requests.get(FEAR_GREED_API_URL, timeout=10)
        response.raise_for_status()
        entries = response.json().get("data") or []
        if not entries:
            print("Fear & Greed API returned no data.")
            return None

        entry = entries[0]
        result = {
            "value": int(entry.get("value", 0)),
            "classification": entry.get("value_classification", "Unknown"),
            "updated": datetime.fromtimestamp(int(entry.get("timestamp", 0)), timezone.utc),
        }
        fear_greed_cache["latest"] = (result, datetime.now(timezone.utc))
        return result
    except (requests.exceptions.RequestException, ValueError, TypeError, KeyError) as e:
        print(f"Error fetching Fear & Greed index: {e}")
        return None


def convert_currency(amount, from_currency, to_currency):
    """Converts an amount between any supported fiat/crypto pair.

    Args:
        amount (float): Amount of from_currency.
        from_currency (str): Source currency code.
        to_currency (str): Target currency code.

    Returns:
        tuple: (converted amount, None) on success, or (None, error message).
    """
    if from_currency == to_currency:
        return amount, None

    is_from_crypto = from_currency in CRYPTO_SYMBOLS
    is_to_crypto = to_currency in CRYPTO_SYMBOLS

    # Fiat to fiat
    if not is_from_crypto and not is_to_crypto:
        rate = get_currency_rate(from_currency, to_currency)
        if rate is None:
            return None, f"Could not get rate for {from_currency}/{to_currency}."
        return amount * rate, None

    # Crypto to fiat
    if is_from_crypto and not is_to_crypto:
        price_data = get_crypto_prices([from_currency]).get(from_currency)
        if not price_data or price_data.get("price") is None:
            return None, f"Could not get price for ${from_currency}."
        usd_value = amount * price_data["price"]
        if to_currency == "USD":
            return usd_value, None
        rate = get_currency_rate("USD", to_currency)
        if rate is None:
            return None, f"Could not get rate for USD/{to_currency}."
        return usd_value * rate, None

    # Fiat to crypto
    if not is_from_crypto and is_to_crypto:
        price_data = get_crypto_prices([to_currency]).get(to_currency)
        if not price_data or price_data.get("price") is None:
            return None, f"Could not get price for ${to_currency}."
        crypto_price = price_data["price"]
        if crypto_price <= 0:
            return None, f"Price for ${to_currency} is zero."
        if from_currency == "USD":
            return amount / crypto_price, None
        rate = get_currency_rate(from_currency, "USD")
        if rate is None:
            return None, f"Could not get rate for {from_currency}/USD."
        return (amount * rate) / crypto_price, None

    # Crypto to crypto
    prices = get_crypto_prices([from_currency, to_currency])
    from_data = prices.get(from_currency)
    to_data = prices.get(to_currency)
    missing = []
    if not from_data or from_data.get("price") is None:
        missing.append(from_currency)
    if not to_data or to_data.get("price") is None:
        missing.append(to_currency)
    if missing:
        return None, f"Could not get price for ${' and $'.join(missing)}."
    if to_data["price"] <= 0:
        return None, f"Price for ${to_currency} is zero."
    return amount * (from_data["price"] / to_data["price"]), None
