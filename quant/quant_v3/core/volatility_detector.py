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

    # 币种映射表（基于历史经验）
    SYMBOL_MAPPING = {
        # 稳定型（蓝筹币）
        'BTC': 'STABLE',
        'BTCUSDT': 'STABLE',
        'BTC-USDT': 'STABLE',
        'ETH': 'STABLE',
        'ETHUSDT': 'STABLE',
        'ETH-USDT': 'STABLE',

        # 高波动型（山寨币）
        'SOL': 'HIGH',
        'SOLUSDT': 'HIGH',
        'SOL-USDT': 'HIGH',
        'DOGE': 'HIGH',
        'DOGEUSDT': 'HIGH',
        'DOGE-USDT': 'HIGH',
        'SHIB': 'HIGH',
        'SHIBUSDT': 'HIGH',
        'ADA': 'HIGH',
        'ADAUSDT': 'HIGH',
        'ADA-USDT': 'HIGH',

        # 中等波动型（主流币）
        'BNB': 'MODERATE',
        'BNBUSDT': 'MODERATE',
        'BNB-USDT': 'MODERATE',
        'XRP': 'MODERATE',
        'XRPUSDT': 'MODERATE',
        'XRP-USDT': 'MODERATE',
    }

    def __init__(self):
        """初始化检测器"""
        pass

    def calculate_volatility(self, df: pd.DataFrame, symbol: str = None) -> Dict:
        """
        计算币种波动率并分类

        Args:
            df: OHLCV数据，包含至少60天数据
            symbol: 交易对符号（可选，如果提供则优先使用映射表）

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

        # 优先使用币种映射表
        if symbol and symbol in self.SYMBOL_MAPPING:
            level_from_map = self.SYMBOL_MAPPING[symbol]
            print(f"[VOLATILITY] {symbol} 使用映射表分类: {level_from_map}")
        else:
            level_from_map = None

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

        # 5. 分类（优先使用映射表）
        if level_from_map:
            level = level_from_map
        else:
            level = self._classify_volatility(
                daily_vol, weekly_vol, atr_pct, abs(max_drop)
            )
            print(f"[VOLATILITY] 使用计算分类: {level} (日波动={daily_vol:.4f}, 周波动={weekly_vol:.4f}, ATR%={atr_pct:.4f}, 最大跌幅={abs(max_drop):.4f})")

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
        分类波动率级别（改进版）

        分类标准（评分制）：
        - 计算综合波动分数（0-3分）
        - STABLE: 分数 <= 1（低波动）
        - MODERATE: 分数 = 2（中波动）
        - HIGH: 分数 >= 3（高波动）

        Args:
            daily_vol: 日波动率
            weekly_vol: 周波动率
            atr_pct: ATR百分比
            max_drop: 最大单日跌幅

        Returns:
            'STABLE' / 'MODERATE' / 'HIGH'
        """
        # 改用评分制，避免单一指标过度影响
        score = 0

        # 日波动评分
        if daily_vol > 0.06:      # >6%
            score += 2
        elif daily_vol > 0.04:    # 4-6%
            score += 1

        # 周波动评分
        if weekly_vol > 0.12:     # >12%
            score += 2
        elif weekly_vol > 0.08:   # 8-12%
            score += 1

        # 最大跌幅评分
        if max_drop > 0.20:       # >20%
            score += 2
        elif max_drop > 0.12:     # 12-20%
            score += 1

        # ATR评分
        if atr_pct > 0.08:        # >8%
            score += 1

        # 根据总分分类
        if score <= 1:
            return 'STABLE'
        elif score >= 5:
            return 'HIGH'
        else:
            return 'MODERATE'
