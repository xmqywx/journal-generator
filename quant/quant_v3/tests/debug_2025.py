"""
调试2025年为什么仍被判定为BULL
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from data.fetcher import BinanceFetcher
from quant_v3.core.market_detector_v2 import MarketDetectorV2
import pandas as pd


def debug_2025():
    print("\n" + "="*80)
    print("调试2025年误判原因")
    print("="*80)

    # 加载数据
    fetcher = BinanceFetcher()
    df = fetcher.fetch_history('BTC-USDT', '1h', days=1095)
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')

    detector = MarketDetectorV2()

    # 测试2025年几个关键点
    test_dates = [
        '2025-01-01',
        '2025-03-01',
        '2025-06-01',
        '2025-09-01',
        '2025-12-01',
    ]

    print(f"\n{'日期':<15s} {'价格':<12s} {'结果':<15s} {'评分':<8s} {'180d':<10s} {'150d':<10s} {'90d':<10s} {'30d':<10s} {'减速':<8s} {'回撤':<8s}")
    print("-" * 120)

    for date_str in test_dates:
        target_date = pd.to_datetime(date_str)
        idx = (df['datetime'] - target_date).abs().idxmin()

        details = detector.get_detection_details(df, idx)

        print(f"{date_str:<15s} {details['current_price']:>11,.2f} "
              f"{details['trend_strength']:<15s} {details['comprehensive_score']:>7.2f} "
              f"{details['trend_365d']:>+9.2%} {details['trend_180d']:>+9.2%} "
              f"{details['trend_90d']:>+9.2%} {details['trend_30d']:>+9.2%} "
              f"{details['deceleration_penalty']:>+7.2f} {details['drawdown_90d']:>+7.2%}")

    # 分析：为什么2025年9月还是BULL?
    print(f"\n{'='*80}")
    print("2025-09-01详细分析")
    print(f"{'='*80}")

    target_date = pd.to_datetime('2025-09-01')
    idx = (df['datetime'] - target_date).abs().idxmin()

    details = detector.get_detection_details(df, idx)

    print(f"\n价格: {details['current_price']:,.2f}")
    print(f"结果: {details['trend_strength']}")
    print(f"评分: {details['comprehensive_score']:.2f}/10")

    print(f"\n各周期趋势:")
    print(f"  180天: {details['trend_365d']:+.2%}")  # super_long_period
    print(f"  150天: {details['trend_180d']:+.2%}")  # long_period
    print(f"  90天: {details['trend_90d']:+.2%}")   # medium_period
    print(f"  30天: {details['trend_30d']:+.2%}")   # short_period

    print(f"\n新增检测:")
    print(f"  趋势减速扣分: {details['deceleration_penalty']:.2f}")
    print(f"  从高点回撤: {details['drawdown_90d']:+.2%} (90天最高: {details['high_90d']:,.2f})")
    print(f"  回撤扣分: {details['drawdown_penalty']:.2f}")

    # 计算各周期起点价格
    for days in [365, 180, 150, 90, 30]:
        start_idx = max(0, idx - days*24)
        start_price = df['close'].iloc[start_idx]
        start_date = df['datetime'].iloc[start_idx]
        change = (details['current_price'] - start_price) / start_price

        print(f"\n{days}天前:")
        print(f"  日期: {start_date}")
        print(f"  价格: {start_price:,.2f}")
        print(f"  涨幅: {change:+.2%}")

    # 分析BTC在这个时期的实际走势
    print(f"\n{'='*80}")
    print("BTC 2025年实际走势")
    print(f"{'='*80}")

    mask_2025 = (df['datetime'] >= '2025-01-01') & (df['datetime'] <= '2025-12-31')
    df_2025 = df[mask_2025]

    print(f"\n2025年:")
    max_idx = df_2025['close'].idxmax()
    min_idx = df_2025['close'].idxmin()
    max_price = df_2025['close'].loc[max_idx]
    min_price = df_2025['close'].loc[min_idx]
    max_date = df_2025['datetime'].loc[max_idx]
    min_date = df_2025['datetime'].loc[min_idx]

    print(f"  最高: {max_price:,.2f} @ {max_date}")
    print(f"  最低: {min_price:,.2f} @ {min_date}")
    print(f"  年初: {df_2025['close'].iloc[0]:,.2f}")
    print(f"  年末: {df_2025['close'].iloc[-1]:,.2f}")
    print(f"  年度变化: {(df_2025['close'].iloc[-1] / df_2025['close'].iloc[0] - 1):+.2%}")


if __name__ == '__main__':
    debug_2025()
