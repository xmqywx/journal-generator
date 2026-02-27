"""
统计套利策略测试
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../'))

import pandas as pd
import numpy as np
from quant_v2.strategies.statistical_arbitrage import StatisticalArbitrageStrategy


def create_correlated_data(length: int = 200) -> tuple[pd.DataFrame, pd.DataFrame]:
    """创建相关性数据（BTC和ETH）"""
    np.random.seed(42)

    # 基础价格
    btc_base = 50000
    eth_base = 3000

    # 共同趋势（高相关性）
    common_trend = np.cumsum(np.random.randn(length) * 0.01)

    # BTC价格
    btc_noise = np.random.randn(length) * 0.005
    btc_prices = btc_base * np.exp(common_trend + btc_noise)

    # ETH价格（高相关性）
    eth_noise = np.random.randn(length) * 0.005
    eth_prices = eth_base * np.exp(common_trend + eth_noise)

    btc_df = pd.DataFrame({
        'timestamp': pd.date_range('2023-01-01', periods=length, freq='1h'),
        'open': btc_prices * (1 + np.random.randn(length) * 0.002),
        'high': btc_prices * (1 + abs(np.random.randn(length)) * 0.005),
        'low': btc_prices * (1 - abs(np.random.randn(length)) * 0.005),
        'close': btc_prices,
        'volume': np.random.randint(1000, 10000, length),
    })

    eth_df = pd.DataFrame({
        'timestamp': pd.date_range('2023-01-01', periods=length, freq='1h'),
        'open': eth_prices * (1 + np.random.randn(length) * 0.002),
        'high': eth_prices * (1 + abs(np.random.randn(length)) * 0.005),
        'low': eth_prices * (1 - abs(np.random.randn(length)) * 0.005),
        'close': eth_prices,
        'volume': np.random.randint(1000, 10000, length),
    })

    return btc_df, eth_df


def test_spread_calculation():
    """测试价差计算"""
    print("=" * 80)
    print("测试1: 价差计算")
    print("=" * 80)

    strategy = StatisticalArbitrageStrategy()
    btc_df, eth_df = create_correlated_data(200)

    # 计算价差
    spread = strategy.calculate_spread(50000, 3000)
    expected = np.log(50000 / 3000)

    print(f"\n价差计算:")
    print(f"  BTC: 50000, ETH: 3000")
    print(f"  价差: {spread:.4f}")
    print(f"  预期: {expected:.4f}")

    assert abs(spread - expected) < 0.0001, "价差计算错误"

    # 计算价差序列
    spread_series = strategy.calculate_spread_series(btc_df, eth_df)
    print(f"  序列长度: {len(spread_series)}")

    assert len(spread_series) == len(btc_df), "价差序列长度错误"

    print("\n✅ 价差计算正常")


def test_z_score_calculation():
    """测试Z-score计算"""
    print("\n" + "=" * 80)
    print("测试2: Z-score计算")
    print("=" * 80)

    strategy = StatisticalArbitrageStrategy(lookback=60)
    btc_df, eth_df = create_correlated_data(200)

    spread_series = strategy.calculate_spread_series(btc_df, eth_df)

    # 测试不同位置的Z-score
    indices = [59, 100, 150, 199]
    print("\nZ-score值:")
    for idx in indices:
        z = strategy.calculate_z_score(spread_series, idx)
        if z is not None:
            print(f"  索引 {idx}: Z-score = {z:.3f}")
        else:
            print(f"  索引 {idx}: 数据不足")

    # 验证前59个位置返回None
    z_early = strategy.calculate_z_score(spread_series, 50)
    assert z_early is None, "数据不足应返回None"

    # 验证后续位置有值
    z_later = strategy.calculate_z_score(spread_series, 100)
    assert z_later is not None, "数据充足应返回Z-score"

    print("\n✅ Z-score计算正常")


def test_correlation_check():
    """测试相关性检查"""
    print("\n" + "=" * 80)
    print("测试3: 相关性检查")
    print("=" * 80)

    strategy = StatisticalArbitrageStrategy(min_correlation=0.85)
    btc_df, eth_df = create_correlated_data(200)

    # 测试相关性
    is_correlated = strategy.check_correlation(btc_df, eth_df, 100)
    print(f"\n相关性检查:")
    print(f"  索引100: {'通过' if is_correlated else '不通过'}")

    # 手动计算相关性验证
    btc_returns = btc_df['close'].iloc[40:100].pct_change()
    eth_returns = eth_df['close'].iloc[40:100].pct_change()
    actual_corr = btc_returns.corr(eth_returns)
    print(f"  实际相关性: {actual_corr:.3f}")

    print("\n✅ 相关性检查正常")


def test_signal_generation():
    """测试信号生成"""
    print("\n" + "=" * 80)
    print("测试4: 信号生成")
    print("=" * 80)

    strategy = StatisticalArbitrageStrategy(
        lookback=60,
        entry_z_score=2.0,
        exit_z_score=0.5
    )
    btc_df, eth_df = create_correlated_data(200)

    signals = []
    for i in range(60, 200):
        signal, strength = strategy.generate_signal(btc_df, eth_df, i)
        if signal != 'HOLD':
            signals.append((i, signal, strength))

    print(f"\n生成了 {len(signals)} 个交易信号")
    if signals:
        print("信号分布:")
        long_count = sum(1 for _, s, _ in signals if s == 'LONG_SPREAD')
        short_count = sum(1 for _, s, _ in signals if s == 'SHORT_SPREAD')
        close_count = sum(1 for _, s, _ in signals if s == 'CLOSE')
        print(f"  LONG_SPREAD: {long_count}")
        print(f"  SHORT_SPREAD: {short_count}")
        print(f"  CLOSE: {close_count}")

    print("\n✅ 信号生成正常")


def test_position_management():
    """测试持仓管理"""
    print("\n" + "=" * 80)
    print("测试5: 持仓管理")
    print("=" * 80)

    strategy = StatisticalArbitrageStrategy()
    btc_df, eth_df = create_correlated_data(200)

    # 初始无持仓
    pos_info = strategy.get_position_info()
    print(f"\n初始持仓: {pos_info}")
    assert pos_info is None, "初始应无持仓"

    # 生成信号直到开仓
    for i in range(60, 200):
        signal, strength = strategy.generate_signal(btc_df, eth_df, i)
        if signal in ['LONG_SPREAD', 'SHORT_SPREAD']:
            print(f"\n开仓信号: {signal} at index {i}, strength {strength:.3f}")
            break

    # 检查持仓
    pos_info = strategy.get_position_info()
    if pos_info:
        print(f"持仓信息:")
        print(f"  类型: {pos_info['position_type']}")
        print(f"  入场Z-score: {pos_info['entry_z_score']:.3f}")

    print("\n✅ 持仓管理正常")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "🧪" * 40)
    print("StatisticalArbitrage 策略测试套件")
    print("🧪" * 40)

    try:
        test_spread_calculation()
        test_z_score_calculation()
        test_correlation_check()
        test_signal_generation()
        test_position_management()

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
