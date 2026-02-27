"""
回测引擎端到端测试

测试完整的回测流程
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../'))

import pandas as pd
import numpy as np
from quant_v2.backtest.backtest_engine import BacktestEngine
from quant_v2.strategies.enhanced_grid import EnhancedGridStrategy


def create_test_data(length: int = 500) -> pd.DataFrame:
    """创建测试数据"""
    np.random.seed(42)
    base_price = 50000

    # 创建震荡+趋势混合数据
    # 前250: 震荡市
    prices_1 = base_price + 2000 * np.sin(np.linspace(0, 6 * np.pi, 250))
    prices_1 += np.random.randn(250) * 200

    # 后250: 上升趋势
    trend = np.linspace(0, 0.3, 250)
    prices_2 = base_price * np.exp(trend) + np.random.randn(250) * 200

    prices = np.concatenate([prices_1, prices_2])

    df = pd.DataFrame({
        'timestamp': pd.date_range('2023-01-01', periods=length, freq='1h'),
        'open': prices * (1 + np.random.randn(length) * 0.002),
        'high': prices * (1 + abs(np.random.randn(length)) * 0.005),
        'low': prices * (1 - abs(np.random.randn(length)) * 0.005),
        'close': prices,
        'volume': np.random.randint(1000, 10000, length),
    })

    return df


def test_basic_backtest():
    """测试基本回测功能"""
    print("=" * 80)
    print("测试1: 基本回测流程")
    print("=" * 80)

    # 创建测试数据
    df = create_test_data(500)
    print(f"\n数据范围: {df['timestamp'].iloc[0]} 至 {df['timestamp'].iloc[-1]}")
    print(f"价格范围: {df['close'].min():.2f} - {df['close'].max():.2f}")

    # 创建回测引擎
    engine = BacktestEngine(initial_capital=10000)

    # 创建策略
    strategy = EnhancedGridStrategy(
        base_spacing=0.02,
        levels=10,
        trend_filter=True
    )

    # 运行回测
    result = engine.run(df, strategy, strategy_name="EnhancedGrid")

    # 验证结果
    print(f"\n回测结果验证:")
    assert result.initial_capital == 10000, "初始资金错误"
    assert result.final_capital > 0, "最终资金应大于0"
    assert len(result.equity_curve) == len(df), "权益曲线长度错误"
    print(f"  ✓ 初始资金: {result.initial_capital:,.2f}")
    print(f"  ✓ 最终资金: {result.final_capital:,.2f}")
    print(f"  ✓ 总收益率: {result.total_return*100:+.2f}%")
    print(f"  ✓ 交易次数: {result.total_trades}")

    print("\n✅ 基本回测流程正常")
    return result


def test_performance_metrics():
    """测试性能指标计算"""
    print("\n" + "=" * 80)
    print("测试2: 性能指标")
    print("=" * 80)

    df = create_test_data(500)
    engine = BacktestEngine(initial_capital=10000)
    strategy = EnhancedGridStrategy()

    result = engine.run(df, strategy, strategy_name="EnhancedGrid")

    print(f"\n性能指标:")
    print(f"  总收益率: {result.total_return*100:+.2f}%")
    print(f"  年化收益: {result.annualized_return*100:+.2f}%")
    print(f"  最大回撤: {result.max_drawdown*100:.2f}%")
    print(f"  夏普比率: {result.sharpe_ratio:.2f}")
    print(f"  胜率: {result.win_rate*100:.1f}%")

    # 验证指标范围合理性
    assert -1 <= result.total_return <= 10, "收益率异常"
    assert 0 <= result.max_drawdown <= 1, "回撤范围异常"
    assert 0 <= result.win_rate <= 1, "胜率范围异常"

    print("\n✅ 性能指标正常")


def test_trade_execution():
    """测试交易执行"""
    print("\n" + "=" * 80)
    print("测试3: 交易执行")
    print("=" * 80)

    df = create_test_data(500)
    engine = BacktestEngine(initial_capital=10000, fee_rate=0.0004)
    strategy = EnhancedGridStrategy()

    result = engine.run(df, strategy, strategy_name="EnhancedGrid")

    if result.total_trades > 0:
        print(f"\n交易统计:")
        print(f"  总交易次数: {result.total_trades}")
        print(f"  盈利交易: {result.winning_trades}")
        print(f"  亏损交易: {result.losing_trades}")
        print(f"  总手续费: {result.total_fees:.2f} USDT")

        # 查看前几笔交易
        print(f"\n前5笔交易:")
        for i, trade in enumerate(result.trades[:5]):
            print(f"  {i+1}. {trade.action} {trade.size:.6f} @ {trade.price:.2f}, PnL: {trade.pnl:+.2f}")

        # 验证交易逻辑
        assert result.winning_trades + result.losing_trades <= result.total_trades
        assert result.total_fees > 0, "应产生手续费"

    print("\n✅ 交易执行正常")


def test_risk_controls():
    """测试风控系统"""
    print("\n" + "=" * 80)
    print("测试4: 风控系统")
    print("=" * 80)

    df = create_test_data(500)
    engine = BacktestEngine(initial_capital=10000)

    # 设置严格风控
    engine.account_risk.max_drawdown_limit = 0.10  # 10%回撤限制
    engine.strategy_risk.max_consecutive_losses = 2

    strategy = EnhancedGridStrategy()
    result = engine.run(df, strategy, strategy_name="EnhancedGrid")

    print(f"\n风控验证:")
    print(f"  最大回撤: {result.max_drawdown*100:.2f}% (限制: 10%)")
    print(f"  是否触发风控: {'是' if result.max_drawdown > 0.10 else '否'}")

    # 回撤应在可控范围内（可能因风控提前平仓而小于限制）
    assert result.max_drawdown < 0.50, "回撤过大，风控失效"

    print("\n✅ 风控系统正常")


def test_equity_curve():
    """测试权益曲线"""
    print("\n" + "=" * 80)
    print("测试5: 权益曲线")
    print("=" * 80)

    df = create_test_data(500)
    engine = BacktestEngine(initial_capital=10000)
    strategy = EnhancedGridStrategy()

    result = engine.run(df, strategy, strategy_name="EnhancedGrid")

    print(f"\n权益曲线分析:")
    equity_series = pd.Series(result.equity_curve)
    print(f"  起始权益: {equity_series.iloc[0]:,.2f}")
    print(f"  最终权益: {equity_series.iloc[-1]:,.2f}")
    print(f"  最高权益: {equity_series.max():,.2f}")
    print(f"  最低权益: {equity_series.min():,.2f}")

    # 验证权益曲线连续性
    assert len(equity_series) == len(df), "权益曲线长度应等于数据长度"
    assert equity_series.iloc[0] == 10000, "起始权益应等于初始资金"

    print("\n✅ 权益曲线正常")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "🧪" * 40)
    print("BacktestEngine 端到端测试套件")
    print("🧪" * 40)

    try:
        test_basic_backtest()
        test_performance_metrics()
        test_trade_execution()
        test_risk_controls()
        test_equity_curve()

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
