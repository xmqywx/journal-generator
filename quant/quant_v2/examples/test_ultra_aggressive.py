"""
测试极度激进的参数配置
目标：3年150%+收益
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from data.fetcher import BinanceFetcher
import pandas as pd


class UltraAggressiveTrendStrategy:
    """极度激进策略"""

    def __init__(self):
        self.ema_fast = 8   # 更快
        self.ema_slow = 21  # 更快
        self.adx_threshold = 15.0  # 更低
        self.trailing_stop_pct = 0.15  # 更宽
        self.max_holding_hours = 2160  # 90天

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

            # 止损
            if current_price < stop_price:
                self.position = None
                return 'CLOSE'

            # 最大持仓
            if index - self.entry_time >= self.max_holding_hours:
                self.position = None
                return 'CLOSE'

            # EMA反转
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

        # 简化条件：EMA上升 + ADX > 15
        if (current_price > ema_fast.iloc[index] > ema_slow.iloc[index] and
            adx.iloc[index] > self.adx_threshold):

            self.position = 'LONG'
            self.entry_price = current_price
            self.entry_time = index
            self.highest_price = current_price
            return 'BUY'

        return 'HOLD'


def backtest_ultra_aggressive():
    print("\n" + "="*80)
    print("极度激进策略回测")
    print("="*80)

    # 加载数据
    fetcher = BinanceFetcher()
    df = fetcher.fetch_history('BTC-USDT', '1h', days=1095)

    print(f"\n数据: {len(df)}条")
    print(f"BTC: {df['close'].iloc[0]:.2f} → {df['close'].iloc[-1]:.2f} ({(df['close'].iloc[-1]/df['close'].iloc[0]-1)*100:.2f}%)")

    # 参数
    print(f"\n策略参数:")
    print(f"  EMA: 8/21（更快）")
    print(f"  ADX阈值: 15（更低）")
    print(f"  止损: 15%（更宽）")
    print(f"  最大持仓: 90天（更长）")
    print(f"  仓位: 80%（更大）")

    # 策略
    strategy = UltraAggressiveTrendStrategy()

    # 回测
    capital = 10000
    position_size = 0
    trades = []

    for i in range(100, len(df)):
        signal = strategy.generate_signal(df, i)
        price = df['close'].iloc[i]

        if signal == 'BUY':
            position_size = (capital * 0.8) / price  # 80%仓位
            trades.append({
                'action': 'BUY',
                'price': price,
                'size': position_size,
                'timestamp': df['timestamp'].iloc[i]
            })

        elif signal == 'CLOSE' and position_size > 0:
            pnl = position_size * (price - trades[-1]['price']) * 0.9992  # 扣除手续费
            capital += pnl

            trades.append({
                'action': 'CLOSE',
                'price': price,
                'size': position_size,
                'pnl': pnl,
                'timestamp': df['timestamp'].iloc[i]
            })

            position_size = 0

    # 统计
    total_trades = len([t for t in trades if 'pnl' in t])
    winning_trades = len([t for t in trades if t.get('pnl', 0) > 0])
    losing_trades = len([t for t in trades if t.get('pnl', 0) < 0])
    total_return = (capital - 10000) / 10000

    print(f"\n{'='*80}")
    print("回测结果")
    print(f"{'='*80}")

    print(f"\n收益:")
    print(f"  初始: 10,000 USDT")
    print(f"  最终: {capital:,.2f} USDT")
    print(f"  收益: {total_return*100:+.2f}%")
    print(f"  年化: {(total_return/3)*100:+.2f}%")

    print(f"\n交易:")
    print(f"  总数: {total_trades}")
    if total_trades > 0:
        print(f"  盈利: {winning_trades} ({winning_trades/total_trades*100:.1f}%)")
        print(f"  亏损: {losing_trades} ({losing_trades/total_trades*100:.1f}%)")

        # 前10笔
        print(f"\n前10笔交易:")
        exit_trades = [t for t in trades if 'pnl' in t][:10]
        for i, trade in enumerate(exit_trades):
            print(f"  {i+1:2d}. [{pd.to_datetime(trade['timestamp'], unit='ms')}] "
                  f"CLOSE @ {trade['price']:>10,.2f}, PnL: {trade['pnl']:>+12,.2f}")

        # 最大盈利/亏损
        max_win = max([t.get('pnl', 0) for t in trades])
        max_loss = min([t.get('pnl', 0) for t in trades])
        print(f"\n最大单笔盈利: {max_win:+,.2f} USDT")
        print(f"最大单笔亏损: {max_loss:+,.2f} USDT")

    # 对比
    print(f"\n{'='*80}")
    print("对比之前的策略")
    print(f"{'='*80}")
    print(f"\n原始MultiTrend（有MarketRegime）: +5.56%")
    print(f"简化版（无MarketRegime）: +19.79%")
    print(f"极度激进版: {total_return*100:+.2f}%")

    if total_return >= 1.50:
        print(f"\n✅ 达到150%目标！")
    else:
        print(f"\n距离150%目标还差: {(1.50-total_return)*100:.2f}%")

    # 买入持有对比
    buy_hold_return = (df['close'].iloc[-1] / df['close'].iloc[100] - 1) * 100
    print(f"\n买入持有（从第100条开始）: {buy_hold_return:+.2f}%")
    print(f"策略 vs 买入持有: {total_return*100 - buy_hold_return:+.2f}%")


if __name__ == '__main__':
    backtest_ultra_aggressive()
