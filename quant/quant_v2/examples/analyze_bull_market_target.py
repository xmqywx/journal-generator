"""
分析牛市（2023-2024）应该如何达到400%收益
BTC从23k涨到94k（+309%），应该能做到400%+
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from data.fetcher import BinanceFetcher
import pandas as pd


def analyze_bull_market():
    print("\n" + "="*80)
    print("牛市（2023-2024）400%收益目标分析")
    print("="*80)

    # 加载数据
    fetcher = BinanceFetcher()
    df = fetcher.fetch_history('BTC-USDT', '1h', days=1095)

    # 筛选2023-2024
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
    mask = (df['datetime'] >= '2023-03-01') & (df['datetime'] <= '2024-12-31')
    df_bull = df[mask].reset_index(drop=True)

    print(f"\n数据概况:")
    print(f"  时间: {df_bull['datetime'].iloc[0]} 至 {df_bull['datetime'].iloc[-1]}")
    print(f"  价格: {df_bull['close'].iloc[0]:.2f} → {df_bull['close'].iloc[-1]:.2f}")

    price_gain = (df_bull['close'].iloc[-1] / df_bull['close'].iloc[0] - 1) * 100
    print(f"  涨幅: {price_gain:+.2f}%")

    # 1. 买入持有
    print(f"\n{'='*80}")
    print("策略1：简单买入持有")
    print(f"{'='*80}")

    buy_hold_1x = price_gain
    buy_hold_2x = price_gain * 2
    buy_hold_3x = price_gain * 3

    print(f"\n1倍（无杠杆）: {buy_hold_1x:+.2f}%")
    print(f"2倍杠杆: {buy_hold_2x:+.2f}%")
    print(f"3倍杠杆: {buy_hold_3x:+.2f}%")

    if buy_hold_2x >= 400:
        print(f"\n✅ 2倍杠杆买入持有可以达到400%！")
    elif buy_hold_3x >= 400:
        print(f"\n✅ 3倍杠杆买入持有可以达到400%！")
    else:
        print(f"\n⚠️  即使3倍杠杆也未达到400%，需要其他策略")

    # 2. 加仓策略
    print(f"\n{'='*80}")
    print("策略2：趋势中加仓")
    print(f"{'='*80}")

    # 计算EMA
    ema_fast = df_bull['close'].ewm(span=8, adjust=False).mean()
    ema_slow = df_bull['close'].ewm(span=21, adjust=False).mean()

    capital = 10000
    position_size = 0  # BTC数量
    trades = []
    last_add_price = 0

    for i in range(100, len(df_bull)):
        price = df_bull['close'].iloc[i]

        # 牛市信号：快线>慢线且价格>快线
        if ema_fast.iloc[i] > ema_slow.iloc[i] and price > ema_fast.iloc[i]:

            # 初次买入
            if position_size == 0:
                # 满仓买入
                position_size = (capital * 1.0) / price
                last_add_price = price
                trades.append({
                    'action': 'BUY',
                    'price': price,
                    'size': position_size,
                    'time': df_bull['datetime'].iloc[i],
                    'reason': '初始买入'
                })

            # 加仓条件：价格上涨10%且还有资金
            elif price > last_add_price * 1.10 and capital > 1000:
                # 用10%资金加仓
                add_size = (capital * 0.1) / price
                position_size += add_size
                capital -= capital * 0.1
                last_add_price = price
                trades.append({
                    'action': 'ADD',
                    'price': price,
                    'size': add_size,
                    'time': df_bull['datetime'].iloc[i],
                    'reason': f'加仓（涨幅>10%）'
                })

        # 止损/平仓条件：快线<慢线（趋势反转）
        elif position_size > 0 and ema_fast.iloc[i] < ema_slow.iloc[i]:
            # 全部卖出
            sell_value = position_size * price
            capital = sell_value
            trades.append({
                'action': 'SELL',
                'price': price,
                'size': position_size,
                'value': sell_value,
                'time': df_bull['datetime'].iloc[i],
                'reason': 'EMA反转'
            })
            position_size = 0

    # 最终价值
    final_value = capital + (position_size * df_bull['close'].iloc[-1] if position_size > 0 else 0)
    total_return = (final_value - 10000) / 10000

    print(f"\n结果:")
    print(f"  初始: 10,000 USDT")
    print(f"  最终: {final_value:,.2f} USDT")
    print(f"  收益: {total_return*100:+.2f}%")
    print(f"  交易数: {len(trades)}")

    # 显示部分交易
    print(f"\n关键交易:")
    for i, trade in enumerate(trades[:20]):
        if trade['action'] == 'BUY':
            print(f"  {trade['time']}: {trade['action']:<6s} {trade['size']:.4f} BTC @ {trade['price']:>10,.2f} - {trade['reason']}")
        elif trade['action'] == 'ADD':
            print(f"  {trade['time']}: {trade['action']:<6s} {trade['size']:.4f} BTC @ {trade['price']:>10,.2f} - {trade['reason']}")
        elif trade['action'] == 'SELL':
            print(f"  {trade['time']}: {trade['action']:<6s} {trade['size']:.4f} BTC @ {trade['price']:>10,.2f} - {trade['reason']}")

    if total_return >= 4.0:
        print(f"\n✅ 加仓策略达到400%目标！")
    else:
        print(f"\n⚠️  加仓策略未达标，距离400%还差: {(4.0 - total_return)*100:.2f}%")

    # 3. 杠杆+加仓
    print(f"\n{'='*80}")
    print("策略3：2倍杠杆 + 加仓")
    print(f"{'='*80}")

    leveraged_return = total_return * 2
    print(f"\n2倍杠杆下的收益: {leveraged_return*100:+.2f}%")

    if leveraged_return >= 4.0:
        print(f"✅ 2倍杠杆+加仓达到400%目标！")

    # 4. 理想情况
    print(f"\n{'='*80}")
    print("理想情况分析")
    print(f"{'='*80}")

    # 找最低点和最高点
    min_price = df_bull['close'].min()
    max_price = df_bull['close'].max()
    min_idx = df_bull['close'].idxmin()
    max_idx = df_bull['close'].idxmax()

    print(f"\n价格极值:")
    print(f"  最低: {min_price:.2f} @ {df_bull['datetime'].iloc[min_idx]}")
    print(f"  最高: {max_price:.2f} @ {df_bull['datetime'].iloc[max_idx]}")

    ideal_gain = (max_price / min_price - 1) * 100
    print(f"\n如果在最低点买入，最高点卖出:")
    print(f"  收益: {ideal_gain:+.2f}%")

    ideal_2x = ideal_gain * 2
    ideal_3x = ideal_gain * 3
    print(f"\n加杠杆:")
    print(f"  2倍: {ideal_2x:+.2f}%")
    print(f"  3倍: {ideal_3x:+.2f}%")

    # 总结
    print(f"\n{'='*80}")
    print("总结")
    print(f"{'='*80}")

    print(f"\n达到400%的方案:")
    print(f"  1. 1.5倍杠杆买入持有: {price_gain*1.5:+.2f}%")
    print(f"  2. 2倍杠杆买入持有: {buy_hold_2x:+.2f}%")
    print(f"  3. 加仓策略: {total_return*100:+.2f}%")
    print(f"  4. 2倍杠杆+加仓: {leveraged_return*100:+.2f}%")
    print(f"  5. 理想3倍杠杆: {ideal_3x:+.2f}%")

    print(f"\n推荐方案:")
    if buy_hold_2x >= 400:
        print(f"  ✅ 2倍杠杆买入持有最简单（{buy_hold_2x:+.2f}%）")
    elif leveraged_return >= 400:
        print(f"  ✅ 2倍杠杆+加仓（{leveraged_return*100:+.2f}%）")
    else:
        print(f"  ⚠️  需要更高杠杆或更频繁的加仓")


if __name__ == '__main__':
    analyze_bull_market()
