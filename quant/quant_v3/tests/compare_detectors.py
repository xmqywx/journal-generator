"""
对比MarketDetectorV1和V2的准确率
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from data.fetcher import BinanceFetcher
from quant_v3.core.market_detector import MarketDetector as V1
from quant_v3.core.market_detector_v2 import MarketDetectorV2 as V2
import pandas as pd


def compare_detectors():
    print("\n" + "="*80)
    print("MarketDetector V1 vs V2 准确率对比")
    print("="*80)

    # 加载数据
    fetcher = BinanceFetcher()
    df = fetcher.fetch_history('BTC-USDT', '1h', days=1095)
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')

    print(f"\n数据: {len(df)}条")
    print(f"时间: {df['datetime'].iloc[0]} 至 {df['datetime'].iloc[-1]}")

    # 创建两个检测器
    detector_v1 = V1(
        lookback_days=60,
        trend_threshold=0.10,
        adx_threshold_strong=25.0,
        adx_threshold_weak=15.0
    )

    detector_v2 = V2(
        short_period=30,
        medium_period=90,
        long_period=150,
        super_long_period=180,  # 改为180天减少滞后
        adx_threshold_strong=25.0,
        adx_threshold_weak=15.0
    )

    # 测试关键时间点
    print(f"\n{'='*80}")
    print("关键时间点检测对比")
    print(f"{'='*80}")

    test_points = [
        ('2023-03-15', '牛市初期（23k）', 'BULL'),
        ('2023-06-01', '牛市中期（27k）', 'BULL'),
        ('2023-09-01', '牛市后期（26k）', 'BULL'),
        ('2023-12-01', '牛市高潮（42k）', 'BULL'),
        ('2024-03-01', '牛市延续（64k）', 'BULL'),
        ('2024-06-01', '牛市顶部（71k）', 'BULL'),
        ('2024-12-01', '新高（92k）', 'BULL'),
        ('2025-03-01', '顶部后下跌（95k）', 'RANGING'),
        ('2025-09-01', '熊市（65k）', 'RANGING'),
        ('2026-01-01', '熊市延续（94k反弹）', 'BEAR'),
    ]

    print(f"\n{'时间':<20s} {'描述':<20s} {'预期':<10s} {'V1结果':<10s} {'V2结果':<15s} {'V2评分':<10s}")
    print("-" * 95)

    v1_correct = 0
    v2_correct = 0
    total = 0

    for date_str, desc, expected in test_points:
        target_date = pd.to_datetime(date_str)
        idx = (df['datetime'] - target_date).abs().idxmin()

        # V1检测
        v1_state = detector_v1.detect(df, idx)

        # V2检测
        v2_state = detector_v2.detect(df, idx)
        v2_details = detector_v2.get_detection_details(df, idx)
        v2_strength = v2_details['trend_strength']
        v2_score = v2_details['comprehensive_score']

        # 统计
        total += 1
        if v1_state == expected:
            v1_correct += 1
        if v2_state == expected:
            v2_correct += 1

        # 显示
        v1_mark = "✅" if v1_state == expected else "❌"
        v2_mark = "✅" if v2_state == expected else "❌"

        print(f"{date_str:<20s} {desc:<20s} {expected:<10s} "
              f"{v1_state:<10s}{v1_mark} {v2_strength:<15s}{v2_mark} {v2_score:>9.2f}")

    print(f"\n准确率:")
    print(f"  V1: {v1_correct}/{total} = {v1_correct/total*100:.1f}%")
    print(f"  V2: {v2_correct}/{total} = {v2_correct/total*100:.1f}%")
    print(f"  提升: {(v2_correct - v1_correct)/total*100:+.1f}%")

    # 按时间段统计
    print(f"\n{'='*80}")
    print("分时段准确率统计")
    print(f"{'='*80}")

    periods = [
        ('2023-03-01', '2024-12-31', '牛市期（预期BULL）', 'BULL'),
        ('2025-01-01', '2026-02-28', '熊市期（预期BEAR/RANGING）', 'BEAR'),
    ]

    for start_date, end_date, desc, expected_majority in periods:
        mask = (df['datetime'] >= start_date) & (df['datetime'] <= end_date)
        period_df = df[mask].copy()

        if len(period_df) == 0:
            continue

        # 每7天采样一次
        sample_indices = period_df.index[::168]

        v1_detections = []
        v2_detections = []

        for idx in sample_indices:
            if idx >= 180*24:  # V2需要180天数据
                v1_detections.append(detector_v1.detect(df, idx))
                v2_detections.append(detector_v2.detect(df, idx))

        # 统计
        v1_bull = v1_detections.count('BULL')
        v1_bear = v1_detections.count('BEAR')
        v1_ranging = v1_detections.count('RANGING')
        v1_total = len(v1_detections)

        v2_bull = v2_detections.count('BULL')
        v2_bear = v2_detections.count('BEAR')
        v2_ranging = v2_detections.count('RANGING')
        v2_total = len(v2_detections)

        print(f"\n{desc}:")
        print(f"  V1检测分布:")
        print(f"    BULL: {v1_bull} ({v1_bull/v1_total*100:.1f}%)")
        print(f"    BEAR: {v1_bear} ({v1_bear/v1_total*100:.1f}%)")
        print(f"    RANGING: {v1_ranging} ({v1_ranging/v1_total*100:.1f}%)")

        print(f"  V2检测分布:")
        print(f"    BULL: {v2_bull} ({v2_bull/v2_total*100:.1f}%)")
        print(f"    BEAR: {v2_bear} ({v2_bear/v2_total*100:.1f}%)")
        print(f"    RANGING: {v2_ranging} ({v2_ranging/v2_total*100:.1f}%)")

        # 判断准确率
        if '牛市期' in desc:
            v1_accuracy = v1_bull / v1_total * 100
            v2_accuracy = v2_bull / v2_total * 100
            print(f"\n  准确率（BULL识别率）:")
            print(f"    V1: {v1_accuracy:.1f}%")
            print(f"    V2: {v2_accuracy:.1f}%")
            print(f"    提升: {v2_accuracy - v1_accuracy:+.1f}%")

            if v2_accuracy >= 60:
                print(f"    ✅ V2达标（>60%）")
            else:
                print(f"    ⚠️  V2仍需优化")

    # 详细案例分析
    print(f"\n{'='*80}")
    print("关键误判案例分析")
    print(f"{'='*80}")

    problem_cases = [
        ('2023-05-12', '第一次误判'),
        ('2023-07-25', '牛市中误判为BEAR'),
        ('2024-04-29', '牛市顶部误判'),
    ]

    for date_str, desc in problem_cases:
        target_date = pd.to_datetime(date_str)
        idx = (df['datetime'] - target_date).abs().idxmin()

        v1_details = detector_v1.get_detection_details(df, idx)
        v2_details = detector_v2.get_detection_details(df, idx)

        print(f"\n{date_str} - {desc}:")
        print(f"  价格: {v2_details['current_price']:,.2f}")
        print(f"\n  V1检测:")
        print(f"    结果: {v1_details['market_state']}")
        print(f"    60天趋势: {v1_details['price_trend']:+.2%}")
        print(f"    ADX: {v1_details['adx']:.2f}")

        print(f"\n  V2检测:")
        print(f"    结果: {v2_details['market_state']}")
        print(f"    强度: {v2_details['trend_strength']}")
        print(f"    综合评分: {v2_details['comprehensive_score']:.2f}/10")
        print(f"    365天趋势: {v2_details['trend_365d']:+.2%}")
        print(f"    180天趋势: {v2_details['trend_180d']:+.2%}")
        print(f"    90天趋势: {v2_details['trend_90d']:+.2%}")
        print(f"    30天趋势: {v2_details['trend_30d']:+.2%}")

    # 总结
    print(f"\n{'='*80}")
    print("总结")
    print(f"{'='*80}")

    improvement = (v2_correct - v1_correct) / total * 100
    if improvement >= 15:
        print(f"\n✅ V2显著改进（+{improvement:.1f}%）")
    elif improvement >= 5:
        print(f"\n👍 V2有所改进（+{improvement:.1f}%）")
    elif improvement > 0:
        print(f"\n⚠️  V2略有改进（+{improvement:.1f}%），需继续优化")
    else:
        print(f"\n❌ V2未改进，需要调整策略")


if __name__ == '__main__':
    compare_detectors()
