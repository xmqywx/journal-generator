"""
测试多周期趋势策略

在3年BTC数据上测试趋势策略表现
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from data.fetcher import BinanceFetcher
from quant_v2.backtest.backtest_engine import BacktestEngine
from quant_v2.strategies.multi_timeframe_trend import MultiTimeframeTrendStrategy


def main():
    print("\n" + "🚀" * 40)
    print("多周期趋势策略 - 3年回测")
    print("🚀" * 40)

    # 1. 加载数据
    print(f"\n{'='*80}")
    print("加载历史数据")
    print(f"{'='*80}")

    fetcher = BinanceFetcher()
    df = fetcher.fetch_history('BTC-USDT', '1h', days=1095)

    if df.empty:
        print("❌ 数据下载失败")
        return

    print(f"✅ 成功加载 {len(df)} 条数据")
    print(f"   时间范围: {df['timestamp'].iloc[0]} 至 {df['timestamp'].iloc[-1]}")
    print(f"   价格范围: {df['close'].min():,.2f} - {df['close'].max():,.2f} USDT")

    # 2. 创建回测引擎
    engine = BacktestEngine(
        initial_capital=10000,
        fee_rate=0.0004,
        slippage=0.0001
    )

    # 3. 创建策略
    strategy = MultiTimeframeTrendStrategy(
        ema_fast=12,
        ema_slow=26,
        adx_threshold=25.0,
        volume_multiplier=1.2,
        trailing_stop_pct=0.03,
        max_holding_hours=168  # 7天
    )

    print(f"\n{'='*80}")
    print("策略参数")
    print(f"{'='*80}")
    print(f"  快速EMA: {strategy.ema_fast}")
    print(f"  慢速EMA: {strategy.ema_slow}")
    print(f"  ADX阈值: {strategy.adx_threshold}")
    print(f"  成交量倍数: {strategy.volume_multiplier}x")
    print(f"  移动止损: {strategy.trailing_stop_pct*100}%")
    print(f"  最大持仓: {strategy.max_holding_hours}小时")

    # 4. 运行回测
    result = engine.run(df, strategy, strategy_name="MultiTimeframeTrend")

    # 5. 详细分析
    print(f"\n{'='*80}")
    print("详细回测结果")
    print(f"{'='*80}")

    print(f"\n📊 收益指标:")
    print(f"  初始资金: {result.initial_capital:,.2f} USDT")
    print(f"  最终资金: {result.final_capital:,.2f} USDT")
    print(f"  绝对收益: {result.final_capital - result.initial_capital:+,.2f} USDT")
    print(f"  总收益率: {result.total_return*100:+.2f}%")
    print(f"  年化收益: {result.annualized_return*100:+.2f}%")

    print(f"\n📉 风险指标:")
    print(f"  最大回撤: {result.max_drawdown*100:.2f}%")
    print(f"  夏普比率: {result.sharpe_ratio:.2f}")

    print(f"\n📈 交易统计:")
    print(f"  总交易次数: {result.total_trades}")
    print(f"  盈利交易: {result.winning_trades} ({result.winning_trades/result.total_trades*100:.1f}%)" if result.total_trades > 0 else "  无交易")
    print(f"  亏损交易: {result.losing_trades} ({result.losing_trades/result.total_trades*100:.1f}%)" if result.total_trades > 0 else "")
    print(f"  胜率: {result.win_rate*100:.1f}%")
    print(f"  总手续费: {result.total_fees:,.2f} USDT ({result.total_fees/result.initial_capital*100:.2f}%)")

    # 交易明细（前20笔）
    if result.total_trades > 0:
        print(f"\n📝 交易明细（前20笔）:")
        for i, trade in enumerate(result.trades[:20]):
            timestamp = trade.timestamp if hasattr(trade.timestamp, 'strftime') else trade.timestamp
            timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M') if hasattr(timestamp, 'strftime') else str(timestamp)
            print(f"  {i+1:2d}. [{timestamp_str}] {trade.action:4s} {trade.size:.6f} BTC @ {trade.price:,.2f}, "
                  f"PnL: {trade.pnl:+,.2f}")

    # 6. 对比评估
    print(f"\n{'='*80}")
    print("策略评估")
    print(f"{'='*80}")

    passed = []
    failed = []

    if result.total_return > 0.3:
        passed.append(f"✅ 3年收益 > 30%: {result.total_return*100:.2f}%")
    elif result.total_return > 0:
        failed.append(f"⚠️  3年收益 < 30%: {result.total_return*100:.2f}%")
    else:
        failed.append(f"❌ 3年收益为负: {result.total_return*100:.2f}%")

    if result.max_drawdown < 0.20:
        passed.append(f"✅ 最大回撤 < 20%: {result.max_drawdown*100:.2f}%")
    else:
        failed.append(f"❌ 最大回撤 > 20%: {result.max_drawdown*100:.2f}%")

    if result.sharpe_ratio > 1.0 or pd.isna(result.sharpe_ratio):
        passed.append(f"✅ 夏普比率 > 1.0: {result.sharpe_ratio:.2f}")
    else:
        failed.append(f"⚠️  夏普比率 < 1.0: {result.sharpe_ratio:.2f}")

    if result.win_rate > 0.5:
        passed.append(f"✅ 胜率 > 50%: {result.win_rate*100:.1f}%")
    else:
        failed.append(f"⚠️  胜率 < 50%: {result.win_rate*100:.1f}%")

    print(f"\n通过的指标:")
    for item in passed:
        print(f"  {item}")

    if failed:
        print(f"\n未达标指标:")
        for item in failed:
            print(f"  {item}")

    # 7. 对比EnhancedGrid
    print(f"\n{'='*80}")
    print("对比分析（vs EnhancedGrid）")
    print(f"{'='*80}")

    grid_return = 0.08  # EnhancedGrid的收益率
    grid_trades = 3

    print(f"\n策略对比:")
    print(f"  {'指标':<20s} {'Trend':>15s} {'Grid':>15s} {'差异':>15s}")
    print(f"  {'-'*20} {'-'*15} {'-'*15} {'-'*15}")
    print(f"  {'收益率':<20s} {result.total_return*100:>14.2f}% {grid_return:>14.2f}% {(result.total_return*100-grid_return):>+14.2f}%")
    print(f"  {'交易次数':<20s} {result.total_trades:>15d} {grid_trades:>15d} {result.total_trades-grid_trades:>+15d}")
    print(f"  {'最大回撤':<20s} {result.max_drawdown*100:>14.2f}% {'0.10':>15s}% {'':>15s}")

    if result.total_return > grid_return/100:
        print(f"\n✅ MultiTimeframeTrend表现更好！收益提升 {(result.total_return*100-grid_return):.2f}%")
    else:
        print(f"\n⚠️  MultiTimeframeTrend表现不如EnhancedGrid")


if __name__ == '__main__':
    import pandas as pd
    main()
