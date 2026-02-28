"""
分析交易时间和持仓时长
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from data.fetcher import BinanceFetcher
import pandas as pd
import numpy as np


def analyze_timing(entry_threshold=1.0, exit_threshold=0.3):
    print(f"\n{'='*80}")
    print(f"交易时间分析（入场±{entry_threshold}，出场±{exit_threshold}）")
    print(f"{'='*80}")

    # 1. 加载数据
    fetcher = BinanceFetcher()
    df_btc = fetcher.fetch_history('BTC-USDT', '1h', days=1095)
    df_eth = fetcher.fetch_history('ETH-USDT', '1h', days=1095)

    df = pd.merge(
        df_btc[['timestamp', 'close']].rename(columns={'close': 'btc_close'}),
        df_eth[['timestamp', 'close']].rename(columns={'close': 'eth_close'}),
        on='timestamp',
        how='inner'
    )

    df['ratio'] = df['btc_close'] / df['eth_close']
    df['log_ratio'] = np.log(df['ratio'])
    mean = df['log_ratio'].mean()
    std = df['log_ratio'].std()
    df['z_score'] = (df['z_score'] if 'z_score' in df.columns
                     else (df['log_ratio'] - mean) / std)

    # 重新计算（确保正确）
    df['z_score'] = (df['log_ratio'] - mean) / std

    # 2. 模拟交易并记录详细时间
    position = None
    entry_time = None
    entry_idx = None
    trades = []

    for i in range(100, len(df)):
        z_score = df['z_score'].iloc[i]
        timestamp = df['timestamp'].iloc[i]

        if position is None:
            # 检查入场
            if z_score > entry_threshold:
                position = 'SHORT_SPREAD'
                entry_time = timestamp
                entry_idx = i
            elif z_score < -entry_threshold:
                position = 'LONG_SPREAD'
                entry_time = timestamp
                entry_idx = i
        else:
            # 检查出场
            should_exit = False
            if position == 'SHORT_SPREAD' and z_score < exit_threshold:
                should_exit = True
            elif position == 'LONG_SPREAD' and z_score > -exit_threshold:
                should_exit = True

            if should_exit:
                holding_hours = i - entry_idx
                holding_days = holding_hours / 24

                trades.append({
                    'type': position,
                    'entry_time': entry_time,
                    'exit_time': timestamp,
                    'entry_idx': entry_idx,
                    'exit_idx': i,
                    'holding_hours': holding_hours,
                    'holding_days': holding_days
                })

                position = None

    # 3. 统计
    print(f"\n总交易数: {len(trades)}")

    if len(trades) > 0:
        print(f"\n交易详情:")
        print(f"{'序号':<6s} {'类型':<20s} {'入场时间':<20s} {'出场时间':<20s} {'持仓时长':<15s}")
        print("-" * 90)

        for i, trade in enumerate(trades):
            entry_dt = pd.to_datetime(trade['entry_time'], unit='ms')
            exit_dt = pd.to_datetime(trade['exit_time'], unit='ms')
            print(f"{i+1:<6d} {trade['type']:<20s} {str(entry_dt):<20s} "
                  f"{str(exit_dt):<20s} {trade['holding_days']:.1f}天 ({trade['holding_hours']}小时)")

        # 统计
        avg_holding = np.mean([t['holding_days'] for t in trades])
        max_holding = max([t['holding_days'] for t in trades])
        min_holding = min([t['holding_days'] for t in trades])

        print(f"\n持仓时长统计:")
        print(f"  平均: {avg_holding:.1f}天")
        print(f"  最短: {min_holding:.1f}天")
        print(f"  最长: {max_holding:.1f}天")

        # 计算错过的机会
        total_days = (df['timestamp'].iloc[-1] - df['timestamp'].iloc[100]) / (1000 * 60 * 60 * 24)
        busy_days = sum([t['holding_days'] for t in trades])
        idle_days = total_days - busy_days
        idle_pct = idle_days / total_days * 100

        print(f"\n资金使用率:")
        print(f"  总天数: {total_days:.1f}天")
        print(f"  持仓天数: {busy_days:.1f}天")
        print(f"  空闲天数: {idle_days:.1f}天 ({idle_pct:.1f}%)")

        # 分析错过的入场机会
        print(f"\n错过的入场机会分析:")

        missed_long = 0
        missed_short = 0

        for i in range(100, len(df)):
            z_score = df['z_score'].iloc[i]

            # 检查是否在持仓期间
            in_position = False
            for trade in trades:
                if trade['entry_idx'] <= i < trade['exit_idx']:
                    in_position = True
                    break

            if in_position:
                # 持仓期间，检查是否有新的入场信号
                if z_score > entry_threshold:
                    missed_short += 1
                elif z_score < -entry_threshold:
                    missed_long += 1

        print(f"  持仓期间错过做多机会: {missed_long}")
        print(f"  持仓期间错过做空机会: {missed_short}")
        print(f"  总计错过: {missed_long + missed_short}")

    else:
        print("\n❌ 没有完成任何交易")


if __name__ == '__main__':
    # 测试不同参数
    analyze_timing(entry_threshold=1.0, exit_threshold=0.3)
    analyze_timing(entry_threshold=1.5, exit_threshold=0.5)
    analyze_timing(entry_threshold=2.0, exit_threshold=0.5)
