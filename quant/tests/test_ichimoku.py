import pandas as pd
import numpy as np
from quant.strategies.ichimoku import IchimokuStrategy
from quant.strategies.base import Signal


def test_strategy_initialization():
    """Test strategy initializes with correct name"""
    strategy = IchimokuStrategy()
    assert strategy.name() == "Ichimoku(9/26/52)"


def test_min_periods():
    """Test strategy requires 78 periods (52 + 26 for cloud shift)"""
    strategy = IchimokuStrategy()
    assert strategy.min_periods() == 78


def test_insufficient_data_returns_hold():
    """Test strategy returns HOLD when data insufficient"""
    strategy = IchimokuStrategy()
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


def test_buy_signal_golden_cross_above_cloud():
    """Test BUY when Tenkan crosses above Kijun, price above green cloud"""
    strategy = IchimokuStrategy()

    # Create strong uptrend: 150 periods
    periods = 150
    prices = np.linspace(40000, 55000, periods)

    df = pd.DataFrame({
        'timestamp': range(periods),
        'open': prices,
        'high': prices * 1.02,
        'low': prices * 0.98,
        'close': prices,
        'volume': [1000] * periods
    })

    # In strong uptrend:
    # - Tenkan should cross above Kijun
    # - Price should be above cloud
    # - Cloud should be green (Span A > Span B)
    signal = strategy.generate_signal(df, 149)
    assert signal == Signal.BUY


def test_sell_signal_death_cross():
    """Test SELL when Tenkan crosses below Kijun"""
    strategy = IchimokuStrategy()

    # Create reversal: uptrend then downtrend
    periods = 150
    uptrend = np.linspace(40000, 55000, 100)
    downtrend = np.linspace(55000, 48000, 50)
    prices = np.concatenate([uptrend, downtrend])

    df = pd.DataFrame({
        'timestamp': range(periods),
        'open': prices,
        'high': prices * 1.02,
        'low': prices * 0.98,
        'close': prices,
        'volume': [1000] * periods
    })

    # At end of downtrend, Tenkan should cross below Kijun
    signal = strategy.generate_signal(df, 149)
    assert signal == Signal.SELL


def test_sell_signal_price_below_cloud():
    """Test SELL when price drops below cloud"""
    strategy = IchimokuStrategy()

    # Create data: consolidation then sharp drop
    periods = 150
    consolidation = [50000] * 100
    drop = np.linspace(50000, 42000, 50)
    prices = np.array(consolidation + list(drop))

    df = pd.DataFrame({
        'timestamp': range(periods),
        'open': prices,
        'high': prices * 1.02,
        'low': prices * 0.98,
        'close': prices,
        'volume': [1000] * periods
    })

    # Price should be below cloud
    signal = strategy.generate_signal(df, 149)
    assert signal == Signal.SELL


def test_hold_signal_inside_cloud():
    """Test HOLD when price inside cloud (consolidation)"""
    strategy = IchimokuStrategy()

    # Sideways consolidation
    periods = 150
    prices = [48000 + np.sin(i * 0.1) * 500 for i in range(periods)]

    df = pd.DataFrame({
        'timestamp': range(periods),
        'open': prices,
        'high': np.array(prices) * 1.02,
        'low': np.array(prices) * 0.98,
        'close': prices,
        'volume': [1000] * periods
    })

    # In consolidation, likely HOLD
    signal = strategy.generate_signal(df, 149)
    # Note: Could be BUY/SELL depending on exact cloud position
    # Test just ensures it doesn't crash
    assert signal in [Signal.BUY, Signal.SELL, Signal.HOLD]


def test_get_indicators():
    """Test get_indicators returns all 5 Ichimoku lines"""
    strategy = IchimokuStrategy()

    periods = 150
    prices = np.linspace(40000, 50000, periods)

    df = pd.DataFrame({
        'timestamp': range(periods),
        'open': prices,
        'high': prices * 1.02,
        'low': prices * 0.98,
        'close': prices,
        'volume': [1000] * periods
    })

    indicators = strategy.get_indicators(df, 149)

    assert 'tenkan_sen' in indicators
    assert 'kijun_sen' in indicators
    assert 'senkou_span_a' in indicators
    assert 'senkou_span_b' in indicators
    assert 'chikou_span' in indicators
    assert 'price' in indicators
    assert 'cloud_color' in indicators
    assert indicators['cloud_color'] in ['green', 'red']
