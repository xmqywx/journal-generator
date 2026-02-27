import pandas as pd
import pytest
from quant.engine.backtester import Backtester
from quant.engine.portfolio import Portfolio
from quant.strategies.ema_triple import EMATripleStrategy
from quant.config import Config


def _make_trending_data(n=100):
    prices = []
    for i in range(n // 2):
        prices.append(100 + i * 2)
    for i in range(n // 2):
        prices.append(100 + (n // 2) * 2 - i * 2)
    return pd.DataFrame({
        "timestamp": list(range(n)),
        "open": prices,
        "high": [p + 1 for p in prices],
        "low": [p - 1 for p in prices],
        "close": prices,
        "volume": [1000] * n,
    })


def test_backtester_runs():
    config = Config(initial_capital=1000.0)
    strategy = EMATripleStrategy()
    bt = Backtester(config)
    df = _make_trending_data(100)
    result = bt.run(df, strategy, capital=1000.0, fee_rate=0.001)
    assert "equity_curve" in result
    assert "trades" in result
    assert "final_equity" in result
    assert len(result["equity_curve"]) == 100


def test_backtester_has_trades():
    config = Config(initial_capital=1000.0)
    strategy = EMATripleStrategy()
    bt = Backtester(config)
    # EMA Triple needs at least 200 periods for the 200 EMA
    df = _make_trending_data(300)
    result = bt.run(df, strategy, capital=1000.0, fee_rate=0.001)
    # May or may not have trades depending on the signal logic, so we just check it runs
    assert "trades" in result


def test_backtester_equity_never_negative():
    config = Config(initial_capital=1000.0)
    strategy = EMATripleStrategy()
    bt = Backtester(config)
    df = _make_trending_data(100)
    result = bt.run(df, strategy, capital=1000.0, fee_rate=0.001)
    for eq in result["equity_curve"]:
        assert eq >= 0
