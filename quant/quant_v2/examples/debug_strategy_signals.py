"""
直接调用策略的generate_signal方法，查看实际返回的信号
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from data.fetcher import BinanceFetcher
from quant_v2.strategies.multi_timeframe_trend import MultiTimeframeTrendStrategy
from quant_v2.core.market_regime import MarketRegime
import pandas as pd


def debug_signals():
    print("\n" + "="*80)
    print("策略信号调试")
    print("="*80)

    # 1. 加载数据
    print("\n加载数据...")
    fetcher = BinanceFetcher()
    df = fetcher.fetch_history('BTC-USDT', '1h', days=1095)

    if df.empty:
        print("❌ 数据下载失败")
        return

    print(f"✅ 成功加载 {len(df)} 条数据")

    # 2. 创建策略和市场环境识别器
    strategy = MultiTimeframeTrendStrategy(
        ema_fast=12,
        ema_slow=26,
        adx_threshold=25.0,
        volume_multiplier=1.2,
        trailing_stop_pct=0.03,
        max_holding_hours=168
    )

    market_regime = MarketRegime()

    # 3. 遍历所有K线，调用generate_signal
    print("\n检查策略信号生成...")

    buy_signals = []
    sell_signals = []
    close_signals = []

    for i in range(100, len(df)):  # 从第100根开始，避免指标不稳定
        regime = market_regime.identify(df, i)
        signal, strength = strategy.generate_signal(df, i, regime)

        if signal == 'BUY':
            buy_signals.append((i, df['close'].iloc[i], df['timestamp'].iloc[i], regime, strength))
        elif signal == 'SELL':
            sell_signals.append((i, df['close'].iloc[i], df['timestamp'].iloc[i], regime, strength))
        elif signal == 'CLOSE':
            close_signals.append((i, df['close'].iloc[i], df['timestamp'].iloc[i], regime))

    # 4. 显示结果
    print("\n" + "="*80)
    print("信号统计")
    print("="*80)

    print(f"\nBUY信号: {len(buy_signals)}")
    if len(buy_signals) > 0:
        print(f"前10个BUY信号:")
        for idx, price, timestamp, regime, strength in buy_signals[:10]:
            print(f"  [{idx}] {timestamp}: 价格={price:.2f}, 环境={regime}, 强度={strength:.2f}")

    print(f"\nSELL信号: {len(sell_signals)}")
    if len(sell_signals) > 0:
        print(f"前10个SELL信号:")
        for idx, price, timestamp, regime, strength in sell_signals[:10]:
            print(f"  [{idx}] {timestamp}: 价格={price:.2f}, 环境={regime}, 强度={strength:.2f}")

    print(f"\nCLOSE信号: {len(close_signals)}")
    if len(close_signals) > 0:
        print(f"前10个CLOSE信号:")
        for idx, price, timestamp, regime in close_signals[:10]:
            print(f"  [{idx}] {timestamp}: 价格={price:.2f}, 环境={regime}")

    # 5. 分析
    print("\n" + "="*80)
    print("分析")
    print("="*80)

    if len(buy_signals) == 0 and len(sell_signals) == 0:
        print("\n❌ 没有产生任何BUY/SELL信号！")
        print("\n可能原因:")
        print("  1. 检查策略代码逻辑")
        print("  2. 检查regime参数传递")
        print("  3. 检查各个过滤条件")

        # 手动检查一个应该满足条件的点
        print("\n手动检查第1000根K线:")
        test_idx = 1000
        regime = market_regime.identify(df, test_idx)
        print(f"  索引: {test_idx}")
        print(f"  时间: {df['timestamp'].iloc[test_idx]}")
        print(f"  价格: {df['close'].iloc[test_idx]:.2f}")
        print(f"  环境: {regime}")

        signal, strength = strategy.generate_signal(df, test_idx, regime)
        print(f"  信号: {signal}")
        print(f"  强度: {strength:.2f}")

    else:
        print(f"\n✅ 产生了 {len(buy_signals)} 个BUY信号和 {len(sell_signals)} 个SELL信号")
        print(f"   但回测结果显示0笔交易，说明问题在回测引擎中")


if __name__ == '__main__':
    debug_signals()
