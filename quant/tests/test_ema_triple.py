import pandas as pd
import numpy as np
from quant.strategies.ema_triple import EMATripleStrategy
from quant.strategies.base import Signal


def test_strategy_initialization():
    """Test strategy initializes with correct name"""
    strategy = EMATripleStrategy()
    assert strategy.name() == "EMA_Triple(9/21/200)"


def test_min_periods():
    """Test strategy requires 200 periods minimum"""
    strategy = EMATripleStrategy()
    assert strategy.min_periods() == 200


def test_insufficient_data_returns_hold():
    """Test strategy returns HOLD when data insufficient"""
    strategy = EMATripleStrategy()
    df = pd.DataFrame({
        'timestamp': range(50),
        'open': [100] * 50,
        'high': [101] * 50,
        'low': [99] * 50,
        'close': [100] * 50,
        'volume': [1000] * 50
    })
    signal = strategy.generate_signal(df, 49)
    assert signal == Signal.HOLD


def test_buy_signal_golden_cross_above_200ema():
    """Test BUY when 9 EMA crosses above 21 EMA and price > 200 EMA"""
    strategy = EMATripleStrategy()

    # Create uptrend data: 250 periods
    periods = 250
    prices = np.linspace(40000, 50000, periods)
    df = pd.DataFrame({
        'timestamp': range(periods),
        'open': prices,
        'high': prices * 1.01,
        'low': prices * 0.99,
        'close': prices,
        'volume': [1000] * periods
    })

    # At index 249, we should have:
    # - 9 EMA recently crossed above 21 EMA (uptrend)
    # - Price > 200 EMA (above long-term trend)
    signal = strategy.generate_signal(df, 249)
    assert signal == Signal.BUY


def test_sell_signal_death_cross():
    """Test SELL when 9 EMA crosses below 21 EMA"""
    strategy = EMATripleStrategy()

    # Create data: uptrend then downtrend
    periods = 250
    uptrend = np.linspace(40000, 50000, 200)
    downtrend = np.linspace(50000, 45000, 50)
    prices = np.concatenate([uptrend, downtrend])

    df = pd.DataFrame({
        'timestamp': range(periods),
        'open': prices,
        'high': prices * 1.01,
        'low': prices * 0.99,
        'close': prices,
        'volume': [1000] * periods
    })

    # At end of downtrend, 9 EMA should cross below 21 EMA
    signal = strategy.generate_signal(df, 249)
    assert signal == Signal.SELL


def test_sell_signal_below_200ema():
    """Test SELL when price drops below 200 EMA"""
    strategy = EMATripleStrategy()

    # Create data: steady at 45k then drop to 42k
    periods = 250
    steady = [45000] * 220
    drop = np.linspace(45000, 42000, 30)
    prices = np.array(steady + list(drop))

    df = pd.DataFrame({
        'timestamp': range(periods),
        'open': prices,
        'high': prices * 1.01,
        'low': prices * 0.99,
        'close': prices,
        'volume': [1000] * periods
    })

    # At end, price should be below 200 EMA
    signal = strategy.generate_signal(df, 249)
    assert signal == Signal.SELL


def test_hold_signal():
    """Test HOLD when conditions not met"""
    strategy = EMATripleStrategy()

    # Sideways market: no clear crossover
    periods = 250
    prices = [45000] * periods

    df = pd.DataFrame({
        'timestamp': range(periods),
        'open': prices,
        'high': [p * 1.01 for p in prices],
        'low': [p * 0.99 for p in prices],
        'close': prices,
        'volume': [1000] * periods
    })

    signal = strategy.generate_signal(df, 249)
    assert signal == Signal.HOLD


def test_get_indicators():
    """Test get_indicators returns EMA values"""
    strategy = EMATripleStrategy()

    periods = 250
    prices = np.linspace(40000, 50000, periods)
    df = pd.DataFrame({
        'timestamp': range(periods),
        'open': prices,
        'high': prices * 1.01,
        'low': prices * 0.99,
        'close': prices,
        'volume': [1000] * periods
    })

    indicators = strategy.get_indicators(df, 249)

    assert 'ema_9' in indicators
    assert 'ema_21' in indicators
    assert 'ema_200' in indicators
    assert 'price' in indicators
    assert isinstance(indicators['ema_9'], (float, np.floating))
    assert indicators['price'] == prices[249]
