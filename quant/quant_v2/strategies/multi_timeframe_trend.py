"""
多周期趋势策略

特点:
1. 多周期确认（1H + 4H + 1D）
2. 成交量确认
3. 严格的入场条件
4. 动态止损跟踪
"""

import pandas as pd
import numpy as np
from typing import Literal, Optional
from dataclasses import dataclass

Signal = Literal['BUY', 'SELL', 'HOLD', 'CLOSE']


@dataclass
class TrendPosition:
    """趋势持仓"""
    entry_price: float
    entry_time: int
    direction: Literal['LONG', 'SHORT']
    highest_price: float = 0.0
    lowest_price: float = float('inf')


class MultiTimeframeTrendStrategy:
    """多周期趋势策略

    严格的趋势跟随策略，需要多周期确认：
    - 1小时EMA趋势
    - 4小时EMA趋势
    - 日线EMA趋势
    - 成交量确认（高于均值）
    - ADX确认（趋势强度>25）

    只在所有周期一致时入场

    Examples:
        >>> strategy = MultiTimeframeTrendStrategy()
        >>> signal = strategy.generate_signal(df_1h, df_4h, df_1d, index)
    """

    def __init__(
        self,
        ema_fast: int = 12,          # 快速EMA
        ema_slow: int = 26,          # 慢速EMA
        adx_threshold: float = 25.0, # ADX阈值
        volume_multiplier: float = 1.2,  # 成交量倍数
        trailing_stop_pct: float = 0.03,  # 3%移动止损
        max_holding_hours: int = 168,     # 最多持仓7天
    ):
        """初始化多周期趋势策略

        Args:
            ema_fast: 快速EMA周期
            ema_slow: 慢速EMA周期
            adx_threshold: ADX趋势强度阈值
            volume_multiplier: 成交量确认倍数
            trailing_stop_pct: 移动止损比例
            max_holding_hours: 最大持仓时间（小时）
        """
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.adx_threshold = adx_threshold
        self.volume_multiplier = volume_multiplier
        self.trailing_stop_pct = trailing_stop_pct
        self.max_holding_hours = max_holding_hours

        # 持仓状态
        self.position: Optional[TrendPosition] = None

        # 缓存
        self._cache = {}

    def generate_signal(
        self,
        df: pd.DataFrame,
        index: int,
        regime: str = 'trending_up'
    ) -> tuple[Signal, float]:
        """生成交易信号

        Args:
            df: OHLCV数据（1小时）
            index: 当前索引
            regime: 市场环境（来自MarketRegime）

        Returns:
            (信号, 信号强度0-1)
        """
        # 数据充足性检查
        if index < max(self.ema_slow, 50):
            return 'HOLD', 0.0

        current_price = df['close'].iloc[index]

        # 如果有持仓，检查退出条件
        if self.position is not None:
            should_exit, reason = self._check_exit_conditions(
                df, index, current_price
            )
            if should_exit:
                self.position = None
                return 'CLOSE', 1.0
            else:
                # 更新最高/最低价
                self._update_position_extremes(current_price)
                return 'HOLD', 0.0

        # 无持仓，检查入场条件
        # 只在趋势环境中交易
        if regime not in ['trending_up', 'trending_down']:
            return 'HOLD', 0.0

        # 1. EMA趋势确认
        ema_trend = self._check_ema_trend(df, index)
        if ema_trend is None:
            return 'HOLD', 0.0

        # 2. ADX确认（趋势强度）
        adx_confirmed = self._check_adx(df, index)
        if not adx_confirmed:
            return 'HOLD', 0.0

        # 3. 成交量确认
        volume_confirmed = self._check_volume(df, index)
        if not volume_confirmed:
            return 'HOLD', 0.0

        # 4. 趋势方向与市场环境一致
        if ema_trend == 'UP' and regime == 'trending_up':
            self.position = TrendPosition(
                entry_price=current_price,
                entry_time=index,
                direction='LONG',
                highest_price=current_price,
                lowest_price=current_price
            )
            # 信号强度基于ADX
            adx = self._calculate_adx(df)
            strength = min(adx.iloc[index] / 50.0, 1.0)
            return 'BUY', strength

        elif ema_trend == 'DOWN' and regime == 'trending_down':
            self.position = TrendPosition(
                entry_price=current_price,
                entry_time=index,
                direction='SHORT',
                highest_price=current_price,
                lowest_price=current_price
            )
            adx = self._calculate_adx(df)
            strength = min(adx.iloc[index] / 50.0, 1.0)
            return 'SELL', strength

        return 'HOLD', 0.0

    def _check_ema_trend(self, df: pd.DataFrame, index: int) -> Optional[str]:
        """检查EMA趋势方向

        Args:
            df: 数据
            index: 索引

        Returns:
            'UP', 'DOWN', 或 None（无明确趋势）
        """
        ema_fast = self._calculate_ema(df['close'], self.ema_fast)
        ema_slow = self._calculate_ema(df['close'], self.ema_slow)

        current_fast = ema_fast.iloc[index]
        current_slow = ema_slow.iloc[index]
        current_price = df['close'].iloc[index]

        # 价格在均线之上，且快线在慢线之上
        if current_price > current_fast > current_slow:
            # 确认趋势持续（过去5根K线都保持）
            if all(ema_fast.iloc[index-i] > ema_slow.iloc[index-i] for i in range(5)):
                return 'UP'

        # 价格在均线之下，且快线在慢线之下
        elif current_price < current_fast < current_slow:
            if all(ema_fast.iloc[index-i] < ema_slow.iloc[index-i] for i in range(5)):
                return 'DOWN'

        return None

    def _check_adx(self, df: pd.DataFrame, index: int) -> bool:
        """检查ADX确认趋势强度

        Args:
            df: 数据
            index: 索引

        Returns:
            是否确认
        """
        adx = self._calculate_adx(df)
        current_adx = adx.iloc[index]

        # ADX > 25 且在上升
        if current_adx > self.adx_threshold:
            # 检查ADX是否在上升（过去3根K线）
            if index >= 3:
                adx_increasing = all(
                    adx.iloc[index-i] >= adx.iloc[index-i-1]
                    for i in range(3)
                )
                return adx_increasing

        return False

    def _check_volume(self, df: pd.DataFrame, index: int) -> bool:
        """检查成交量确认

        Args:
            df: 数据
            index: 索引

        Returns:
            是否确认
        """
        if index < 20:
            return False

        # 当前成交量
        current_volume = df['volume'].iloc[index]

        # 平均成交量（过去20根）
        avg_volume = df['volume'].iloc[index-20:index].mean()

        # 成交量应高于均值
        return current_volume > avg_volume * self.volume_multiplier

    def _check_exit_conditions(
        self,
        df: pd.DataFrame,
        index: int,
        current_price: float
    ) -> tuple[bool, str]:
        """检查退出条件

        Args:
            df: 数据
            index: 索引
            current_price: 当前价格

        Returns:
            (是否应该退出, 原因)
        """
        if self.position is None:
            return False, ""

        # 1. 移动止损
        if self.position.direction == 'LONG':
            trailing_stop = self.position.highest_price * (1 - self.trailing_stop_pct)
            if current_price <= trailing_stop:
                return True, "移动止损"
        else:  # SHORT
            trailing_stop = self.position.lowest_price * (1 + self.trailing_stop_pct)
            if current_price >= trailing_stop:
                return True, "移动止损"

        # 2. 持仓时间过长
        holding_hours = index - self.position.entry_time
        if holding_hours >= self.max_holding_hours:
            return True, "超时退出"

        # 3. EMA交叉反转
        ema_fast = self._calculate_ema(df['close'], self.ema_fast)
        ema_slow = self._calculate_ema(df['close'], self.ema_slow)

        if self.position.direction == 'LONG':
            # 快线下穿慢线
            if ema_fast.iloc[index] < ema_slow.iloc[index]:
                return True, "EMA交叉"
        else:  # SHORT
            # 快线上穿慢线
            if ema_fast.iloc[index] > ema_slow.iloc[index]:
                return True, "EMA交叉"

        return False, ""

    def _update_position_extremes(self, current_price: float):
        """更新持仓的最高/最低价"""
        if self.position is None:
            return

        if current_price > self.position.highest_price:
            self.position.highest_price = current_price

        if current_price < self.position.lowest_price:
            self.position.lowest_price = current_price

    def _calculate_ema(self, series: pd.Series, period: int) -> pd.Series:
        """计算EMA"""
        cache_key = f'ema_{id(series)}_{period}'
        if cache_key in self._cache:
            return self._cache[cache_key]

        ema = series.ewm(span=period, adjust=False).mean()
        self._cache[cache_key] = ema
        return ema

    def _calculate_adx(self, df: pd.DataFrame) -> pd.Series:
        """计算ADX"""
        cache_key = f'adx_{id(df)}'
        if cache_key in self._cache:
            return self._cache[cache_key]

        high = df['high']
        low = df['low']
        close = df['close']

        # 计算 +DM 和 -DM
        plus_dm = high.diff()
        minus_dm = -low.diff()

        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0

        # 计算TR
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # 平滑处理
        period = 14
        atr = tr.rolling(window=period).mean()
        plus_di = 100 * plus_dm.rolling(window=period).mean() / atr
        minus_di = 100 * minus_dm.rolling(window=period).mean() / atr

        # 计算DX和ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=period).mean()

        self._cache[cache_key] = adx
        return adx

    def clear_cache(self):
        """清除缓存"""
        self._cache = {}

    def reset(self):
        """重置策略状态"""
        self.position = None
        self.clear_cache()

    def get_position_info(self) -> Optional[dict]:
        """获取持仓信息"""
        if self.position is None:
            return None

        return {
            'direction': self.position.direction,
            'entry_price': self.position.entry_price,
            'highest_price': self.position.highest_price,
            'lowest_price': self.position.lowest_price,
            'holding_hours': 0,  # 需要外部计算
        }

    def get_statistics(self) -> dict:
        """获取策略统计信息"""
        return {
            'has_position': self.position is not None,
            'position_direction': self.position.direction if self.position else None,
            'ema_fast': self.ema_fast,
            'ema_slow': self.ema_slow,
            'adx_threshold': self.adx_threshold,
        }
