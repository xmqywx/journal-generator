"""
检查为什么2023-05-12之后没有再次买入
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from data.fetcher import BinanceFetcher
from quant_v3.core.market_detector import MarketDetector
from quant_v3.strategies.bull_market_hold import BullMarketHold
import pandas as pd


def check():
    print("\n" + "="*80)
    print("检查2023年5月之后的BULL信号")
    print("="*80)

    # 加载数据
    fetcher = BinanceFetcher()
    df = fetcher.fetch_history('BTC-USDT', '1h', days=1095)
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')

    detector = MarketDetector(
        lookback_days=60,
        trend_threshold=0.10,
        adx_threshold_strong=25.0,
        adx_threshold_weak=15.0
    )

    strategy = BullMarketHold(leverage=2.0)

    # 找到2023-05-12之后的BULL时期
    start_idx = (df['datetime'] - pd.to_datetime('2023-05-12')).abs().idxmin()

    bull_periods = []
    current_bull_start = None

    for i in range(start_idx, min(start_idx + 10000, len(df))):
        if i < 100:
            continue

        market_state = detector.detect(df, i)

        if market_state == 'BULL' and current_bull_start is None:
            current_bull_start = i
        elif market_state != 'BULL' and current_bull_start is not None:
            bull_periods.append({
                'start_idx': current_bull_start,
                'end_idx': i - 1,
                'start_time': df['datetime'].iloc[current_bull_start],
                'end_time': df['datetime'].iloc[i - 1],
                'start_price': df['close'].iloc[current_bull_start],
                'end_price': df['close'].iloc[i - 1],
                'duration_hours': i - current_bull_start
            })
            current_bull_start = None

    print(f"\n找到 {len(bull_periods)} 个BULL时期:")
    print(f"\n{'开始时间':<20s} {'结束时间':<20s} {'持续(小时)':<12s} {'开始价格':<12s} {'结束价格':<12s}")
    print("-" * 90)

    for i, bp in enumerate(bull_periods[:20]):
        print(f"{str(bp['start_time']):<20s} {str(bp['end_time']):<20s} "
              f"{bp['duration_hours']:>11d} {bp['start_price']:>11,.2f} {bp['end_price']:>11,.2f}")

        if i == 0:
            # 检查第一个BULL期间策略为什么不买入
            print(f"\n检查第一个BULL期间的策略信号:")
            print(f"  策略当前持仓: {strategy.position}")

            signal, strength = strategy.generate_signal(df, bp['start_idx'], 'BULL')
            print(f"  策略信号: {signal}, 杠杆: {strength}")


if __name__ == '__main__':
    check()
