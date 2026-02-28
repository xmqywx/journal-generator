"""
测试EMA排列和价格极值检测
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from data.fetcher import BinanceFetcher
import pandas as pd


def test_ema_alignment():
    print("\n" + "="*80)
    print("测试EMA排列检测")
    print("="*80)

    fetcher = BinanceFetcher()
    df = fetcher.fetch_history('BTC-USDT', '1h', days=1095)
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')

    # 计算EMA
    ema8 = df['close'].ewm(span=8, adjust=False).mean()
    ema21 = df['close'].ewm(span=21, adjust=False).mean()
    ema55 = df['close'].ewm(span=55, adjust=False).mean()

    # 测试2024-03-01（明显牛市）
    target_date = pd.to_datetime('2024-03-01')
    idx = (df['datetime'] - target_date).abs().idxmin()

    print(f"\n2024-03-01 (BTC {df['close'].iloc[idx]:,.2f}):")
    print(f"  EMA8:  {ema8.iloc[idx]:,.2f}")
    print(f"  EMA21: {ema21.iloc[idx]:,.2f}")
    print(f"  EMA55: {ema55.iloc[idx]:,.2f}")
    print(f"  EMA8 > EMA21: {ema8.iloc[idx] > ema21.iloc[idx]}")
    print(f"  EMA21 > EMA55: {ema21.iloc[idx] > ema55.iloc[idx]}")

    if ema8.iloc[idx] > ema21.iloc[idx] > ema55.iloc[idx]:
        print(f"  ✓ 多头排列")
    elif ema8.iloc[idx] < ema21.iloc[idx] < ema55.iloc[idx]:
        print(f"  ✓ 空头排列")
    else:
        print(f"  ✗ 无明显排列")

    # 测试2024-12-01（新高）
    target_date = pd.to_datetime('2024-12-01')
    idx = (df['datetime'] - target_date).abs().idxmin()

    print(f"\n2024-12-01 (BTC {df['close'].iloc[idx]:,.2f}):")
    print(f"  EMA8:  {ema8.iloc[idx]:,.2f}")
    print(f"  EMA21: {ema21.iloc[idx]:,.2f}")
    print(f"  EMA55: {ema55.iloc[idx]:,.2f}")
    print(f"  EMA8 > EMA21: {ema8.iloc[idx] > ema21.iloc[idx]}")
    print(f"  EMA21 > EMA55: {ema21.iloc[idx] > ema55.iloc[idx]}")

    if ema8.iloc[idx] > ema21.iloc[idx] > ema55.iloc[idx]:
        print(f"  ✓ 多头排列")
    elif ema8.iloc[idx] < ema21.iloc[idx] < ema55.iloc[idx]:
        print(f"  ✓ 空头排列")
    else:
        print(f"  ✗ 无明显排列")


def test_price_extremes():
    print("\n" + "="*80)
    print("测试价格极值检测")
    print("="*80)

    fetcher = BinanceFetcher()
    df = fetcher.fetch_history('BTC-USDT', '1h', days=1095)
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')

    lookback_days = 60
    lookback_hours = lookback_days * 24

    # 测试2024-12-01（应该是新高）
    target_date = pd.to_datetime('2024-12-01')
    idx = (df['datetime'] - target_date).abs().idxmin()

    start_idx = max(0, idx - lookback_hours)
    period_data = df['close'].iloc[start_idx:idx+1]
    current_price = df['close'].iloc[idx]
    period_high = period_data.max()
    period_low = period_data.min()

    print(f"\n2024-12-01:")
    print(f"  当前价格: {current_price:,.2f}")
    print(f"  60天最高: {period_high:,.2f}")
    print(f"  60天最低: {period_low:,.2f}")
    print(f"  当前 vs 最高: {current_price / period_high:.4f}")
    print(f"  当前 vs 最低: {current_price / period_low:.4f}")

    # 检测逻辑（允许0.5%误差）
    if current_price >= period_high * 0.995:
        print(f"  ✓ 创新高（{current_price:,.2f} >= {period_high * 0.995:,.2f}）")
    elif current_price <= period_low * 1.005:
        print(f"  ✓ 创新低（{current_price:,.2f} <= {period_low * 1.005:,.2f}）")
    else:
        print(f"  ✗ 非新高/新低")

    # 测试2026-01-01（应该是新低）
    target_date = pd.to_datetime('2026-01-01')
    idx = (df['datetime'] - target_date).abs().idxmin()

    start_idx = max(0, idx - lookback_hours)
    period_data = df['close'].iloc[start_idx:idx+1]
    current_price = df['close'].iloc[idx]
    period_high = period_data.max()
    period_low = period_data.min()

    print(f"\n2026-01-01:")
    print(f"  当前价格: {current_price:,.2f}")
    print(f"  60天最高: {period_high:,.2f}")
    print(f"  60天最低: {period_low:,.2f}")
    print(f"  当前 vs 最高: {current_price / period_high:.4f}")
    print(f"  当前 vs 最低: {current_price / period_low:.4f}")

    if current_price >= period_high * 0.995:
        print(f"  ✓ 创新高")
    elif current_price <= period_low * 1.005:
        print(f"  ✓ 创新低（{current_price:,.2f} <= {period_low * 1.005:,.2f}）")
    else:
        print(f"  ✗ 非新高/新低")


if __name__ == '__main__':
    test_ema_alignment()
    test_price_extremes()
