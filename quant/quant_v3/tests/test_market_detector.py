"""
测试MarketDetector的检测准确率
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from data.fetcher import BinanceFetcher
from quant_v3.core.market_detector import MarketDetector
import pandas as pd


def test_market_detector():
    print("\n" + "="*80)
    print("MarketDetector 准确率测试（2023-2026）")
    print("="*80)

    # 加载数据
    fetcher = BinanceFetcher()
    df = fetcher.fetch_history('BTC-USDT', '1h', days=1095)

    print(f"\n数据: {len(df)}条")
    print(f"时间: {pd.to_datetime(df['timestamp'].iloc[0], unit='ms')} 至 "
          f"{pd.to_datetime(df['timestamp'].iloc[-1], unit='ms')}")

    # 创建检测器
    detector = MarketDetector(
        lookback_days=90,
        trend_threshold=0.15,
        adx_threshold_strong=30.0,
        adx_threshold_weak=20.0
    )

    # 关键时间点检测
    print(f"\n{'='*80}")
    print("关键时间点检测")
    print(f"{'='*80}")

    # 准备时间点
    test_points = [
        ('2023-03-15', '牛市初期（23k）'),
        ('2023-06-01', '牛市中期（27k）'),
        ('2023-09-01', '牛市后期（26k）'),
        ('2023-12-01', '牛市高潮（42k）'),
        ('2024-03-01', '牛市延续（64k）'),
        ('2024-06-01', '牛市顶部（71k）'),
        ('2024-09-01', '调整期（59k）'),
        ('2024-12-01', '新高（92k）'),
        ('2025-03-01', '顶部（95k）'),
        ('2025-06-01', '下跌中（70k）'),
        ('2025-09-01', '熊市（65k）'),
        ('2026-01-01', '熊市延续（94k反弹）'),
    ]

    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')

    print(f"\n{'时间':<20s} {'描述':<20s} {'实际价格':<15s} {'检测结果':<12s} {'ADX':<10s} {'趋势':<10s}")
    print("-" * 100)

    for date_str, desc in test_points:
        # 找到最接近的索引
        target_date = pd.to_datetime(date_str)
        idx = (df['datetime'] - target_date).abs().idxmin()

        # 检测
        details = detector.get_detection_details(df, idx)

        print(f"{date_str:<20s} {desc:<20s} {details['current_price']:>14,.2f} "
              f"{details['market_state']:<12s} {details['adx']:>9.2f} "
              f"{details['price_trend']:>+9.2%}")

    # 统计整个时期的检测结果
    print(f"\n{'='*80}")
    print("整体检测统计")
    print(f"{'='*80}")

    # 按时间段统计
    periods = [
        ('2023-03-01', '2024-12-31', '牛市期（预期BULL）'),
        ('2025-01-01', '2026-02-28', '熊市期（预期BEAR）'),
    ]

    for start_date, end_date, desc in periods:
        mask = (df['datetime'] >= start_date) & (df['datetime'] <= end_date)
        period_df = df[mask].copy()

        if len(period_df) == 0:
            continue

        # 每7天采样一次（避免过于密集）
        sample_indices = period_df.index[::168]  # 7天 = 168小时

        detections = []
        for idx in sample_indices:
            if idx >= 100:  # 确保有足够数据
                state = detector.detect(df, idx)
                detections.append(state)

        # 统计
        bull_count = detections.count('BULL')
        bear_count = detections.count('BEAR')
        ranging_count = detections.count('RANGING')
        total = len(detections)

        print(f"\n{desc}:")
        print(f"  样本数: {total}")
        print(f"  BULL: {bull_count} ({bull_count/total*100:.1f}%)")
        print(f"  BEAR: {bear_count} ({bear_count/total*100:.1f}%)")
        print(f"  RANGING: {ranging_count} ({ranging_count/total*100:.1f}%)")

        # 判断准确率
        if '牛市期' in desc:
            accuracy = bull_count / total * 100
            print(f"  准确率: {accuracy:.1f}% (BULL识别率)")
            if accuracy >= 60:
                print(f"  ✅ 良好（>60%）")
            else:
                print(f"  ⚠️  需要优化")
        else:  # 熊市期
            accuracy = bear_count / total * 100
            print(f"  准确率: {accuracy:.1f}% (BEAR识别率)")
            if accuracy >= 60:
                print(f"  ✅ 良好（>60%）")
            else:
                print(f"  ⚠️  需要优化")

    # 可视化检测时间线
    print(f"\n{'='*80}")
    print("检测时间线（每30天采样）")
    print(f"{'='*80}")

    sample_step = 720  # 30天 = 720小时
    timeline = []

    for i in range(100, len(df), sample_step):
        state = detector.detect(df, i)
        price = df['close'].iloc[i]
        date = df['datetime'].iloc[i]
        timeline.append({
            'date': date,
            'price': price,
            'state': state
        })

    print(f"\n{'日期':<20s} {'价格':<15s} {'市场状态':<12s}")
    print("-" * 50)
    for t in timeline:
        print(f"{str(t['date']):<20s} {t['price']:>14,.2f} {t['state']:<12s}")


if __name__ == '__main__':
    test_market_detector()
