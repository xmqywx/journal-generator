"""
波动率检测器
在买入时执行一次，判断币种的波动特性
"""
import pandas as pd
import numpy as np
from typing import Dict, Literal

VolatilityLevel = Literal['STABLE', 'MODERATE', 'HIGH']


class VolatilityDetector:
    """币种波动率检测器"""

    def __init__(self):
        """初始化检测器"""
        pass

    def calculate_volatility(self, df: pd.DataFrame) -> Dict:
        """
        计算币种波动率并分类

        Args:
            df: OHLCV数据，包含至少60天数据

        Returns:
            {
                'daily_volatility': 日均波动率,
                'weekly_volatility': 周均波动率,
                'atr_percentage': ATR百分比,
                'max_drawdown_speed': 最大单日跌幅,
                'volatility_level': 分类结果
            }
        """
        if len(df) < 60:
            raise ValueError("数据不足，需要至少60天数据计算波动率")

        # 1. 日波动率（过去30天）
        daily_changes = df['close'].pct_change().tail(30)
        daily_vol = daily_changes.abs().mean()

        # 2. 周波动率（过去12周）
        # 按周重采样
        df_copy = df.copy()
        df_copy['date'] = pd.to_datetime(df_copy['date'])
        df_copy.set_index('date', inplace=True)
        weekly_closes = df_copy['close'].resample('W').last()
        weekly_changes = weekly_closes.pct_change().tail(12)
        weekly_vol = weekly_changes.abs().mean()

        # 3. ATR波动率（过去14天）
        atr = self._calculate_atr(df, period=14)
        current_price = df['close'].iloc[-1]
        atr_pct = atr / current_price if current_price > 0 else 0

        # 4. 极端波动（最大单日跌幅，过去60天）
        max_drop = daily_changes.tail(60).min()

        # 5. 分类
        level = self._classify_volatility(
            daily_vol, weekly_vol, atr_pct, abs(max_drop)
        )

        return {
            'daily_volatility': float(daily_vol),
            'weekly_volatility': float(weekly_vol),
            'atr_percentage': float(atr_pct),
            'max_drawdown_speed': float(abs(max_drop)),
            'volatility_level': level
        }

    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """
        计算平均真实波幅（ATR）

        Args:
            df: OHLCV数据
            period: 计算周期

        Returns:
            ATR值
        """
        high = df['high']
        low = df['low']
        close = df['close']

        # True Range = max(high-low, abs(high-prev_close), abs(low-prev_close))
        prev_close = close.shift(1)
        tr1 = high - low
        tr2 = abs(high - prev_close)
        tr3 = abs(low - prev_close)

        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # ATR = TR的移动平均
        atr = tr.tail(period).mean()

        return float(atr)

    def _classify_volatility(
        self,
        daily_vol: float,
        weekly_vol: float,
        atr_pct: float,
        max_drop: float
    ) -> VolatilityLevel:
        """
        分类波动率级别

        分类标准：
        - STABLE: 日波动<3%, 周波动<5%, 最大跌幅<8%
        - HIGH: 日波动>5%, 周波动>10%, 最大跌幅>15%
        - MODERATE: 介于两者之间

        Args:
            daily_vol: 日波动率
            weekly_vol: 周波动率
            atr_pct: ATR百分比
            max_drop: 最大单日跌幅

        Returns:
            'STABLE' / 'MODERATE' / 'HIGH'
        """
        # STABLE判断（所有条件都满足）
        if (daily_vol < 0.03 and
            weekly_vol < 0.05 and
            max_drop < 0.08):
            return 'STABLE'

        # HIGH判断（任一条件满足）
        if (daily_vol > 0.05 or
            weekly_vol > 0.10 or
            max_drop > 0.15):
            return 'HIGH'

        # 其他情况为MODERATE
        return 'MODERATE'
