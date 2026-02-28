"""
测试更激进的MultiTimeframeTrend参数

目标：捕捉更多趋势，获得更高收益
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from data.fetcher import BinanceFetcher
from quant_v2.backtest.backtest_engine import BacktestEngine
from quant_v2.strategies.multi_timeframe_trend import MultiTimeframeTrendStrategy


def test_params(name, params):
    """测试指定参数"""
    print(f"\n{'='*80}")
    print(f"测试: {name}")
    print(f"{'='*80}")

    # 加载数据
    fetcher = BinanceFetcher()
    df = fetcher.fetch_history('BTC-USDT', '1h', days=1095)

    # 创建策略
    strategy = MultiTimeframeTrendStrategy(**params)

    # 回测
    engine = BacktestEngine(
        initial_capital=10000,
        fee_rate=0.0004,
        slippage=0.0001
    )

    result = engine.run(df, strategy, strategy_name=name)

    # 简要结果
    print(f"\n结果:")
    print(f"  收益率: {result.total_return*100:+.2f}%")
    print(f"  年化: {result.annualized_return*100:+.2f}%")
    print(f"  交易数: {result.total_trades}")
    print(f"  胜率: {result.win_rate*100:.1f}%")
    print(f"  最大回撤: {result.max_drawdown*100:.2f}%")
    print(f"  夏普比率: {result.sharpe_ratio:.2f}")

    return result


def main():
    print("\n" + "🚀" * 40)
    print("MultiTimeframeTrend 参数优化测试")
    print("🚀" * 40)

    # 1. 原始参数（基准）
    result_original = test_params(
        "原始参数",
        {
            'ema_fast': 12,
            'ema_slow': 26,
            'adx_threshold': 25.0,
            'volume_multiplier': 1.2,
            'trailing_stop_pct': 0.03,
            'max_holding_hours': 168
        }
    )

    # 2. 放宽止损
    result_wide_stop = test_params(
        "放宽止损（3% → 10%）",
        {
            'ema_fast': 12,
            'ema_slow': 26,
            'adx_threshold': 25.0,
            'volume_multiplier': 1.2,
            'trailing_stop_pct': 0.10,  # 放宽到10%
            'max_holding_hours': 168
        }
    )

    # 3. 降低入场条件
    result_easy_entry = test_params(
        "降低入场条件（ADX 25→20, Vol 1.2→1.05）",
        {
            'ema_fast': 12,
            'ema_slow': 26,
            'adx_threshold': 20.0,      # 降低ADX
            'volume_multiplier': 1.05,   # 降低成交量要求
            'trailing_stop_pct': 0.03,
            'max_holding_hours': 168
        }
    )

    # 4. 延长持仓时间
    result_long_hold = test_params(
        "延长持仓（7天 → 30天）",
        {
            'ema_fast': 12,
            'ema_slow': 26,
            'adx_threshold': 25.0,
            'volume_multiplier': 1.2,
            'trailing_stop_pct': 0.03,
            'max_holding_hours': 720     # 30天
        }
    )

    # 5. 综合优化
    result_optimized = test_params(
        "综合优化（止损10% + ADX 20 + Vol 1.05 + 30天）",
        {
            'ema_fast': 12,
            'ema_slow': 26,
            'adx_threshold': 20.0,
            'volume_multiplier': 1.05,
            'trailing_stop_pct': 0.10,
            'max_holding_hours': 720
        }
    )

    # 6. 激进版
    result_aggressive = test_params(
        "激进版（止损15% + ADX 15 + Vol 1.0 + 60天）",
        {
            'ema_fast': 12,
            'ema_slow': 26,
            'adx_threshold': 15.0,      # 很低的ADX
            'volume_multiplier': 1.0,    # 取消成交量过滤
            'trailing_stop_pct': 0.15,   # 15%止损
            'max_holding_hours': 1440    # 60天
        }
    )

    # 对比总结
    print("\n" + "="*80)
    print("参数对比总结")
    print("="*80)

    results = [
        ("原始参数", result_original),
        ("放宽止损", result_wide_stop),
        ("降低入场", result_easy_entry),
        ("延长持仓", result_long_hold),
        ("综合优化", result_optimized),
        ("激进版", result_aggressive)
    ]

    print(f"\n{'策略':<25s} {'收益率':<12s} {'年化':<12s} {'交易数':<10s} {'胜率':<12s} {'最大回撤':<12s}")
    print("-" * 90)

    for name, result in results:
        print(f"{name:<25s} {result.total_return*100:>+10.2f}% {result.annualized_return*100:>+10.2f}% "
              f"{result.total_trades:>9d} {result.win_rate*100:>10.1f}% {result.max_drawdown*100:>10.2f}%")

    # 找出最佳策略
    best = max(results, key=lambda x: x[1].total_return)
    print(f"\n🏆 收益最高: {best[0]}")
    print(f"   3年收益: {best[1].total_return*100:+.2f}%")
    print(f"   年化收益: {best[1].annualized_return*100:+.2f}%")
    print(f"   交易次数: {best[1].total_trades}")
    print(f"   胜率: {best[1].win_rate*100:.1f}%")

    # 检查是否达标
    if best[1].total_return >= 1.50:  # 150%
        print(f"\n✅ 达到目标！3年收益≥150%")
    else:
        print(f"\n⚠️  未达目标（3年收益<150%），需要进一步优化")
        shortfall = 1.50 - best[1].total_return
        print(f"   差距: {shortfall*100:.2f}%")


if __name__ == '__main__':
    main()
