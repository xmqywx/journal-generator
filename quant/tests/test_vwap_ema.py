import pandas as pd
import numpy as np
from quant.strategies.vwap_ema import VWAPEMAStrategy
from quant.strategies.base import Signal


def test_strategy_initialization():
    """Test strategy initializes with correct name"""
    strategy = VWAPEMAStrategy()
    assert strategy.name() == "VWAP_EMA(24h/21)"


def test_min_periods():
    """Test strategy requires 45 periods (24 for VWAP + 21 for EMA)"""
    strategy = VWAPEMAStrategy()
    assert strategy.min_periods() == 45


def test_insufficient_data_returns_hold():
    """Test strategy returns HOLD when data insufficient"""
    strategy = VWAPEMAStrategy()
    df = pd.DataFrame({
        'timestamp': range(30),
        'open': [100] * 30,
        'high': [101] * 30,
        'low': [99] * 30,
        'close': [100] * 30,
        'volume': [1000] * 30
    })
    signal = strategy.generate_signal(df, 29)
    assert signal == Signal.HOLD


def test_buy_signal_price_breaks_above_vwap_ema_up():
    """Test BUY when price breaks above VWAP and EMA trending up"""
    strategy = VWAPEMAStrategy()

    # Create scenario: price consolidates below VWAP then breaks above
    periods = 100
    # First 80 periods: price below VWAP
    prices_low = np.linspace(44000, 44500, 80)
    volumes_low = [1000] * 80

    # Last 20 periods: price breaks above VWAP with volume
    prices_high = np.linspace(44600, 46000, 20)
    volumes_high = [2000] * 20

    prices = np.concatenate([prices_low, prices_high])
    volumes = volumes_low + volumes_high

    df = pd.DataFrame({
        'timestamp': range(periods),
        'open': prices,
        'high': prices * 1.01,
        'low': prices * 0.99,
        'close': prices,
        'volume': volumes
    })

    signal = strategy.generate_signal(df, 99)
    assert signal == Signal.BUY


def test_sell_signal_price_breaks_below_vwap_ema_down():
    """Test SELL when price breaks below VWAP and EMA trending down"""
    strategy = VWAPEMAStrategy()

    # Create scenario: price above VWAP then breaks below
    periods = 100
    # First 80 periods: price above VWAP
    prices_high = np.linspace(46000, 46500, 80)
    volumes_high = [1000] * 80

    # Last 20 periods: price breaks below VWAP
    prices_low = np.linspace(46400, 44000, 20)
    volumes_low = [2000] * 20

    prices = np.concatenate([prices_high, prices_low])
    volumes = volumes_high + volumes_low

    df = pd.DataFrame({
        'timestamp': range(periods),
        'open': prices,
        'high': prices * 1.01,
        'low': prices * 0.99,
        'close': prices,
        'volume': volumes
    })

    signal = strategy.generate_signal(df, 99)
    assert signal == Signal.SELL


def test_hold_signal_no_breakout():
    """Test HOLD when no clear breakout"""
    strategy = VWAPEMAStrategy()

    # Sideways price action
    periods = 100
    prices = [45000 + np.sin(i * 0.1) * 200 for i in range(periods)]

    df = pd.DataFrame({
        'timestamp': range(periods),
        'open': prices,
        'high': np.array(prices) * 1.01,
        'low': np.array(prices) * 0.99,
        'close': prices,
        'volume': [1000] * periods
    })

    signal = strategy.generate_signal(df, 99)
    assert signal == Signal.HOLD


def test_get_indicators():
    """Test get_indicators returns VWAP and EMA values"""
    strategy = VWAPEMAStrategy()

    periods = 100
    prices = np.linspace(44000, 46000, periods)
    volumes = [1000 + i * 10 for i in range(periods)]

    df = pd.DataFrame({
        'timestamp': range(periods),
        'open': prices,
        'high': prices * 1.01,
        'low': prices * 0.99,
        'close': prices,
        'volume': volumes
    })

    indicators = strategy.get_indicators(df, 99)

    assert 'vwap' in indicators
    assert 'ema_21' in indicators
    assert 'price' in indicators
    assert 'volume' in indicators
    assert isinstance(indicators['vwap'], (float, np.floating))
    assert indicators['price'] == prices[99]
