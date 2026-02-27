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
