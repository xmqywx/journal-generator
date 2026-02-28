"""
测试移除MarketRegime限制后的MultiTimeframeTrend表现
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from data.fetcher import BinanceFetcher
import pandas as pd
import numpy as np


class SimplifiedTrendStrategy:
    """简化版趋势策略：移除MarketRegime依赖"""

    def __init__(
        self,
        ema_fast: int = 12,
        ema_slow: int = 26,
        adx_threshold: float = 20.0,
        volume_multiplier: float = 1.05,
        trailing_stop_pct: float = 0.10,
        max_holding_hours: int = 720
    ):
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.adx_threshold = adx_threshold
        self.volume_multiplier = volume_multiplier
        self.trailing_stop_pct = trailing_stop_pct
        self.max_holding_hours = max_holding_hours

        self.position = None
        self.entry_price = 0
        self.entry_time = 0
        self.highest_price = 0
        self.lowest_price = 0

    def _calculate_ema(self, series, period):
        return series.ewm(span=period, adjust=False).mean()

    def _calculate_adx(self, df, period=14):
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

        # Wilder's smoothing
        atr = tr.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
        plus_di = 100 * (plus_dm.ewm(alpha=1/period, min_periods=period, adjust=False).mean() / atr)
        minus_di = 100 * (minus_dm.ewm(alpha=1/period, min_periods=period, adjust=False).mean() / atr)

        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.ewm(alpha=1/period, min_periods=period, adjust=False).mean()

        return adx

    def generate_signal(self, df, index):
        """生成交易信号"""
        if index < max(self.ema_slow, 50):
            return 'HOLD'

        current_price = df['close'].iloc[index]

        # 如果有持仓，检查退出
        if self.position is not None:
            # 更新最高/最低价
            if self.position == 'LONG':
                self.highest_price = max(self.highest_price, current_price)
                # 移动止损
                stop_price = self.highest_price * (1 - self.trailing_stop_pct)
                if current_price < stop_price:
                    self.position = None
                    return 'CLOSE'
            else:  # SHORT
                self.lowest_price = min(self.lowest_price, current_price)
                stop_price = self.lowest_price * (1 + self.trailing_stop_pct)
                if current_price > stop_price:
                    self.position = None
                    return 'CLOSE'

            # 最大持仓时间
            if index - self.entry_time >= self.max_holding_hours:
                self.position = None
                return 'CLOSE'

            # EMA反转
            ema_fast = self._calculate_ema(df['close'], self.ema_fast)
            ema_slow = self._calculate_ema(df['close'], self.ema_slow)
            if self.position == 'LONG' and ema_fast.iloc[index] < ema_slow.iloc[index]:
                self.position = None
                return 'CLOSE'
            elif self.position == 'SHORT' and ema_fast.iloc[index] > ema_slow.iloc[index]:
                self.position = None
                return 'CLOSE'

            return 'HOLD'

        # 无持仓，检查入场
        ema_fast = self._calculate_ema(df['close'], self.ema_fast)
        ema_slow = self._calculate_ema(df['close'], self.ema_slow)
        adx = self._calculate_adx(df)

        # 1. EMA趋势
        if current_price > ema_fast.iloc[index] > ema_slow.iloc[index]:
            ema_trend = 'UP'
        elif current_price < ema_fast.iloc[index] < ema_slow.iloc[index]:
            ema_trend = 'DOWN'
        else:
            return 'HOLD'

        # 2. EMA持续
        if ema_trend == 'UP':
            if not all(ema_fast.iloc[index-i] > ema_slow.iloc[index-i] for i in range(3)):
                return 'HOLD'
        else:
            if not all(ema_fast.iloc[index-i] < ema_slow.iloc[index-i] for i in range(3)):
                return 'HOLD'

        # 3. ADX确认
        if adx.iloc[index] <= self.adx_threshold:
            return 'HOLD'

        # 4. 成交量确认
        volume_ma = df['volume'].rolling(window=20).mean()
        if df['volume'].iloc[index] < volume_ma.iloc[index] * self.volume_multiplier:
            return 'HOLD'

        # 所有条件满足，买入
        if ema_trend == 'UP':
            self.position = 'LONG'
            self.entry_price = current_price
            self.entry_time = index
            self.highest_price = current_price
            return 'BUY'
        else:
            self.position = 'SHORT'
            self.entry_price = current_price
            self.entry_time = index
            self.lowest_price = current_price
            return 'SELL'


def backtest_simplified():
    """回测简化策略"""
    print("\n" + "="*80)
    print("简化趋势策略回测（移除MarketRegime限制）")
    print("="*80)

    # 加载数据
    fetcher = BinanceFetcher()
    df = fetcher.fetch_history('BTC-USDT', '1h', days=1095)

    print(f"\n数据: {len(df)}条")
    print(f"BTC: {df['close'].iloc[0]:.2f} → {df['close'].iloc[-1]:.2f}")
    print(f"涨幅: {(df['close'].iloc[-1]/df['close'].iloc[0]-1)*100:.2f}%")

    # 创建策略
    strategy = SimplifiedTrendStrategy(
        ema_fast=12,
        ema_slow=26,
        adx_threshold=20.0,
        volume_multiplier=1.05,
        trailing_stop_pct=0.10,
        max_holding_hours=720
    )

    # 手动回测
    capital = 10000
    position_size = 0
    trades = []

    for i in range(100, len(df)):
        signal = strategy.generate_signal(df, i)
        price = df['close'].iloc[i]

        if signal == 'BUY':
            # 使用40%仓位
            position_size = (capital * 0.4) / price
            trades.append({
                'action': 'BUY',
                'price': price,
                'size': position_size,
                'timestamp': df['timestamp'].iloc[i]
            })

        elif signal == 'SELL' and position_size > 0:
            # 卖出
            pnl = position_size * (price - trades[-1]['price'])
            capital += pnl

            trades.append({
                'action': 'SELL',
                'price': price,
                'size': position_size,
                'pnl': pnl,
                'timestamp': df['timestamp'].iloc[i]
            })

            position_size = 0

        elif signal == 'CLOSE' and position_size > 0:
            # 平仓
            pnl = position_size * (price - trades[-1]['price'])
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
    print(f"  盈利: {winning_trades} ({winning_trades/total_trades*100:.1f}%)" if total_trades > 0 else "  无交易")

    if total_trades > 0:
        print(f"\n前10笔交易:")
        exit_trades = [t for t in trades if 'pnl' in t][:10]
        for i, trade in enumerate(exit_trades):
            print(f"  {i+1}. [{pd.to_datetime(trade['timestamp'], unit='ms')}] "
                  f"{trade['action']:<6s} @ {trade['price']:>10,.2f}, PnL: {trade['pnl']:>+10,.2f}")

    # 对比
    print(f"\n{'='*80}")
    print("对比")
    print(f"{'='*80}")
    print(f"\n原始策略（有MarketRegime限制）: +5.56%")
    print(f"简化策略（无MarketRegime限制）: {total_return*100:+.2f}%")
    print(f"改进: {(total_return*100-5.56):+.2f}%")

    if total_return >= 1.50:
        print(f"\n✅ 达到150%目标！")
    else:
        print(f"\n⚠️  距离150%目标还差: {(1.50-total_return)*100:.2f}%")


if __name__ == '__main__':
    backtest_simplified()
