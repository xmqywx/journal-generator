"""
分析为什么错过30k→63k的主升浪
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from data.fetcher import BinanceFetcher
from quant_v2.core.market_regime import MarketRegime
from quant_v2.strategies.multi_timeframe_trend import MultiTimeframeTrendStrategy
import pandas as pd
import numpy as np


def analyze():
    print("\n" + "="*80)
    print("分析为什么错过主升浪（30k → 63k）")
    print("="*80)

    # 1. 加载数据
    fetcher = BinanceFetcher()
    df = fetcher.fetch_history('BTC-USDT', '1h', days=1095)

    print(f"\n数据范围:")
    print(f"  起始: {pd.to_datetime(df['timestamp'].iloc[0], unit='ms')}")
    print(f"  结束: {pd.to_datetime(df['timestamp'].iloc[-1], unit='ms')}")
    print(f"  价格: {df['close'].iloc[0]:.2f} → {df['close'].iloc[-1]:.2f}")

    # 2. 分析市场环境
    print(f"\n{'='*80}")
    print("市场环境分析")
    print(f"{'='*80}")

    market_regime = MarketRegime()
    regimes = []

    for i in range(len(df)):
        regime = market_regime.identify(df, i)
        regimes.append(regime)

    df['regime'] = regimes

    # 找出30k后的数据（2023年5月之后）
    df['price_level'] = pd.cut(df['close'], bins=[0, 30000, 40000, 50000, 60000, 70000],
                                labels=['<30k', '30-40k', '40-50k', '50-60k', '60-70k'])

    print(f"\n不同价格区间的市场环境分布:")
    for level in ['<30k', '30-40k', '40-50k', '50-60k', '60-70k']:
        level_df = df[df['price_level'] == level]
        if len(level_df) > 0:
            regime_dist = level_df['regime'].value_counts()
            print(f"\n{level}区间 ({len(level_df)}条数据):")
            for regime, count in regime_dist.items():
                pct = count / len(level_df) * 100
                print(f"  {regime}: {count} ({pct:.1f}%)")

    # 3. 检查策略信号
    print(f"\n{'='*80}")
    print("策略信号分析")
    print(f"{'='*80}")

    strategy = MultiTimeframeTrendStrategy(
        ema_fast=12,
        ema_slow=26,
        adx_threshold=20.0,  # 使用优化后的参数
        volume_multiplier=1.05,
        trailing_stop_pct=0.03,
        max_holding_hours=168
    )

    # 检查每个价格区间的信号
    for level in ['30-40k', '40-50k', '50-60k']:
        level_df = df[df['price_level'] == level]
        if len(level_df) > 0:
            print(f"\n{level}区间:")

            buy_count = 0
            for idx in level_df.index:
                if idx < max(strategy.ema_slow, 50):
                    continue

                regime = df['regime'].iloc[idx]
                signal, strength = strategy.generate_signal(df, idx, regime)

                if signal == 'BUY':
                    buy_count += 1

            print(f"  BUY信号数: {buy_count}/{len(level_df)} ({buy_count/len(level_df)*100:.2f}%)")

    # 4. 详细检查40-50k区间（应该是trending_up）
    print(f"\n{'='*80}")
    print("40-50k区间详细分析（2024年初主升浪）")
    print(f"{'='*80}")

    level_40_50k = df[(df['close'] >= 40000) & (df['close'] < 50000)]

    if len(level_40_50k) > 0:
        print(f"\n数据量: {len(level_40_50k)}")
        print(f"时间范围: {pd.to_datetime(level_40_50k['timestamp'].iloc[0], unit='ms')} 至 "
              f"{pd.to_datetime(level_40_50k['timestamp'].iloc[-1], unit='ms')}")

        # 计算技术指标
        ema_12 = df['close'].ewm(span=12, adjust=False).mean()
        ema_26 = df['close'].ewm(span=26, adjust=False).mean()

        # 检查为什么没有BUY信号
        print(f"\n为什么没有BUY信号？")

        sample_indices = level_40_50k.index[::100]  # 每100条采样一次
        for idx in sample_indices[:5]:  # 只看前5个样本
            regime = df['regime'].iloc[idx]
            price = df['close'].iloc[idx]
            signal, strength = strategy.generate_signal(df, idx, regime)

            print(f"\n样本 [{pd.to_datetime(df['timestamp'].iloc[idx], unit='ms')}]:")
            print(f"  价格: {price:.2f}")
            print(f"  市场环境: {regime}")
            print(f"  信号: {signal}")

            # 详细检查条件
            ema_fast_val = ema_12.iloc[idx]
            ema_slow_val = ema_26.iloc[idx]
            ema_trend = "UP" if ema_fast_val > ema_slow_val else "DOWN"

            print(f"  EMA12: {ema_fast_val:.2f}, EMA26: {ema_slow_val:.2f} → {ema_trend}")

            # 检查regime是否trending_up
            if regime != 'trending_up':
                print(f"  ❌ 问题：市场环境不是trending_up，而是{regime}")

    # 5. 简单买入持有对比
    print(f"\n{'='*80}")
    print("买入持有策略对比")
    print(f"{'='*80}")

    # 假设在2023年5月1日买入（30k左右）
    buy_date = pd.to_datetime('2023-05-01')
    buy_df = df[pd.to_datetime(df['timestamp'], unit='ms') >= buy_date]

    if len(buy_df) > 0:
        buy_price = buy_df['close'].iloc[0]
        final_price = df['close'].iloc[-1]
        buy_hold_return = (final_price / buy_price - 1) * 100

        print(f"\n如果在2023-05-01买入并持有:")
        print(f"  买入价: {buy_price:.2f}")
        print(f"  当前价: {final_price:.2f}")
        print(f"  收益: {buy_hold_return:+.2f}%")
        print(f"\n对比策略收益: +5.56%")
        print(f"差距: {buy_hold_return - 5.56:.2f}%")


if __name__ == '__main__':
    analyze()
