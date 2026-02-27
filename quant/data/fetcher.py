import time
import pandas as pd
import requests

OKX_BASE_URL = "https://www.okx.com"
BINANCE_BASE_URL = "https://api.binance.com"

# Mapping from OKX-style timeframes to Binance intervals
_BINANCE_INTERVALS = {
    "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
    "1H": "1h", "4H": "4h", "1D": "1d", "1W": "1w",
}


class OKXFetcher:
    """Fetch historical candle data from OKX public API."""

    def fetch_candles(
        self, symbol: str, timeframe: str = "1H", limit: int = 100, after: str = ""
    ) -> pd.DataFrame:
        url = f"{OKX_BASE_URL}/api/v5/market/candles"
        params = {"instId": symbol, "bar": timeframe, "limit": str(limit)}
        if after:
            params["after"] = after

        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if data["code"] != "0" or not data["data"]:
            return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

        rows = []
        for candle in data["data"]:
            rows.append({
                "timestamp": int(candle[0]),
                "open": float(candle[1]),
                "high": float(candle[2]),
                "low": float(candle[3]),
                "close": float(candle[4]),
                "volume": float(candle[5]),
            })

        df = pd.DataFrame(rows)
        df.sort_values("timestamp", inplace=True)
        df.reset_index(drop=True, inplace=True)
        return df

    def fetch_history(self, symbol: str, timeframe: str = "1H", days: int = 365) -> pd.DataFrame:
        """Fetch multiple pages of historical data."""
        all_frames = []
        after = ""
        target_ts = int((time.time() - days * 86400) * 1000)

        while True:
            df = self.fetch_candles(symbol, timeframe, limit=100, after=after)
            if df.empty:
                break
            all_frames.append(df)
            earliest_ts = int(df["timestamp"].iloc[0])
            if earliest_ts <= target_ts:
                break
            after = str(earliest_ts)
            time.sleep(0.1)  # rate limit

        if not all_frames:
            return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

        result = pd.concat(all_frames, ignore_index=True)
        result.drop_duplicates(subset=["timestamp"], inplace=True)
        result.sort_values("timestamp", inplace=True)
        result.reset_index(drop=True, inplace=True)
        result = result[result["timestamp"] >= target_ts].reset_index(drop=True)
        return result


class BinanceFetcher:
    """Fetch historical candle data from Binance public API (2017-present)."""

    def _to_binance_symbol(self, symbol: str) -> str:
        """Convert OKX-style symbol (BTC-USDT) to Binance style (BTCUSDT)."""
        return symbol.replace("-", "")

    def _to_binance_interval(self, timeframe: str) -> str:
        return _BINANCE_INTERVALS.get(timeframe, "1h")

    def fetch_candles(
        self, symbol: str, timeframe: str = "1H", limit: int = 1000,
        start_time: int = 0, end_time: int = 0,
    ) -> pd.DataFrame:
        url = f"{BINANCE_BASE_URL}/api/v3/klines"
        params = {
            "symbol": self._to_binance_symbol(symbol),
            "interval": self._to_binance_interval(timeframe),
            "limit": limit,
        }
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time

        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        if not data:
            return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

        rows = []
        for candle in data:
            rows.append({
                "timestamp": int(candle[0]),
                "open": float(candle[1]),
                "high": float(candle[2]),
                "low": float(candle[3]),
                "close": float(candle[4]),
                "volume": float(candle[5]),
            })

        df = pd.DataFrame(rows)
        df.sort_values("timestamp", inplace=True)
        df.reset_index(drop=True, inplace=True)
        return df

    def fetch_history(self, symbol: str, timeframe: str = "1H", days: int = 365) -> pd.DataFrame:
        """Fetch complete historical data via pagination (up to years of data)."""
        all_frames = []
        target_ts = int((time.time() - days * 86400) * 1000)
        current_start = target_ts

        while True:
            df = self.fetch_candles(symbol, timeframe, limit=1000, start_time=current_start)
            if df.empty:
                break
            all_frames.append(df)
            latest_ts = int(df["timestamp"].iloc[-1])
            # Move forward past the last candle
            current_start = latest_ts + 1
            if current_start >= int(time.time() * 1000):
                break
            time.sleep(0.05)  # Binance rate limit is generous

        if not all_frames:
            return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

        result = pd.concat(all_frames, ignore_index=True)
        result.drop_duplicates(subset=["timestamp"], inplace=True)
        result.sort_values("timestamp", inplace=True)
        result.reset_index(drop=True, inplace=True)
        return result
