import pytest
import pandas as pd
from quant.strategies.random_monkey import RandomMonkeyStrategy
from quant.strategies.base import Signal


def test_random_monkey_initialization():
    """测试随机策略初始化"""
    strategy = RandomMonkeyStrategy(seed=42, buy_prob=0.3, sell_prob=0.3)
    assert strategy.seed == 42
    assert strategy.buy_prob == 0.3
    assert strategy.sell_prob == 0.3
    assert strategy.name() == "RandomMonkey(seed=42)"


def test_random_monkey_signal_generation():
    """测试随机信号生成的可复现性"""
    strategy = RandomMonkeyStrategy(seed=42)

    # 创建测试数据
    df = pd.DataFrame({
        'close': [100, 101, 102, 103, 104]
    })

    # 同一个 index 应该生成相同的信号
    signal1 = strategy.generate_signal(df, 2)
    signal2 = strategy.generate_signal(df, 2)
    assert signal1 == signal2

    # 验证信号类型正确
    assert signal1 in [Signal.BUY, Signal.SELL, Signal.HOLD]


def test_random_monkey_probability_distribution():
    """测试概率分布是否符合预期"""
    strategy = RandomMonkeyStrategy(seed=42, buy_prob=0.3, sell_prob=0.3)

    df = pd.DataFrame({
        'close': [100] * 1000
    })

    # 生成大量信号并统计分布
    signals = [strategy.generate_signal(df, i) for i in range(1000)]
    buy_count = signals.count(Signal.BUY)
    sell_count = signals.count(Signal.SELL)
    hold_count = signals.count(Signal.HOLD)

    # 允许 5% 的误差范围
    assert 250 <= buy_count <= 350  # 预期 30%
    assert 250 <= sell_count <= 350  # 预期 30%
    assert 350 <= hold_count <= 450  # 预期 40%
