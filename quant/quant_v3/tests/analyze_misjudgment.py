"""
分析MarketDetector在牛市期间的误判
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from data.fetcher import BinanceFetcher
from quant_v3.core.market_detector import MarketDetector
import pandas as pd


def analyze():
    print("\n" + "="*80)
    print("分析牛市期间的BEAR误判")
    print("="*80)

    # 加载数据
    fetcher = BinanceFetcher()
    df = fetcher.fetch_history('BTC-USDT', '1h', days=1095)
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')

    # 筛选牛市期间
    mask = (df['datetime'] >= '2023-03-01') & (df['datetime'] <= '2024-12-31')
    bull_period = df[mask].reset_index(drop=True)

    detector = MarketDetector(
        lookback_days=60,
        trend_threshold=0.10,
        adx_threshold_strong=25.0,
        adx_threshold_weak=15.0
    )

    # 检测所有时间点
    bear_periods = []
    for i in range(100, len(bull_period)):
        state = detector.detect(bull_period, i)
        if state == 'BEAR':
            bear_periods.append({
                'index': i,
                'datetime': bull_period['datetime'].iloc[i],
                'price': bull_period['close'].iloc[i],
                'details': detector.get_detection_details(bull_period, i)
            })

    print(f"\n牛市期间被误判为BEAR的时间点: {len(bear_periods)}")
    print(f"牛市总时长: {len(bull_period)} 小时")
    print(f"误判比例: {len(bear_periods) / len(bull_period) * 100:.1f}%")

    # 显示前20个误判点
    print(f"\n前20个BEAR误判点:")
    print(f"{'时间':<20s} {'价格':<12s} {'趋势':<10s} {'EMA':<10s} {'ADX':<10s} {'极值':<10s}")
    print("-" * 80)

    for i, bp in enumerate(bear_periods[:20]):
        d = bp['details']
        print(f"{str(bp['datetime']):<20s} {bp['price']:>11,.2f} "
              f"{d['price_trend']:>+9.2%} {d['ema_alignment']:>9.1f} "
              f"{d['adx']:>9.2f} {d['price_extreme']:>9.1f}")

    # 分析误判的原因
    print(f"\n误判原因分析:")

    trend_bear = sum(1 for bp in bear_periods if bp['details']['price_trend'] < -0.10)
    ema_bear = sum(1 for bp in bear_periods if bp['details']['ema_alignment'] < 0)
    extreme_low = sum(1 for bp in bear_periods if bp['details']['price_extreme'] < 0)

    print(f"  价格趋势<-10%: {trend_bear} ({trend_bear/len(bear_periods)*100:.1f}%)")
    print(f"  EMA空头排列: {ema_bear} ({ema_bear/len(bear_periods)*100:.1f}%)")
    print(f"  创新低: {extreme_low} ({extreme_low/len(bear_periods)*100:.1f}%)")

    # 关键误判时间点
    print(f"\n关键时间点误判检查:")

    key_points = [
        ('2023-07-25', '第一次误判BEAR（导致卖出并做空）'),
        ('2024-01-19', '第二次误判BEAR（导致巨额亏损）'),
    ]

    for date_str, desc in key_points:
        target_date = pd.to_datetime(date_str)
        idx = (bull_period['datetime'] - target_date).abs().idxmin()

        details = detector.get_detection_details(bull_period, idx)
        state = details['market_state']

        print(f"\n{date_str} - {desc}:")
        print(f"  检测结果: {state}")
        print(f"  价格: {details['current_price']:,.2f}")
        print(f"  60天趋势: {details['price_trend']:+.2%}")
        print(f"  EMA排列: {details['ema_alignment']}")
        print(f"  ADX: {details['adx']:.2f}")
        print(f"  极值: {details['price_extreme']}")


if __name__ == '__main__':
    analyze()
