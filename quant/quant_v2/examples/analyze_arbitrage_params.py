"""
分析统计套利参数优化
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from data.fetcher import BinanceFetcher
import pandas as pd
import numpy as np


def analyze():
    print("\n" + "="*80)
    print("统计套利参数分析")
    print("="*80)

    # 1. 加载数据
    fetcher = BinanceFetcher()
    df_btc = fetcher.fetch_history('BTC-USDT', '1h', days=1095)
    df_eth = fetcher.fetch_history('ETH-USDT', '1h', days=1095)

    # 2. 对齐并计算Z-score
    df = pd.merge(
        df_btc[['timestamp', 'close']].rename(columns={'close': 'btc'}),
        df_eth[['timestamp', 'close']].rename(columns={'close': 'eth'}),
        on='timestamp',
        how='inner'
    )

    df['ratio'] = df['btc'] / df['eth']
    df['log_ratio'] = np.log(df['ratio'])

    mean = df['log_ratio'].mean()
    std = df['log_ratio'].std()
    df['z_score'] = (df['log_ratio'] - mean) / std

    # 3. Z-score分布分析
    print(f"\n{'='*80}")
    print("Z-score分布")
    print(f"{'='*80}")

    print(f"\n统计量:")
    print(f"  均值: {df['z_score'].mean():.4f}")
    print(f"  标准差: {df['z_score'].std():.4f}")
    print(f"  最小值: {df['z_score'].min():.2f}")
    print(f"  最大值: {df['z_score'].max():.2f}")

    # 百分位分析
    percentiles = [0, 1, 5, 10, 25, 50, 75, 90, 95, 99, 100]
    print(f"\n百分位分布:")
    for p in percentiles:
        value = np.percentile(df['z_score'], p)
        print(f"  {p:3d}%: {value:+.2f}")

    # 4. 不同阈值下的触发频率
    print(f"\n{'='*80}")
    print("不同阈值的触发频率")
    print(f"{'='*80}")

    thresholds = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]

    print(f"\n{'阈值':<10s} {'触发次数':<15s} {'触发率':<15s} {'预计交易对数':<20s}")
    print("-" * 60)

    for threshold in thresholds:
        high_count = (df['z_score'] > threshold).sum()
        low_count = (df['z_score'] < -threshold).sum()
        total_count = high_count + low_count
        trigger_rate = total_count / len(df) * 100
        expected_trades = total_count // 2  # 每对进出算1笔交易

        print(f"±{threshold:<9.1f} {total_count:<15d} {trigger_rate:<14.2f}% {expected_trades:<20d}")

    # 5. 相关性滚动分析
    print(f"\n{'='*80}")
    print("BTC-ETH相关性分析")
    print(f"{'='*80}")

    # 不同窗口的相关性
    windows = [168, 720, 2160]  # 1周、1月、3月（小时）

    print(f"\n不同时间窗口的相关性:")
    for window in windows:
        if window < len(df):
            corr = df['btc'].rolling(window=window).corr(df['eth']).mean()
            print(f"  {window//24:3d}天窗口: {corr:.4f}")

    overall_corr = df['btc'].corr(df['eth'])
    print(f"\n全局相关性: {overall_corr:.4f}")

    if overall_corr < 0.85:
        print(f"  ⚠️  低于0.85阈值，套利风险较高")
        print(f"  建议:")
        print(f"    1. 增加相关性过滤（只在相关性>0.85时交易）")
        print(f"    2. 减小仓位大小（50% → 30%）")
        print(f"    3. 收紧出场阈值（0.5 → 0.3）")

    # 6. 推荐参数
    print(f"\n{'='*80}")
    print("参数优化建议")
    print(f"{'='*80}")

    print(f"\n当前参数:")
    print(f"  入场阈值: ±2.0")
    print(f"  出场阈值: ±0.5")
    print(f"  结果: 3年1笔交易，+51.88%")

    print(f"\n建议优化1（平衡型）:")
    print(f"  入场阈值: ±1.5")
    print(f"  出场阈值: ±0.5")
    print(f"  预期: 约4笔交易，相对安全")

    print(f"\n建议优化2（积极型）:")
    print(f"  入场阈值: ±1.0")
    print(f"  出场阈值: ±0.3")
    print(f"  预期: 约32笔交易，更多机会")

    print(f"\n建议优化3（保守型）:")
    print(f"  入场阈值: ±2.0（不变）")
    print(f"  出场阈值: ±0.3（收紧）")
    print(f"  仓位大小: 30%（降低）")
    print(f"  预期: 约1笔交易，但风险更低")


if __name__ == '__main__':
    analyze()
