"""
增强网格策略测试
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../'))

import pandas as pd
import numpy as np
from quant_v2.strategies.enhanced_grid import EnhancedGridStrategy


def create_ranging_data(length: int = 200) -> pd.DataFrame:
    """创建震荡数据"""
    np.random.seed(42)
    base_price = 50000

    # 在48000-52000之间震荡
    prices = base_price + 2000 * np.sin(np.linspace(0, 4 * np.pi, length))
    prices += np.random.randn(length) * 200

    df = pd.DataFrame({
        'timestamp': pd.date_range('2023-01-01', periods=length, freq='1h'),
        'open': prices * (1 + np.random.randn(length) * 0.002),
        'high': prices * (1 + abs(np.random.randn(length)) * 0.005),
        'low': prices * (1 - abs(np.random.randn(length)) * 0.005),
        'close': prices,
        'volume': np.random.randint(1000, 10000, length),
    })

    return df


def test_basic_functionality():
    """测试基本功能"""
    print("=" * 80)
    print("测试1: 基本功能")
    print("=" * 80)

    strategy = EnhancedGridStrategy()
    df = create_ranging_data(200)

    # 测试网格激活条件
    should_activate = strategy.should_activate_grid(df, 100, 'ranging')
    print(f"\n震荡市场应激活网格: {should_activate}")
    assert should_activate, "震荡市应激活网格"

    should_activate_trend = strategy.should_activate_grid(df, 100, 'trending_up')
    print(f"趋势市场不应激活网格: {not should_activate_trend}")
    assert not should_activate_trend, "趋势市不应激活网格"

    print("\n✅ 基本功能正常")


def test_grid_initialization():
    """测试网格初始化"""
    print("\n" + "=" * 80)
    print("测试2: 网格初始化")
    print("=" * 80)

    strategy = EnhancedGridStrategy(levels=10)
    df = create_ranging_data(200)

    # 初始化网格
    strategy.initialize_grid(df, 100, account_equity=10000)

    stats = strategy.get_statistics()
    print(f"\n网格状态:")
    print(f"  激活状态: {stats['is_active']}")
    print(f"  中心价格: {stats['center_price']:.2f}")
    print(f"  网格层数: {stats['levels']}")
    print(f"  已成交层数: {stats['filled_levels']}")

    assert stats['is_active'], "网格应处于激活状态"
    assert stats['levels'] == 10, "应有10层网格"
    assert stats['filled_levels'] == 0, "初始无成交"

    print("\n✅ 网格初始化正常")


def test_signal_generation():
    """测试信号生成"""
    print("\n" + "=" * 80)
    print("测试3: 信号生成")
    print("=" * 80)

    strategy = EnhancedGridStrategy()
    df = create_ranging_data(200)

    signals = []
    for i in range(50, 200):
        signal, size = strategy.generate_signal(
            df, i, 'ranging', account_equity=10000, current_position=0.0
        )
        if signal != 'HOLD':
            signals.append((i, signal, size))

    print(f"\n生成了 {len(signals)} 个交易信号")
    print("前5个信号:")
    for i, (idx, sig, sz) in enumerate(signals[:5]):
        print(f"  {i+1}. 索引{idx}: {sig}, 数量{sz:.6f}")

    assert len(signals) > 0, "应该生成交易信号"

    print("\n✅ 信号生成正常")


def test_stop_loss():
    """测试止损"""
    print("\n" + "=" * 80)
    print("测试4: 止损机制")
    print("=" * 80)

    strategy = EnhancedGridStrategy(max_drawdown=0.20)
    df = create_ranging_data(200)

    # 初始化网格
    strategy.initialize_grid(df, 100, account_equity=10000)
    strategy.entry_equity = 10000

    # 测试止损触发
    assert not strategy._should_stop_loss(9000), "10%亏损不应止损"
    assert strategy._should_stop_loss(7900), "21%亏损应触发止损"

    print("\n止损检查:")
    print("  10%亏损: 不触发 ✓")
    print("  21%亏损: 触发 ✓")

    print("\n✅ 止损机制正常")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "🧪" * 40)
    print("EnhancedGrid 策略测试套件")
    print("🧪" * 40)

    try:
        test_basic_functionality()
        test_grid_initialization()
        test_signal_generation()
        test_stop_loss()

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
