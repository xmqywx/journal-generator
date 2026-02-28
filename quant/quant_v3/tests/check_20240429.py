"""
检查2024-04-29为什么被误判为BEAR
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from data.fetcher import BinanceFetcher
from quant_v3.core.market_detector import MarketDetector
import pandas as pd


def check():
    print("\n" + "="*80)
    print("检查2024-04-29误判原因")
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

    # 找到2024-04-29
    target_date = pd.to_datetime('2024-04-29 05:00:00')
    idx = (df['datetime'] - target_date).abs().idxmin()

    details = detector.get_detection_details(df, idx)

    print(f"\n时间: {df['datetime'].iloc[idx]}")
    print(f"价格: {details['current_price']:,.2f}")
    print(f"检测结果: {details['market_state']}")
    print(f"\n详细评分:")
    print(f"  60天趋势: {details['price_trend']:+.2%}")
    print(f"  EMA排列: {details['ema_alignment']}")
    print(f"  ADX: {details['adx']:.2f}")
    print(f"  价格极值: {details['price_extreme']}")

    # 分析60天前的价格
    lookback_idx = max(0, idx - 60*24)
    price_60d_ago = df['close'].iloc[lookback_idx]
    print(f"\n60天前:")
    print(f"  时间: {df['datetime'].iloc[lookback_idx]}")
    print(f"  价格: {price_60d_ago:,.2f}")
    print(f"  涨幅: {(details['current_price'] - price_60d_ago) / price_60d_ago:+.2%}")

    # 看看之后的价格
    print(f"\n之后的价格走势:")
    future_points = [
        ('30天后', idx + 30*24),
        ('60天后', idx + 60*24),
        ('90天后', idx + 90*24),
    ]

    for desc, future_idx in future_points:
        if future_idx < len(df):
            future_price = df['close'].iloc[future_idx]
            future_date = df['datetime'].iloc[future_idx]
            change = (future_price - details['current_price']) / details['current_price']
            print(f"  {desc} ({future_date}): {future_price:,.2f} ({change:+.2%})")


if __name__ == '__main__':
    check()
