"""
诊断MarketDetector为什么无法正确识别牛市
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from data.fetcher import BinanceFetcher
from quant_v3.core.market_detector import MarketDetector
import pandas as pd


def diagnose():
    print("\n" + "="*80)
    print("MarketDetector 诊断")
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

    # 测试几个明显的牛市时期
    test_cases = [
        ('2023-12-01', '牛市高潮42k', 'BULL'),
        ('2024-03-01', '牛市延续64k', 'BULL'),
        ('2024-12-01', '新高92k', 'BULL'),
        ('2026-01-01', '熊市反弹94k', 'BEAR'),
    ]

    for date_str, desc, expected in test_cases:
        print(f"\n{'='*80}")
        print(f"{date_str} - {desc} (预期: {expected})")
        print(f"{'='*80}")

        # 找到最接近的索引
        target_date = pd.to_datetime(date_str)
        idx = (df['datetime'] - target_date).abs().idxmin()

        # 获取详细信息
        details = detector.get_detection_details(df, idx)

        print(f"\n价格: {details['current_price']:,.2f}")
        print(f"检测结果: {details['market_state']}")
        print(f"\n详细评分:")
        print(f"  价格趋势: {details['price_trend']:+.2%}")
        print(f"  EMA排列: {details['ema_alignment']}")
        print(f"  ADX: {details['adx']:.2f}")
        print(f"  价格极值: {details['price_extreme']}")

        # 手动计算评分
        bull_score = 0
        bear_score = 0

        # 价格趋势（权重：2）
        if details['price_trend'] > 0.10:
            bull_score += 2
            print(f"  ✓ 价格趋势 > 10%: +2 bull")
        elif details['price_trend'] < -0.10:
            bear_score += 2
            print(f"  ✓ 价格趋势 < -10%: +2 bear")
        else:
            print(f"  ✗ 价格趋势在±10%内: 无分")

        # 均线排列（权重：1）
        if details['ema_alignment'] > 0:
            bull_score += 1
            print(f"  ✓ EMA多头排列: +1 bull")
        elif details['ema_alignment'] < 0:
            bear_score += 1
            print(f"  ✓ EMA空头排列: +1 bear")
        else:
            print(f"  ✗ EMA无明显排列: 无分")

        # ADX强度（权重：1）
        if details['adx'] > 25.0:
            if bull_score > bear_score:
                bull_score += 1
                print(f"  ✓ ADX > 25 且bull领先: +1 bull")
            elif bear_score > bull_score:
                bear_score += 1
                print(f"  ✓ ADX > 25 且bear领先: +1 bear")
        else:
            print(f"  ✗ ADX < 25: 无强度加分")

        # 新高/新低（权重：1）
        if details['price_extreme'] > 0:
            bull_score += 1
            print(f"  ✓ 创新高: +1 bull")
        elif details['price_extreme'] < 0:
            bear_score += 1
            print(f"  ✓ 创新低: +1 bear")
        else:
            print(f"  ✗ 非新高/新低: 无分")

        print(f"\n最终评分:")
        print(f"  Bull: {bull_score}")
        print(f"  Bear: {bear_score}")

        # 弱趋势判断
        if details['adx'] < 15.0:
            print(f"  ⚠️  ADX < 15 → 强制RANGING")

        # 判断逻辑
        if details['adx'] < 15.0:
            final = 'RANGING'
        elif bull_score >= 3:
            final = 'BULL'
        elif bear_score >= 3:
            final = 'BEAR'
        else:
            final = 'RANGING'

        print(f"\n判断: {final}")

        if final != expected:
            print(f"❌ 错误！预期 {expected}，实际 {final}")
        else:
            print(f"✅ 正确")


if __name__ == '__main__':
    diagnose()
