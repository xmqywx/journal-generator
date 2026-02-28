"""
测试2025-2026年的策略表现
这段时间可能不是主升浪，更适合量化策略
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from data.fetcher import BinanceFetcher
import pandas as pd
import numpy as np


class UltraAggressiveTrendStrategy:
    """极度激进策略"""

    def __init__(self):
        self.ema_fast = 8
        self.ema_slow = 21
        self.adx_threshold = 15.0
        self.trailing_stop_pct = 0.15
        self.max_holding_hours = 2160

        self.position = None
        self.entry_price = 0
        self.entry_time = 0
        self.highest_price = 0

    def _calculate_ema(self, series, period):
        return series.ewm(span=period, adjust=False).mean()

    def _calculate_adx(self, df, period=14):
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

        atr = tr.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
        plus_di = 100 * (plus_dm.ewm(alpha=1/period, min_periods=period, adjust=False).mean() / atr)
        minus_di = 100 * (minus_dm.ewm(alpha=1/period, min_periods=period, adjust=False).mean() / atr)

        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.ewm(alpha=1/period, min_periods=period, adjust=False).mean()

        return adx

    def generate_signal(self, df, index):
        if index < 50:
            return 'HOLD'

        current_price = df['close'].iloc[index]

        # 持仓检查
        if self.position == 'LONG':
            self.highest_price = max(self.highest_price, current_price)
            stop_price = self.highest_price * (1 - self.trailing_stop_pct)

            if current_price < stop_price:
                self.position = None
                return 'CLOSE'

            if index - self.entry_time >= self.max_holding_hours:
                self.position = None
                return 'CLOSE'

            ema_fast = self._calculate_ema(df['close'], self.ema_fast)
            ema_slow = self._calculate_ema(df['close'], self.ema_slow)
            if ema_fast.iloc[index] < ema_slow.iloc[index]:
                self.position = None
                return 'CLOSE'

            return 'HOLD'

        # 无持仓，检查买入
        ema_fast = self._calculate_ema(df['close'], self.ema_fast)
        ema_slow = self._calculate_ema(df['close'], self.ema_slow)
        adx = self._calculate_adx(df)

        if (current_price > ema_fast.iloc[index] > ema_slow.iloc[index] and
            adx.iloc[index] > self.adx_threshold):

            self.position = 'LONG'
            self.entry_price = current_price
            self.entry_time = index
            self.highest_price = current_price
            return 'BUY'

        return 'HOLD'


def test_period(start_date, end_date, position_pct=0.8):
    """测试指定时间段"""
    print("\n" + "="*80)
    print(f"测试期间: {start_date} - {end_date}")
    print("="*80)

    # 加载数据
    fetcher = BinanceFetcher()
    df = fetcher.fetch_history('BTC-USDT', '1h', days=1095)

    # 转换timestamp为datetime
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')

    # 筛选时间段
    mask = (df['datetime'] >= start_date) & (df['datetime'] <= end_date)
    df_period = df[mask].reset_index(drop=True)

    if len(df_period) == 0:
        print("❌ 没有该时间段的数据")
        return None

    print(f"\n数据统计:")
    print(f"  数据量: {len(df_period)} 条")
    print(f"  开始: {df_period['datetime'].iloc[0]}")
    print(f"  结束: {df_period['datetime'].iloc[-1]}")
    print(f"  价格: {df_period['close'].iloc[0]:.2f} → {df_period['close'].iloc[-1]:.2f}")

    price_change = (df_period['close'].iloc[-1] / df_period['close'].iloc[0] - 1) * 100
    print(f"  涨跌幅: {price_change:+.2f}%")

    # 策略回测
    strategy = UltraAggressiveTrendStrategy()

    capital = 10000
    position_size = 0
    trades = []

    for i in range(100, len(df_period)):
        signal = strategy.generate_signal(df_period, i)
        price = df_period['close'].iloc[i]

        if signal == 'BUY':
            position_size = (capital * position_pct) / price
            trades.append({
                'action': 'BUY',
                'price': price,
                'size': position_size,
                'timestamp': df_period['datetime'].iloc[i]
            })

        elif signal == 'CLOSE' and position_size > 0:
            pnl = position_size * (price - trades[-1]['price']) * 0.9992
            capital += pnl

            trades.append({
                'action': 'CLOSE',
                'price': price,
                'size': position_size,
                'pnl': pnl,
                'timestamp': df_period['datetime'].iloc[i]
            })

            position_size = 0

    # 统计
    total_trades = len([t for t in trades if 'pnl' in t])
    winning_trades = len([t for t in trades if t.get('pnl', 0) > 0])
    total_return = (capital - 10000) / 10000

    print(f"\n{'='*80}")
    print("回测结果")
    print(f"{'='*80}")

    print(f"\n收益:")
    print(f"  初始: 10,000 USDT")
    print(f"  最终: {capital:,.2f} USDT")
    print(f"  收益: {total_return*100:+.2f}%")

    print(f"\n交易:")
    print(f"  总数: {total_trades}")
    if total_trades > 0:
        print(f"  盈利: {winning_trades} ({winning_trades/total_trades*100:.1f}%)")

        # 前10笔
        print(f"\n前10笔交易:")
        exit_trades = [t for t in trades if 'pnl' in t][:10]
        for i, trade in enumerate(exit_trades):
            print(f"  {i+1:2d}. [{trade['timestamp']}] CLOSE @ {trade['price']:>10,.2f}, PnL: {trade['pnl']:>+12,.2f}")

    # 对比买入持有
    buy_hold_return = (df_period['close'].iloc[-1] / df_period['close'].iloc[100] - 1) * 100
    print(f"\n对比:")
    print(f"  买入持有: {buy_hold_return:+.2f}%")
    print(f"  策略: {total_return*100:+.2f}%")
    print(f"  差异: {total_return*100 - buy_hold_return:+.2f}%")

    if total_return*100 > buy_hold_return:
        print(f"\n✅ 策略跑赢买入持有！")
    else:
        print(f"\n❌ 策略跑输买入持有")

    return {
        'period': f"{start_date} - {end_date}",
        'data_points': len(df_period),
        'price_change': price_change,
        'strategy_return': total_return * 100,
        'buy_hold_return': buy_hold_return,
        'trades': total_trades,
        'win_rate': winning_trades/total_trades*100 if total_trades > 0 else 0
    }


def main():
    print("\n" + "🚀" * 40)
    print("分时段策略表现测试")
    print("🚀" * 40)

    results = []

    # 测试不同时间段
    results.append(test_period('2023-03-01', '2023-12-31', position_pct=0.8))  # 2023年
    results.append(test_period('2024-01-01', '2024-12-31', position_pct=0.8))  # 2024年
    results.append(test_period('2025-01-01', '2026-02-28', position_pct=0.8))  # 2025-2026年

    # 总结对比
    print("\n" + "="*80)
    print("分时段对比总结")
    print("="*80)

    print(f"\n{'时期':<30s} {'BTC涨跌':<12s} {'策略收益':<12s} {'买入持有':<12s} {'差异':<12s} {'交易数':<10s}")
    print("-" * 90)

    for r in results:
        if r:
            diff = r['strategy_return'] - r['buy_hold_return']
            print(f"{r['period']:<30s} {r['price_change']:>+10.2f}% {r['strategy_return']:>+10.2f}% "
                  f"{r['buy_hold_return']:>+10.2f}% {diff:>+10.2f}% {r['trades']:>9d}")

    # 分析
    print("\n" + "="*80)
    print("关键发现")
    print("="*80)

    print(f"\n观察:")
    print(f"  • 2023年（主升浪）: 策略 vs 买入持有")
    print(f"  • 2024年（continuation）: 策略 vs 买入持有")
    print(f"  • 2025-2026年（震荡/回调?）: 策略 vs 买入持有")

    print(f"\n结论:")
    print(f"  如果2025-2026年策略跑赢买入持有，说明量化策略适合震荡市")
    print(f"  如果依然跑输，说明策略本身有问题，需要重新设计")


if __name__ == '__main__':
    main()
