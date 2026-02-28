"""
测试v3自适应系统的完整表现（2023-2026）
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from data.fetcher import BinanceFetcher
from quant_v3.engine.adaptive_engine import AdaptiveEngine
import pandas as pd


def test_v3_system():
    print("\n" + "="*80)
    print("v3 自适应系统 - 完整回测（2023-2026）")
    print("="*80)

    # 加载数据
    fetcher = BinanceFetcher()
    df = fetcher.fetch_history('BTC-USDT', '1h', days=1095)

    print(f"\n数据: {len(df)}条")
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
    print(f"时间: {df['datetime'].iloc[0]} 至 {df['datetime'].iloc[-1]}")
    print(f"价格: {df['close'].iloc[0]:,.2f} → {df['close'].iloc[-1]:,.2f}")

    # 市场表现
    market_return = (df['close'].iloc[-1] / df['close'].iloc[0] - 1) * 100
    print(f"市场涨幅: {market_return:+.2f}%")

    # 运行v3系统
    print(f"\n{'='*80}")
    print("v3系统回测")
    print(f"{'='*80}")

    engine = AdaptiveEngine(initial_capital=10000)
    results = engine.backtest(df)

    # 结果
    print(f"\n资金:")
    print(f"  初始: {results['initial_capital']:,.2f} USDT")
    print(f"  最终: {results['final_capital']:,.2f} USDT")
    print(f"  收益: {results['total_return']*100:+.2f}%")
    print(f"  交易数: {results['total_trades']}")

    # 市场状态分布
    print(f"\n市场状态分布:")
    total_bars = len(results['market_states'])
    for state, count in results['state_distribution'].items():
        pct = count / total_bars * 100
        print(f"  {state}: {count} ({pct:.1f}%)")

    # 交易记录
    print(f"\n前20笔交易:")
    print(f"{'时间':<20s} {'类型':<12s} {'价格':<12s} {'杠杆':<8s} {'市场':<10s} {'收益':<15s}")
    print("-" * 90)

    for i, trade in enumerate(results['trades'][:20]):
        ts = pd.to_datetime(trade['timestamp'], unit='ms').strftime('%Y-%m-%d %H:%M')
        trade_type = trade['type']
        price = trade['price']
        leverage = trade.get('leverage', 1.0)
        market = trade['market_state']
        pnl = trade.get('pnl', 0)

        if trade_type in ['BUY', 'SHORT']:
            print(f"{ts:<20s} {trade_type:<12s} {price:>11,.2f} {leverage:>7.1f}x {market:<10s} {'--':<15s}")
        else:
            print(f"{ts:<20s} {trade_type:<12s} {price:>11,.2f} {'--':<8s} {market:<10s} {pnl:>+14,.2f}")

    # 分时段分析
    print(f"\n{'='*80}")
    print("分时段分析")
    print(f"{'='*80}")

    periods = [
        ('2023-03-01', '2024-12-31', '牛市期'),
        ('2025-01-01', '2026-02-28', '熊市期'),
    ]

    for start_date, end_date, desc in periods:
        mask = (df['datetime'] >= start_date) & (df['datetime'] <= end_date)
        period_df = df[mask].copy()

        if len(period_df) == 0:
            continue

        # 运行该时段的回测
        period_engine = AdaptiveEngine(initial_capital=10000)
        period_results = period_engine.backtest(period_df)

        period_market_return = (period_df['close'].iloc[-1] / period_df['close'].iloc[0] - 1) * 100

        print(f"\n{desc} ({start_date} ~ {end_date}):")
        print(f"  BTC涨幅: {period_market_return:+.2f}%")
        print(f"  v3收益: {period_results['total_return']*100:+.2f}%")
        print(f"  交易数: {period_results['total_trades']}")

        # 市场状态
        state_dist = period_results['state_distribution']
        total = sum(state_dist.values())
        print(f"  市场状态: ", end='')
        for state, count in state_dist.items():
            print(f"{state}:{count/total*100:.0f}% ", end='')
        print()

        # 判断是否达标
        if '牛市期' in desc:
            if period_results['total_return'] >= 4.0:
                print(f"  ✅ 达标（目标400%）")
            else:
                print(f"  ❌ 未达标（目标400%，差{400 - period_results['total_return']*100:.1f}%）")
        else:  # 熊市期
            if period_results['total_return'] >= 0.70:
                print(f"  ✅ 达标（目标70%）")
            else:
                print(f"  ❌ 未达标（目标70%，差{70 - period_results['total_return']*100:.1f}%）")

    # 对比v2
    print(f"\n{'='*80}")
    print("v2 vs v3 对比")
    print(f"{'='*80}")

    print(f"\nv2最佳（StatisticalArbitrage）: +49.05%")
    print(f"v3自适应系统: {results['total_return']*100:+.2f}%")
    print(f"提升: {results['total_return']*100 - 49.05:+.2f}%")

    if results['total_return'] >= 6.0:
        print(f"\n🎉 v3系统达到预期目标（680%+）！")
    elif results['total_return'] >= 2.0:
        print(f"\n👍 v3系统表现良好（200%+），但未达到最优目标")
    else:
        print(f"\n⚠️  v3系统需要优化，当前表现未达预期")


if __name__ == '__main__':
    test_v3_system()
