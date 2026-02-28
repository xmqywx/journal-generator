"""
诊断MultiTimeframeTrend收益低的根本原因
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from data.fetcher import BinanceFetcher
from quant_v2.backtest.backtest_engine import BacktestEngine
from quant_v2.strategies.multi_timeframe_trend import MultiTimeframeTrendStrategy
import pandas as pd


def diagnose():
    print("\n" + "="*80)
    print("MultiTimeframeTrend 收益低问题诊断")
    print("="*80)

    # 1. 加载数据
    print("\n加载数据...")
    fetcher = BinanceFetcher()
    df = fetcher.fetch_history('BTC-USDT', '1h', days=1095)

    print(f"✅ {len(df)} 条数据")
    print(f"   BTC价格: {df['close'].iloc[0]:.2f} → {df['close'].iloc[-1]:.2f}")
    print(f"   涨幅: {(df['close'].iloc[-1] / df['close'].iloc[0] - 1) * 100:.2f}%")

    # 2. 创建回测引擎
    engine = BacktestEngine(
        initial_capital=10000,
        fee_rate=0.0004,
        slippage=0.0001
    )

    # 3. 运行回测
    strategy = MultiTimeframeTrendStrategy(
        ema_fast=12,
        ema_slow=26,
        adx_threshold=25.0,
        volume_multiplier=1.2,
        trailing_stop_pct=0.03,
        max_holding_hours=168
    )

    result = engine.run(df, strategy, strategy_name="MultiTimeframeTrend")

    # 4. 详细分析每笔交易
    print("\n" + "="*80)
    print("交易明细分析")
    print("="*80)

    trades = result.trades
    print(f"\n总交易数: {len(trades)}")

    # 按买入/卖出分组
    buys = [t for t in trades if t.action == 'BUY']
    sells = [t for t in trades if t.action == 'SELL']

    print(f"BUY交易: {len(buys)}")
    print(f"SELL交易: {len(sells)}")

    # 配对分析
    print("\n" + "-"*100)
    print(f"{'序号':<4s} {'买入时间':<20s} {'买入价':<12s} {'买入量':<12s} "
          f"{'卖出时间':<20s} {'卖出价':<12s} {'盈亏':<12s} {'收益率':<10s}")
    print("-"*100)

    total_invested = 0
    total_return = 0

    for i in range(len(buys)):
        buy = buys[i]
        sell = sells[i] if i < len(sells) else None

        if sell:
            buy_time = pd.to_datetime(buy.timestamp, unit='ms') if isinstance(buy.timestamp, (int, float)) else buy.timestamp
            sell_time = pd.to_datetime(sell.timestamp, unit='ms') if isinstance(sell.timestamp, (int, float)) else sell.timestamp

            invested = buy.price * buy.size
            returned = sell.price * sell.size
            profit = sell.pnl
            profit_pct = (sell.price / buy.price - 1) * 100

            total_invested += invested
            total_return += returned

            print(f"{i+1:<4d} {str(buy_time):<20s} {buy.price:>11,.2f} {buy.size:>11.6f} "
                  f"{str(sell_time):<20s} {sell.price:>11,.2f} {profit:>+11.2f} {profit_pct:>+9.2f}%")

    # 5. 仓位分析
    print("\n" + "="*80)
    print("仓位分析")
    print("="*80)

    if len(buys) > 0:
        avg_investment = total_invested / len(buys)
        avg_position_pct = (avg_investment / result.initial_capital) * 100

        print(f"\n平均每笔投入: {avg_investment:,.2f} USDT")
        print(f"平均仓位比例: {avg_position_pct:.2f}%")
        print(f"初始资金: {result.initial_capital:,.2f} USDT")

        if avg_position_pct < 20:
            print(f"\n❌ 问题：仓位太小（{avg_position_pct:.2f}%）！")
            print(f"   应该至少30-50%仓位才能有效捕捉趋势")

        # 检查买入时的资金使用
        print(f"\n每笔买入时的资金状况:")
        for i, buy in enumerate(buys):
            invested = buy.price * buy.size
            pct = (invested / result.initial_capital) * 100
            print(f"  第{i+1}笔: {invested:,.2f} USDT ({pct:.2f}%)")

    # 6. 价格变动分析
    print("\n" + "="*80)
    print("持仓期间价格变动")
    print("="*80)

    for i in range(len(buys)):
        buy = buys[i]
        sell = sells[i] if i < len(sells) else None

        if sell:
            price_change = (sell.price / buy.price - 1) * 100

            # 检查期间最大涨幅
            buy_idx = None
            sell_idx = None

            for idx, row in df.iterrows():
                ts = row['timestamp']
                if ts == buy.timestamp:
                    buy_idx = idx
                if ts == sell.timestamp:
                    sell_idx = idx
                    break

            if buy_idx is not None and sell_idx is not None:
                period_df = df.iloc[buy_idx:sell_idx+1]
                max_price = period_df['close'].max()
                max_gain = (max_price / buy.price - 1) * 100

                print(f"\n第{i+1}笔:")
                print(f"  买入: {buy.price:,.2f}")
                print(f"  卖出: {sell.price:,.2f}")
                print(f"  实际收益: {price_change:+.2f}%")
                print(f"  期间最高: {max_price:,.2f} ({max_gain:+.2f}%)")
                print(f"  盈亏: {sell.pnl:+,.2f} USDT")

    # 7. 问题总结
    print("\n" + "="*80)
    print("问题总结")
    print("="*80)

    print(f"\n收益低的可能原因:")

    if result.win_rate < 0.3:
        print(f"  ❌ 胜率太低（{result.win_rate*100:.1f}%），大部分交易亏损")

    if avg_position_pct < 30:
        print(f"  ❌ 仓位太小（{avg_position_pct:.2f}%），无法有效捕捉趋势")

    if result.total_trades < 30:
        print(f"  ❌ 交易频率太低（{result.total_trades}笔/3年），错过太多机会")

    print(f"\n建议优化:")
    print(f"  1. 增加仓位（目标30-50%）")
    print(f"  2. 放宽止损（3% → 5-7%）")
    print(f"  3. 降低入场条件（增加交易频率）")
    print(f"  4. 检查PositionSizer配置")


if __name__ == '__main__':
    diagnose()
