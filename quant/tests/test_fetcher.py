import pandas as pd
import pytest
from unittest.mock import patch, MagicMock
from quant.data.fetcher import OKXFetcher


def _mock_candle_response():
    """Mock OKX API response: [ts, o, h, l, c, vol, volCcy, volCcyQuote, confirm]"""
    return {
        "code": "0",
        "data": [
            ["1700000000000", "37000", "37500", "36800", "37200", "100", "3700000", "3700000", "1"],
            ["1699996400000", "36500", "37100", "36400", "37000", "120", "4440000", "4440000", "1"],
        ]
    }


def test_fetch_candles_returns_dataframe():
    fetcher = OKXFetcher()
    with patch("quant.data.fetcher.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = _mock_candle_response()
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        df = fetcher.fetch_candles("BTC-USDT", "1H", limit=2)

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    assert list(df.columns) == ["timestamp", "open", "high", "low", "close", "volume"]
    assert df["close"].iloc[0] == 37000.0
    assert df["close"].iloc[1] == 37200.0


def test_fetch_candles_sorted_ascending():
    fetcher = OKXFetcher()
    with patch("quant.data.fetcher.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = _mock_candle_response()
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        df = fetcher.fetch_candles("BTC-USDT", "1H", limit=2)

    assert df["timestamp"].iloc[0] < df["timestamp"].iloc[1]
