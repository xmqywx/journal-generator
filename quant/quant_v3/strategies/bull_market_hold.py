"""
BullMarketHold - 牛市买入持有策略

确认牛市后2倍杠杆满仓买入，持有到熊市信号
目标：牛市期间实现400%+收益
"""

from typing import Tuple, Literal

SignalType = Literal['BUY', 'SELL', 'HOLD']


class BullMarketHold:
    """牛市买入持有策略

    策略逻辑：
    1. 确认牛市（market_state == 'BULL'）后满仓买入
    2. 使用2倍杠杆放大收益
    3. 持有直到出现熊市信号
    4. 不做频繁交易，避免错过主升浪
    """

    def __init__(self, leverage: float = 2.0):
        """
        Args:
            leverage: 杠杆倍数（默认2倍）
        """
        self.leverage = leverage
        self.position = None  # 'LONG' or None
        self.entry_price = 0.0

    def generate_signal(
        self,
        df,
        index: int,
        market_state: Literal['BULL', 'BEAR', 'RANGING']
    ) -> Tuple[SignalType, float]:
        """生成交易信号

        Args:
            df: OHLCV数据
            index: 当前索引
            market_state: 市场状态（由MarketDetector提供）

        Returns:
            (signal, position_size):
                - signal: 'BUY', 'SELL', 'HOLD'
                - position_size: 仓位大小（杠杆倍数）
        """
        current_price = df['close'].iloc[index]

        # 无持仓且确认牛市
        if self.position is None and market_state == 'BULL':
            self.position = 'LONG'
            self.entry_price = current_price
            return 'BUY', self.leverage  # 满仓买入，2倍杠杆

        # 有持仓但出现熊市信号
        elif self.position == 'LONG' and market_state == 'BEAR':
            self.position = None
            return 'SELL', 1.0  # 全部卖出

        # 其他情况：持有或观望
        return 'HOLD', 0.0

    def reset(self):
        """重置策略状态"""
        self.position = None
        self.entry_price = 0.0
