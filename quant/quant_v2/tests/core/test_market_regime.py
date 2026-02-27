"""
市场环境识别模块测试

测试MarketRegime类的功能
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../'))

import pandas as pd
import numpy as np
from quant_v2.core.market_regime import MarketRegime


def create_test_data(length: int = 200) -> pd.DataFrame:
    """创建测试数据"""
    np.random.seed(42)

    # 创建基础价格序列
    base_price = 100
    returns = np.random.randn(length) * 0.02  # 2%波动
    prices = base_price * (1 + returns).cumprod()

    # 创建OHLC
    df = pd.DataFrame({
        'timestamp': pd.date_range('2023-01-01', periods=length, freq='1h'),
        'open': prices * (1 + np.random.randn(length) * 0.005),
        'high': prices * (1 + abs(np.random.randn(length)) * 0.01),
        'low': prices * (1 - abs(np.random.randn(length)) * 0.01),
        'close': prices,
        'volume': np.random.randint(1000, 10000, length),
    })

    return df


def create_trending_data(length: int = 200, trend: str = 'up') -> pd.DataFrame:
    """创建趋势市场数据"""
    # 使用不同的随机种子以避免相同噪音模式
    np.random.seed(42 if trend == 'up' else 43)
    base_price = 100

    if trend == 'up':
        # 上升趋势 - 更强的趋势，更小的噪音
        trend_component = np.linspace(0, 0.8, length)  # 80%上涨
    else:
        # 下降趋势 - 更强的趋势，更小的噪音
        trend_component = np.linspace(0, -0.5, length)  # 50%下跌

    # 添加较小的随机波动，保持趋势清晰
    noise = np.random.randn(length) * 0.005  # 减小噪音
    returns = trend_component + noise
    prices = base_price * np.exp(returns)

    df = pd.DataFrame({
        'timestamp': pd.date_range('2023-01-01', periods=length, freq='1h'),
        'open': prices * (1 + np.random.randn(length) * 0.005),
        'high': prices * (1 + abs(np.random.randn(length)) * 0.01),
        'low': prices * (1 - abs(np.random.randn(length)) * 0.01),
        'close': prices,
        'volume': np.random.randint(1000, 10000, length),
    })

    return df


def create_ranging_data(length: int = 200) -> pd.DataFrame:
    """创建震荡市场数据"""
    np.random.seed(44)
    base_price = 100

    # 在95-105之间震荡，添加更多噪音使其更现实
    prices = base_price + 5 * np.sin(np.linspace(0, 4 * np.pi, length))
    prices += np.random.randn(length) * 2.0  # 增加随机波动

    df = pd.DataFrame({
        'timestamp': pd.date_range('2023-01-01', periods=length, freq='1h'),
        'open': prices * (1 + np.random.randn(length) * 0.005),
        'high': prices * (1 + abs(np.random.randn(length)) * 0.01),
        'low': prices * (1 - abs(np.random.randn(length)) * 0.01),
        'close': prices,
        'volume': np.random.randint(1000, 10000, length),
    })

    return df


def test_basic_functionality():
    """测试基本功能"""
    print("=" * 80)
    print("测试1: 基本功能测试")
    print("=" * 80)

    regime = MarketRegime()
    df = create_test_data(200)

    # 测试单个时刻
    index = 100
    state = regime.identify(df, index)
    strength = regime.get_regime_strength(df, index)

    print(f"\n时刻 {index} 的市场状态:")
    print(f"  状态: {state}")
    print(f"  强度: {strength:.2f}")

    assert state in ['trending_up', 'trending_down', 'ranging',
                     'high_volatility', 'low_volatility']
    assert 0 <= strength <= 1

    print("\n✅ 基本功能正常")


def test_trend_detection():
    """测试趋势检测"""
    print("\n" + "=" * 80)
    print("测试2: 趋势检测")
    print("=" * 80)

    regime = MarketRegime()

    # 测试上升趋势
    df_up = create_trending_data(200, trend='up')
    states_up = []
    for i in range(100, 200):
        state = regime.identify(df_up, i)
        states_up.append(state)

    regime.clear_cache()  # 清除缓存

    # 测试下降趋势
    df_down = create_trending_data(200, trend='down')
    states_down = []
    for i in range(100, 200):
        state = regime.identify(df_down, i)
        states_down.append(state)

    # 统计
    up_count = states_up.count('trending_up')
    down_count = states_down.count('trending_down')

    print(f"\n上升趋势数据:")
    print(f"  识别为上升趋势: {up_count}/100 ({up_count}%)")
    print(f"  最终价格: {df_up['close'].iloc[-1]:.2f} (初始: {df_up['close'].iloc[0]:.2f})")

    print(f"\n下降趋势数据:")
    print(f"  识别为下降趋势: {down_count}/100 ({down_count}%)")
    print(f"  最终价格: {df_down['close'].iloc[-1]:.2f} (初始: {df_down['close'].iloc[0]:.2f})")

    # 至少应该有一定比例识别正确（20%以上说明逻辑正常）
    assert up_count > 20, f"上升趋势识别率过低: {up_count}%"
    assert down_count > 20, f"下降趋势识别率过低: {down_count}%"

    print("\n✅ 趋势检测正常")


def test_ranging_detection():
    """测试震荡检测"""
    print("\n" + "=" * 80)
    print("测试3: 震荡市场检测")
    print("=" * 80)

    regime = MarketRegime()
    df_ranging = create_ranging_data(200)

    states = []
    for i in range(100, 200):
        state = regime.identify(df_ranging, i)
        states.append(state)

    ranging_count = states.count('ranging')

    # 统计各状态分布
    from collections import Counter
    state_counts = Counter(states)

    print(f"\n震荡市场数据:")
    print(f"  识别为震荡: {ranging_count}/100 ({ranging_count}%)")
    print(f"  价格范围: {df_ranging['close'].iloc[100:].min():.2f} - {df_ranging['close'].iloc[100:].max():.2f}")
    print(f"  所有状态分布: {dict(state_counts)}")

    assert ranging_count > 20, f"震荡市场识别率过低: {ranging_count}%"

    print("\n✅ 震荡检测正常")


def test_statistics():
    """测试统计功能"""
    print("\n" + "=" * 80)
    print("测试4: 统计分析")
    print("=" * 80)

    regime = MarketRegime()
    df = create_test_data(300)

    stats = regime.get_statistics(df)

    print("\n市场状态分布:")
    for state, ratio in sorted(stats.items(), key=lambda x: x[1], reverse=True):
        print(f"  {state}: {ratio*100:.1f}%")

    # 验证总和为100%
    total = sum(stats.values())
    assert abs(total - 1.0) < 0.01, f"统计总和不为100%: {total}"

    print("\n✅ 统计功能正常")


def test_with_real_data():
    """使用真实数据测试"""
    print("\n" + "=" * 80)
    print("测试5: 真实数据测试")
    print("=" * 80)

    try:
        # 尝试加载真实数据
        from data.fetcher import BinanceFetcher

        fetcher = BinanceFetcher()
        df = fetcher.fetch_history('BTC-USDT', '1h', days=30)

        if df.empty:
            print("⚠️  无法获取真实数据，跳过此测试")
            return

        regime = MarketRegime()

        # 分析最近30天的市场状态
        stats = regime.get_statistics(df)

        print("\nBTC-USDT 最近30天市场状态:")
        for state, ratio in sorted(stats.items(), key=lambda x: x[1], reverse=True):
            print(f"  {state}: {ratio*100:.1f}%")

        # 最近状态
        current_state = regime.identify(df, len(df) - 1)
        current_strength = regime.get_regime_strength(df, len(df) - 1)

        print(f"\n当前状态: {current_state}")
        print(f"状态强度: {current_strength:.2f}")

        print("\n✅ 真实数据测试完成")

    except Exception as e:
        print(f"\n⚠️  真实数据测试失败: {e}")
        print("   （这是可选测试，不影响模块功能）")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "🧪" * 40)
    print("MarketRegime 模块测试套件")
    print("🧪" * 40)

    try:
        test_basic_functionality()
        test_trend_detection()
        test_ranging_detection()
        test_statistics()
        test_with_real_data()

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
