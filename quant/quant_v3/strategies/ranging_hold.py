"""
RangingHold - 震荡市观望策略

在震荡市中不交易，保持观望
"""

from typing import Tuple, Literal

SignalType = Literal['HOLD']


class RangingHold:
    """震荡市观望策略

    策略逻辑：
    在震荡市中不交易，避免频繁进出被手续费消耗
    """

    def __init__(self):
        """初始化策略"""
        pass

    def generate_signal(self, df, index: int) -> Tuple[SignalType, float]:
        """生成交易信号

        在震荡市中总是返回HOLD

        Args:
            df: OHLCV数据
            index: 当前索引

        Returns:
            ('HOLD', 0.0)
        """
        return 'HOLD', 0.0

    def reset(self):
        """重置策略状态"""
        pass
