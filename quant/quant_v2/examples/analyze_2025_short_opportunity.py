"""
分析2025-2026年的做空机会
BTC从94k跌到66k（-30%），应该能通过做空获利70%+
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from data.fetcher import BinanceFetcher
import pandas as pd
import numpy as np


def analyze_short_opportunity():
    print("\n" + "="*80)
    print("2025-2026年做空机会分析")
    print("="*80)

    # 加载数据
    fetcher = BinanceFetcher()
    df = fetcher.fetch_history('BTC-USDT', '1h', days=1095)

    # 筛选2025-2026
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
    mask = (df['datetime'] >= '2025-01-01') & (df['datetime'] <= '2026-02-28')
    df_2025 = df[mask].reset_index(drop=True)

    print(f"\n数据概况:")
    print(f"  时间: {df_2025['datetime'].iloc[0]} 至 {df_2025['datetime'].iloc[-1]}")
    print(f"  价格: {df_2025['close'].iloc[0]:.2f} → {df_2025['close'].iloc[-1]:.2f}")
    print(f"  跌幅: {(df_2025['close'].iloc[-1]/df_2025['close'].iloc[0]-1)*100:.2f}%")

    # 1. 简单策略：在高点附近做空，低点平仓
    print(f"\n{'='*80}")
    print("策略1：识别趋势反转做空")
    print(f"{'='*80}")

    # 计算EMA
    ema_fast = df_2025['close'].ewm(span=8, adjust=False).mean()
    ema_slow = df_2025['close'].ewm(span=21, adjust=False).mean()

    capital = 10000
    position = None
    entry_price = 0
    entry_time = 0
    lowest_price = 0
    trades = []

    for i in range(100, len(df_2025)):
        price = df_2025['close'].iloc[i]

        # 持仓检查
        if position == 'SHORT':
            # 更新最低价
            lowest_price = min(lowest_price, price)

            # 移动止损（空头：价格上涨超过15%止损）
            stop_price = lowest_price * 1.15
            if price > stop_price:
                # 止损
                pnl = ((entry_price - price) / entry_price) * (capital * 0.8) * 0.9992
                capital += pnl
                trades.append({
                    'type': 'CLOSE_SHORT',
                    'entry': entry_price,
                    'exit': price,
                    'pnl': pnl,
                    'reason': '止损',
                    'time': df_2025['datetime'].iloc[i]
                })
                position = None
                continue

            # EMA反转（做空信号消失：快线上穿慢线）
            if ema_fast.iloc[i] > ema_slow.iloc[i]:
                # 平仓
                pnl = ((entry_price - price) / entry_price) * (capital * 0.8) * 0.9992
                capital += pnl
                trades.append({
                    'type': 'CLOSE_SHORT',
                    'entry': entry_price,
                    'exit': price,
                    'pnl': pnl,
                    'reason': 'EMA反转',
                    'time': df_2025['datetime'].iloc[i]
                })
                position = None

        # 无持仓，检查做空机会
        else:
            # 做空条件：快线下穿慢线（下跌趋势）
            if ema_fast.iloc[i] < ema_slow.iloc[i] and price < ema_fast.iloc[i]:
                position = 'SHORT'
                entry_price = price
                entry_time = i
                lowest_price = price
                trades.append({
                    'type': 'OPEN_SHORT',
                    'entry': entry_price,
                    'time': df_2025['datetime'].iloc[i]
                })

    # 统计
    close_trades = [t for t in trades if 'pnl' in t]
    total_trades = len(close_trades)
    winning_trades = len([t for t in close_trades if t['pnl'] > 0])
    total_return = (capital - 10000) / 10000

    print(f"\n结果:")
    print(f"  初始: 10,000 USDT")
    print(f"  最终: {capital:,.2f} USDT")
    print(f"  收益: {total_return*100:+.2f}%")
    print(f"  交易数: {total_trades}")
    if total_trades > 0:
        print(f"  胜率: {winning_trades/total_trades*100:.1f}%")

        # 显示交易
        print(f"\n前10笔做空交易:")
        for i, trade in enumerate(close_trades[:10]):
            profit_pct = ((trade['entry'] - trade['exit']) / trade['entry']) * 100
            print(f"  {i+1:2d}. [{trade['time']}] {trade['entry']:>10,.2f} → {trade['exit']:>10,.2f} "
                  f"({profit_pct:+.2f}%), PnL: {trade['pnl']:+,.2f}, {trade['reason']}")

    print(f"\n对比:")
    print(f"  买入持有: -30.15%")
    print(f"  做空策略: {total_return*100:+.2f}%")
    print(f"  差异: {total_return*100 + 30.15:+.2f}%")

    # 2. 理想情况分析
    print(f"\n{'='*80}")
    print("理想做空分析")
    print(f"{'='*80}")

    # 找到最高点和最低点
    max_price = df_2025['close'].max()
    min_price = df_2025['close'].min()
    max_idx = df_2025['close'].idxmax()
    min_idx = df_2025['close'].idxmin()

    print(f"\n价格极值:")
    print(f"  最高: {max_price:.2f} @ {df_2025['datetime'].iloc[max_idx]}")
    print(f"  最低: {min_price:.2f} @ {df_2025['datetime'].iloc[min_idx]}")
    print(f"  跌幅: {(min_price/max_price-1)*100:.2f}%")

    # 如果在最高点做空，最低点平仓
    ideal_short_profit = ((max_price - min_price) / max_price) * 100
    print(f"\n如果在最高点满仓做空，最低点平仓:")
    print(f"  收益: {ideal_short_profit:+.2f}%")

    # 考虑杠杆
    leverage_2x = ideal_short_profit * 2
    leverage_3x = ideal_short_profit * 3

    print(f"\n加杠杆后:")
    print(f"  2倍杠杆: {leverage_2x:+.2f}%")
    print(f"  3倍杠杆: {leverage_3x:+.2f}%")

    if leverage_2x >= 70:
        print(f"\n✅ 2倍杠杆可以达到70%目标！")
    elif leverage_3x >= 70:
        print(f"\n✅ 3倍杠杆可以达到70%目标！")
    else:
        print(f"\n⚠️  需要更高杠杆或更频繁的做空交易")

    # 3. 多次做空累积收益
    print(f"\n{'='*80}")
    print("多次做空累积收益分析")
    print(f"{'='*80}")

    # 找出所有明显的下跌段
    window = 168  # 7天窗口
    declines = []

    for i in range(window, len(df_2025)):
        period_high = df_2025['close'].iloc[i-window:i].max()
        period_low = df_2025['close'].iloc[i-window:i].min()
        current = df_2025['close'].iloc[i]

        # 如果当前是该窗口最低点，且跌幅>10%
        if current == period_low and (period_low / period_high - 1) < -0.10:
            declines.append({
                'high': period_high,
                'low': period_low,
                'decline': (period_low / period_high - 1) * 100
            })

    print(f"\n发现 {len(declines)} 个明显下跌段（跌幅>10%）:")
    for i, d in enumerate(declines[:10]):
        print(f"  {i+1}. {d['high']:.2f} → {d['low']:.2f} ({d['decline']:.2f}%)")

    # 如果每次下跌都做空
    cumulative = 10000
    for d in declines:
        profit = abs(d['decline']) / 100 * cumulative * 0.8  # 80%仓位
        cumulative += profit

    cumulative_return = (cumulative - 10000) / 10000
    print(f"\n如果捕捉所有下跌段:")
    print(f"  初始: 10,000 USDT")
    print(f"  累积: {cumulative:,.2f} USDT")
    print(f"  收益: {cumulative_return*100:+.2f}%")

    if cumulative_return >= 0.70:
        print(f"\n✅ 通过多次做空可以达到70%目标！")


if __name__ == '__main__':
    analyze_short_opportunity()
