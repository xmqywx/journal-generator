import pytest
import pandas as pd
import numpy as np
from quant.strategies.dynamic_grid import DynamicGridStrategy
from quant.strategies.base import Signal


def test_dynamic_grid_initialization():
    """测试动态网格策略初始化"""
    strategy = DynamicGridStrategy(
        atr_period=14,
        base_spacing=0.02,
        atr_multiplier=1.0,
        levels=7,
    )
    assert strategy.atr_period == 14
    assert strategy.base_spacing == 0.02
    assert strategy.atr_multiplier == 1.0
    assert strategy.levels == 7
    assert strategy.name() == "DynamicGrid(7L,2.0%)"
    assert strategy.min_periods() == 14


def test_atr_calculation():
    """测试 ATR 计算"""
    strategy = DynamicGridStrategy()

    # 创建测试数据
    df = pd.DataFrame({
        'high': [102, 105, 103, 107, 106],
        'low': [98, 101, 99, 103, 102],
        'close': [100, 104, 101, 105, 104],
    })

    atr = strategy._calculate_atr(df, 3)
    assert atr > 0
    assert isinstance(atr, float)


def test_dynamic_spacing_calculation():
    """测试动态间距计算"""
    strategy = DynamicGridStrategy(
        base_spacing=0.02,
        atr_multiplier=1.0,
    )

    # 模拟 ATR = 2.0, 价格 = 100
    spacing = strategy._calculate_spacing(atr=2.0, price=100.0)

    # ATR% = 2/100 = 0.02
    # spacing = 0.02 * (1 + 1.0 * 0.02) = 0.02 * 1.02 = 0.0204
    expected = 0.02 * (1 + 1.0 * 0.02)
    assert abs(spacing - expected) < 0.0001

    # 测试间距限制 [0.01, 0.04]
    spacing_low = strategy._calculate_spacing(atr=0.01, price=100.0)
    assert spacing_low >= 0.01

    spacing_high = strategy._calculate_spacing(atr=10.0, price=100.0)
    assert spacing_high <= 0.04


def test_grid_initialization():
    """测试网格初始化"""
    strategy = DynamicGridStrategy(
        base_spacing=0.02,
        levels=7,
    )

    # 初始化网格，中心价 100
    strategy._initialize_grid(center_price=100.0, spacing=0.02)

    assert strategy.initialized is True
    assert strategy.center_price == 100.0
    assert len(strategy.grid_prices) == 7

    # 验证网格价格
    # 7层: -3, -2, -1, 0, +1, +2, +3
    # 每层间隔 2%
    expected_prices = [
        100 * (1 - 0.02) ** 3,  # -3: ~94.12
        100 * (1 - 0.02) ** 2,  # -2: ~96.04
        100 * (1 - 0.02) ** 1,  # -1: ~98.00
        100,                     #  0: 100.00
        100 * (1 + 0.02) ** 1,  # +1: ~102.00
        100 * (1 + 0.02) ** 2,  # +2: ~104.04
        100 * (1 + 0.02) ** 3,  # +3: ~106.12
    ]

    for i, (actual, expected) in enumerate(zip(strategy.grid_prices, expected_prices)):
        assert abs(actual - expected) < 0.01, f"Level {i}: {actual} != {expected}"


def test_grid_reset():
    """测试网格重置"""
    strategy = DynamicGridStrategy(levels=7)

    # 初始化网格
    strategy._initialize_grid(center_price=100.0, spacing=0.02)
    strategy.positions[0] = 100.0  # 模拟持仓

    # 重置网格
    strategy._reset_grid(new_center=110.0, spacing=0.02)

    assert strategy.center_price == 110.0
    assert len(strategy.positions) == 0  # 持仓清空
    assert strategy.grid_prices[3] == 110.0  # 中心层


def test_check_breakout():
    """测试价格突破检测"""
    strategy = DynamicGridStrategy(levels=7)
    strategy._initialize_grid(center_price=100.0, spacing=0.02)

    # 价格在网格范围内
    assert strategy._check_breakout(100.0) is False
    assert strategy._check_breakout(95.0) is False

    # 价格突破上方
    assert strategy._check_breakout(110.0) is True

    # 价格突破下方
    assert strategy._check_breakout(90.0) is True


def test_signal_generation_initial():
    """测试首次信号生成（初始化网格）"""
    strategy = DynamicGridStrategy(
        atr_period=3,
        base_spacing=0.02,
        levels=7,
    )

    df = pd.DataFrame({
        'high': [102, 105, 103, 107],
        'low': [98, 101, 99, 103],
        'close': [100, 104, 101, 105],
    })

    # 首次调用应该初始化网格并返回 HOLD
    signal = strategy.generate_signal(df, 3)

    assert strategy.initialized is True
    assert strategy.center_price == 105.0  # 当前价格
    assert len(strategy.grid_prices) == 7
    assert signal == Signal.HOLD


def test_signal_generation_buy():
    """测试买入信号生成"""
    strategy = DynamicGridStrategy(
        atr_period=3,
        base_spacing=0.02,
        levels=7,
    )

    df = pd.DataFrame({
        'high': [102, 105, 103, 107, 105, 102],
        'low': [98, 101, 99, 103, 101, 98],
        'close': [100, 104, 101, 105, 103, 100],
    })

    # 初始化网格（index 3, price=105）
    # Grid will be: ~[98.52, 100.63, 102.79, 105.00, 107.21, 109.46, 111.76]
    strategy.generate_signal(df, 3)

    # 价格下跌到 103（index 4），触发买入（level 2）
    signal1 = strategy.generate_signal(df, 4)
    assert signal1 == Signal.BUY

    # 价格继续下跌到 100（index 5），应该触发买入（level 1）
    signal2 = strategy.generate_signal(df, 5)
    assert signal2 == Signal.BUY


def test_signal_generation_sell():
    """测试卖出信号生成"""
    strategy = DynamicGridStrategy(
        atr_period=3,
        base_spacing=0.02,
        levels=7,
    )

    df = pd.DataFrame({
        'high': [102, 105, 103, 102, 105, 107],
        'low': [98, 101, 99, 98, 101, 103],
        'close': [100, 104, 101, 100, 103, 105],
    })

    # 初始化网格（index 3, price=100）
    # Grid will be: ~[93.85, 95.86, 97.91, 100.00, 102.09, 104.23, 106.41]
    strategy.generate_signal(df, 3)

    # 先买入（模拟持仓）
    strategy.positions[2] = 98.0  # 在较低层有持仓

    # 价格上涨到 105（index 5），应该触发卖出（level 6）
    signal = strategy.generate_signal(df, 5)
    assert signal == Signal.SELL


def test_grid_reset_on_breakout():
    """测试价格突破时重置网格"""
    strategy = DynamicGridStrategy(
        atr_period=3,
        base_spacing=0.02,
        levels=7,
    )

    df = pd.DataFrame({
        'high': [102, 105, 103, 102, 125],
        'low': [98, 101, 99, 98, 121],
        'close': [100, 104, 101, 100, 123],
    })

    # 初始化网格（index 3, price=100）
    strategy.generate_signal(df, 3)
    old_center = strategy.center_price

    # 价格突破到 123（index 4），应该重置网格
    strategy.generate_signal(df, 4)

    assert strategy.center_price != old_center
    assert abs(strategy.center_price - 123) < 1.0  # 新中心接近当前价格
