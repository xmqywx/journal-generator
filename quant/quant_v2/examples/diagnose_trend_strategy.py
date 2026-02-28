"""
诊断MultiTimeframeTrend策略为什么没有交易

分析每个入场条件的通过率
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from data.fetcher import BinanceFetcher
from quant_v2.strategies.multi_timeframe_trend import MultiTimeframeTrendStrategy
from quant_v2.core.market_regime import MarketRegime
import pandas as pd
import numpy as np


def calculate_ema(df: pd.DataFrame, period: int) -> pd.Series:
    """计算EMA"""
    return df['close'].ewm(span=period, adjust=False).mean()


def calculate_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """计算ADX"""
    high = df['high']
    low = df['low']
    close = df['close']

    plus_dm = high.diff()
    minus_dm = -low.diff()

    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)

    tr = pd.DataFrame({
        'hl': high - low,
        'hc': abs(high - close.shift(1)),
        'lc': abs(low - close.shift(1))
    }).max(axis=1)

    atr = tr.rolling(window=period).mean()
    plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)

    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = dx.rolling(window=period).mean()

    return adx


def diagnose():
    print("\n" + "="*80)
    print("MultiTimeframeTrend 策略诊断")
    print("="*80)

    # 1. 加载数据
    print("\n加载数据...")
    fetcher = BinanceFetcher()
    df = fetcher.fetch_history('BTC-USDT', '1h', days=1095)

    if df.empty:
        print("❌ 数据下载失败")
        return

    print(f"✅ 成功加载 {len(df)} 条数据")
    print(f"   时间范围: {df['timestamp'].iloc[0]} 至 {df['timestamp'].iloc[-1]}")

    # 2. 计算技术指标
    print("\n计算技术指标...")
    df['ema_12'] = calculate_ema(df, 12)
    df['ema_26'] = calculate_ema(df, 26)
    df['adx'] = calculate_adx(df, 14)
    df['volume_ma'] = df['volume'].rolling(window=20).mean()

    # 3. 分析每个条件的通过率
    print("\n" + "="*80)
    print("条件分析（从第100条数据开始统计，避免指标未稳定）")
    print("="*80)

    start_idx = 100
    total_bars = len(df) - start_idx

    # 条件1: EMA趋势（快线 > 慢线）
    ema_bullish = df['ema_12'] > df['ema_26']
    ema_bullish_count = ema_bullish.iloc[start_idx:].sum()
    ema_bullish_pct = ema_bullish_count / total_bars * 100

    print(f"\n1️⃣ EMA趋势（快线 > 慢线）:")
    print(f"   通过: {ema_bullish_count}/{total_bars} ({ema_bullish_pct:.1f}%)")

    # 条件2: EMA持续5根
    ema_sustained = pd.Series(False, index=df.index)
    for i in range(5, len(df)):
        if all(df['ema_12'].iloc[i-j] > df['ema_26'].iloc[i-j] for j in range(5)):
            ema_sustained.iloc[i] = True

    ema_sustained_count = ema_sustained.iloc[start_idx:].sum()
    ema_sustained_pct = ema_sustained_count / total_bars * 100

    print(f"\n2️⃣ EMA持续5根K线:")
    print(f"   通过: {ema_sustained_count}/{total_bars} ({ema_sustained_pct:.1f}%)")

    # 条件3: ADX > 25
    adx_strong = df['adx'] > 25
    adx_strong_count = adx_strong.iloc[start_idx:].sum()
    adx_strong_pct = adx_strong_count / total_bars * 100

    print(f"\n3️⃣ ADX > 25 (趋势强度):")
    print(f"   通过: {adx_strong_count}/{total_bars} ({adx_strong_pct:.1f}%)")
    print(f"   ADX平均值: {df['adx'].iloc[start_idx:].mean():.2f}")
    print(f"   ADX最大值: {df['adx'].iloc[start_idx:].max():.2f}")

    # 条件4: ADX上升
    adx_rising = df['adx'].diff() > 0
    adx_rising_count = adx_rising.iloc[start_idx:].sum()
    adx_rising_pct = adx_rising_count / total_bars * 100

    print(f"\n4️⃣ ADX上升 (斜率 > 0):")
    print(f"   通过: {adx_rising_count}/{total_bars} ({adx_rising_pct:.1f}%)")

    # 条件5: ADX > 25 且上升
    adx_confirmed = adx_strong & adx_rising
    adx_confirmed_count = adx_confirmed.iloc[start_idx:].sum()
    adx_confirmed_pct = adx_confirmed_count / total_bars * 100

    print(f"\n5️⃣ ADX > 25 且上升 (两个条件同时满足):")
    print(f"   通过: {adx_confirmed_count}/{total_bars} ({adx_confirmed_pct:.1f}%)")

    # 条件6: 成交量 > 均值1.2倍
    volume_high = df['volume'] > df['volume_ma'] * 1.2
    volume_high_count = volume_high.iloc[start_idx:].sum()
    volume_high_pct = volume_high_count / total_bars * 100

    print(f"\n6️⃣ 成交量 > 均值1.2倍:")
    print(f"   通过: {volume_high_count}/{total_bars} ({volume_high_pct:.1f}%)")

    # 条件7: 价格在快线之上，快线在慢线之上（最严格的条件！）
    price_above_ema = df['close'] > df['ema_12']
    fast_above_slow = df['ema_12'] > df['ema_26']
    price_structure = price_above_ema & fast_above_slow
    price_structure_count = price_structure.iloc[start_idx:].sum()
    price_structure_pct = price_structure_count / total_bars * 100

    print(f"\n7️⃣ 价格结构 (价格 > 快线 > 慢线):")
    print(f"   通过: {price_structure_count}/{total_bars} ({price_structure_pct:.1f}%)")

    # 条件8: 市场环境（动态识别）
    print(f"\n8️⃣ 市场环境识别:")
    print(f"   正在计算...")
    market_regime = MarketRegime()
    regimes = []
    for i in range(len(df)):
        regime = market_regime.identify(df, i)
        regimes.append(regime)
    df['regime'] = regimes

    regime_counts = df['regime'].iloc[start_idx:].value_counts()
    print(f"   分布:")
    for regime, count in regime_counts.items():
        pct = count / total_bars * 100
        print(f"     {regime}: {count} ({pct:.1f}%)")

    # 条件9: 市场环境匹配趋势（trending_up或trending_down）
    trending_regimes = (df['regime'] == 'trending_up') | (df['regime'] == 'trending_down')
    trending_regimes_count = trending_regimes.iloc[start_idx:].sum()
    trending_regimes_pct = trending_regimes_count / total_bars * 100

    print(f"\n9️⃣ 市场环境为趋势状态:")
    print(f"   通过: {trending_regimes_count}/{total_bars} ({trending_regimes_pct:.1f}%)")

    # 条件10: 所有条件同时满足（包括市场环境）
    # 做多需要：EMA向上 + regime = trending_up
    # 做空需要：EMA向下 + regime = trending_down
    # 目前我们只检查做多的情况
    all_conditions_long = ema_sustained & adx_confirmed & volume_high & price_structure & (df['regime'] == 'trending_up')
    all_conditions_long_count = all_conditions_long.iloc[start_idx:].sum()
    all_conditions_long_pct = all_conditions_long_count / total_bars * 100

    print(f"\n🔟 所有条件同时满足（做多）:")
    print(f"   通过: {all_conditions_long_count}/{total_bars} ({all_conditions_long_pct:.1f}%)")

    # 找出满足条件的时间点
    if all_conditions_long_count > 0:
        print(f"\n满足做多条件的时间点:")
        satisfied_indices = df[all_conditions_long].index[:10]  # 只显示前10个
        for idx in satisfied_indices:
            row = df.loc[idx]
            print(f"   {row['timestamp']}: 价格={row['close']:.2f}, ADX={row['adx']:.2f}, 成交量={row['volume']:.0f}, 环境={row['regime']}")

    # 10. 关键发现
    print("\n" + "="*80)
    print("关键发现")
    print("="*80)

    print(f"\n瓶颈分析:")
    print(f"  • EMA持续5根: {ema_sustained_pct:.1f}% 通过")
    print(f"  • ADX>25且上升: {adx_confirmed_pct:.1f}% 通过")
    print(f"  • 成交量>1.2倍: {volume_high_pct:.1f}% 通过（最大瓶颈）")
    print(f"  • 价格结构: {price_structure_pct:.1f}% 通过")
    print(f"  • 市场环境trending: {trending_regimes_pct:.1f}% 通过")
    print(f"  • 所有条件（做多）: {all_conditions_long_pct:.1f}% 通过")

    if all_conditions_long_pct < 1:
        print(f"\n❌ 问题：条件太严格，3年只有 {all_conditions_long_pct:.2f}% 的时间满足")
        print(f"\n建议优化（按优先级）:")
        print(f"  1. 🔴 降低成交量倍数（1.2 → 1.05）- 最大瓶颈")
        print(f"  2. 🟡 去掉ADX上升要求（只要>阈值即可）")
        print(f"  3. 🟡 降低ADX阈值（25 → 20）")
        print(f"  4. 🟢 减少EMA持续要求（5根 → 3根）")
    else:
        print(f"\n✅ 有 {all_conditions_long_pct:.2f}% 的时间满足条件，但仍然没有交易")
        print(f"   可能原因：")
        print(f"   1. 仓位计算问题")
        print(f"   2. 风控过严")
        print(f"   3. 代码逻辑错误")


if __name__ == '__main__':
    diagnose()
