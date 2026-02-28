"""
BearMarketShort - 熊市做空策略

确认熊市后2倍杠杆满仓做空，持有到牛市信号或移动止损
目标：熊市期间实现70%+收益
"""

from typing import Tuple, Literal

SignalType = Literal['SHORT', 'CLOSE', 'HOLD']


class BearMarketShort:
    """熊市做空策略

    策略逻辑：
    1. 确认熊市（market_state == 'BEAR'）后满仓做空
    2. 使用2倍杠杆放大收益
    3. 15%移动止损（价格从最低点反弹超过15%时止损）
    4. 出现牛市信号时平仓
    """

    def __init__(self, leverage: float = 2.0, trailing_stop: float = 0.15):
        """
        Args:
            leverage: 杠杆倍数（默认2倍）
            trailing_stop: 移动止损比例（默认15%）
        """
        self.leverage = leverage
        self.trailing_stop = trailing_stop
        self.position = None  # 'SHORT' or None
        self.entry_price = 0.0
        self.lowest_price = 0.0  # 做空后的最低价（用于移动止损）

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
                - signal: 'SHORT', 'CLOSE', 'HOLD'
                - position_size: 仓位大小（杠杆倍数）
        """
        current_price = df['close'].iloc[index]

        # 无持仓且确认熊市
        if self.position is None and market_state == 'BEAR':
            self.position = 'SHORT'
            self.entry_price = current_price
            self.lowest_price = current_price  # 初始化为入场价
            return 'SHORT', self.leverage  # 满仓做空，2倍杠杆

        # 有持仓
        elif self.position == 'SHORT':
            # 更新最低价
            if current_price < self.lowest_price:
                self.lowest_price = current_price

            # 移动止损：价格从最低点反弹超过15%
            stop_price = self.lowest_price * (1 + self.trailing_stop)
            if current_price > stop_price:
                self.position = None
                return 'CLOSE', 1.0  # 止损平仓

            # 牛市信号出现，平仓
            if market_state == 'BULL':
                self.position = None
                return 'CLOSE', 1.0

        # 其他情况：持有或观望
        return 'HOLD', 0.0

    def reset(self):
        """重置策略状态"""
        self.position = None
        self.entry_price = 0.0
        self.lowest_price = 0.0
