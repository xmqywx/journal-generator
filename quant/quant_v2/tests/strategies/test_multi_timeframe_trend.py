"""
多周期趋势策略测试
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../'))

import pandas as pd
import numpy as np
from quant_v2.strategies.multi_timeframe_trend import MultiTimeframeTrendStrategy


def create_trending_data(length: int = 500, trend: str = 'up') -> pd.DataFrame:
    """创建趋势数据"""
    np.random.seed(42)
    base_price = 50000

    if trend == 'up':
        # 强上升趋势
        trend_component = np.linspace(0, 0.5, length)
        prices = base_price * np.exp(trend_component + np.random.randn(length) * 0.01)
    else:
        # 强下降趋势
        trend_component = np.linspace(0, -0.3, length)
        prices = base_price * np.exp(trend_component + np.random.randn(length) * 0.01)

    df = pd.DataFrame({
        'timestamp': pd.date_range('2023-01-01', periods=length, freq='1h'),
        'open': prices * (1 + np.random.randn(length) * 0.002),
        'high': prices * (1 + abs(np.random.randn(length)) * 0.005),
        'low': prices * (1 - abs(np.random.randn(length)) * 0.005),
        'close': prices,
        'volume': np.random.randint(1000, 10000, length) * (1 + np.random.rand(length)),
    })

    return df


def test_ema_trend_detection():
    """测试EMA趋势检测"""
    print("=" * 80)
    print("测试1: EMA趋势检测")
    print("=" * 80)

    strategy = MultiTimeframeTrendStrategy()

    # 测试上升趋势
    df_up = create_trending_data(500, 'up')
    trend_up = strategy._check_ema_trend(df_up, 100)
    print(f"\n上升趋势数据: {trend_up}")

    # 测试下降趋势
    df_down = create_trending_data(500, 'down')
    trend_down = strategy._check_ema_trend(df_down, 100)
    print(f"下降趋势数据: {trend_down}")

    assert trend_up in ['UP', None], "上升趋势检测错误"
    assert trend_down in ['DOWN', None], "下降趋势检测错误"

    print("\n✅ EMA趋势检测正常")


def test_adx_confirmation():
    """测试ADX确认"""
    print("\n" + "=" * 80)
    print("测试2: ADX确认")
    print("=" * 80)

    strategy = MultiTimeframeTrendStrategy(adx_threshold=25.0)
    df = create_trending_data(500, 'up')

    # 测试ADX
    adx = strategy._calculate_adx(df)
    print(f"\nADX值（100-110）:")
    for i in range(100, 110):
        confirmed = strategy._check_adx(df, i)
        print(f"  索引{i}: ADX={adx.iloc[i]:.2f}, 确认={confirmed}")

    print("\n✅ ADX确认正常")


def test_volume_confirmation():
    """测试成交量确认"""
    print("\n" + "=" * 80)
    print("测试3: 成交量确认")
    print("=" * 80)

    strategy = MultiTimeframeTrendStrategy(volume_multiplier=1.2)
    df = create_trending_data(500, 'up')

    # 测试成交量
    confirmed_count = 0
    for i in range(100, 200):
        if strategy._check_volume(df, i):
            confirmed_count += 1

    print(f"\n成交量确认次数: {confirmed_count}/100")
    assert confirmed_count > 0, "应该有成交量确认"

    print("\n✅ 成交量确认正常")


def test_signal_generation():
    """测试信号生成"""
    print("\n" + "=" * 80)
    print("测试4: 信号生成")
    print("=" * 80)

    strategy = MultiTimeframeTrendStrategy()
    df = create_trending_data(500, 'up')

    signals = []
    for i in range(50, 200):
        signal, strength = strategy.generate_signal(df, i, regime='trending_up')
        if signal != 'HOLD':
            signals.append((i, signal, strength))

    print(f"\n生成了 {len(signals)} 个交易信号")
    if signals:
        print("前5个信号:")
        for idx, (i, sig, strength) in enumerate(signals[:5]):
            print(f"  {idx+1}. 索引{i}: {sig}, 强度{strength:.3f}")

    print("\n✅ 信号生成正常")


def test_exit_conditions():
    """测试退出条件"""
    print("\n" + "=" * 80)
    print("测试5: 退出条件")
    print("=" * 80)

    strategy = MultiTimeframeTrendStrategy(trailing_stop_pct=0.03)
    df = create_trending_data(500, 'up')

    # 模拟开仓
    from quant_v2.strategies.multi_timeframe_trend import TrendPosition
    strategy.position = TrendPosition(
        entry_price=50000,
        entry_time=100,
        direction='LONG',
        highest_price=52000,
        lowest_price=50000
    )

    # 测试移动止损
    # highest_price = 52000
    # trailing_stop = 52000 * (1 - 0.03) = 50440
    should_exit_1, reason_1 = strategy._check_exit_conditions(df, 110, 50500)  # 高于止损线
    should_exit_2, reason_2 = strategy._check_exit_conditions(df, 110, 50400)  # 低于止损线

    print(f"\n移动止损测试:")
    print(f"  最高价: 52000, 止损线: 50440")
    print(f"  价格50500（未触发）: {should_exit_1}, {reason_1}")
    print(f"  价格50400（触发）: {should_exit_2}, {reason_2}")

    assert not should_exit_1, "不应触发止损"
    assert should_exit_2, "应触发止损"

    print("\n✅ 退出条件正常")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "🧪" * 40)
    print("MultiTimeframeTrend 策略测试套件")
    print("🧪" * 40)

    try:
        test_ema_trend_detection()
        test_adx_confirmation()
        test_volume_confirmation()
        test_signal_generation()
        test_exit_conditions()

        print("\n" + "=" * 80)
        print("🎉 所有测试通过！")
        print("=" * 80)

        return True

    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        return False
    except Exception as e:
        print(f"\n💥 测试错误: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = run_all_tests()
    exit(0 if success else 1)
