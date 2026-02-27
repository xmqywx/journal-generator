import pandas as pd
import pytest
from quant.strategies.base import Strategy, Signal


def test_signal_enum():
    assert Signal.BUY.value == "BUY"
    assert Signal.SELL.value == "SELL"
    assert Signal.HOLD.value == "HOLD"


class DummyStrategy(Strategy):
    def name(self) -> str:
        return "dummy"

    def generate_signal(self, df: pd.DataFrame, index: int) -> Signal:
        if df["close"].iloc[index] > 100:
            return Signal.BUY
        return Signal.HOLD


def test_strategy_subclass():
    strategy = DummyStrategy()
    df = pd.DataFrame({"close": [90, 95, 101, 98]})
    assert strategy.generate_signal(df, 0) == Signal.HOLD
    assert strategy.generate_signal(df, 2) == Signal.BUY
    assert strategy.name() == "dummy"
