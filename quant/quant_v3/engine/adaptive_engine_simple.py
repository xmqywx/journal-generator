"""
AdaptiveEngine Simple - 简化版自适应引擎

只做牛市买入，避免高风险做空
- 牛市 → 2倍杠杆买入持有
- 熊市/震荡 → 平仓观望
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

import pandas as pd
import numpy as np
from typing import Dict, List

from quant_v3.core.market_detector import MarketDetector
from quant_v3.strategies.bull_market_hold import BullMarketHold
from quant_v3.strategies.ranging_hold import RangingHold


class AdaptiveEngineSimple:
    """简化版自适应回测引擎

    只在牛市做多，避免做空风险
    """

    def __init__(
        self,
        initial_capital: float = 10000.0,
        commission_rate: float = 0.0008
    ):
        """
        Args:
            initial_capital: 初始资金
            commission_rate: 手续费率
        """
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate

        # 市场检测器
        self.detector = MarketDetector(
            lookback_days=60,
            trend_threshold=0.10,
            adx_threshold_strong=25.0,
            adx_threshold_weak=15.0
        )

        # 两个策略
        self.bull_strategy = BullMarketHold(leverage=2.0)
        self.ranging_strategy = RangingHold()

    def backtest(self, df: pd.DataFrame) -> Dict:
        """运行自适应回测

        Args:
            df: OHLCV数据

        Returns:
            回测结果字典
        """
        capital = self.initial_capital
        position = None  # 'LONG' or None
        position_size = 0.0  # BTC数量
        entry_price = 0.0

        trades = []
        equity_curve = []
        market_states = []

        # 从100小时开始
        for i in range(100, len(df)):
            price = df['close'].iloc[i]

            # 1. 检测市场状态
            market_state = self.detector.detect(df, i)
            market_states.append({
                'index': i,
                'timestamp': df['timestamp'].iloc[i],
                'state': market_state,
                'price': price
            })

            # 2. 根据市场状态决定信号（不使用策略内部状态）
            if market_state == 'BULL' and position is None:
                # 无持仓且牛市→买入
                signal = 'BUY'
                strength = 2.0  # 2倍杠杆
            elif market_state != 'BULL' and position == 'LONG':
                # 非牛市且有持仓→卖出
                signal = 'SELL'
                strength = 1.0
            else:
                # 其他情况→观望
                signal = 'HOLD'
                strength = 0.0

            # 3. 执行交易
            if signal == 'BUY' and position is None:
                # 买入（做多）
                position = 'LONG'
                leverage = strength if strength > 0 else 1.0
                position_value = capital * leverage
                commission = position_value * self.commission_rate
                position_size = (position_value - commission) / price
                entry_price = price

                capital -= commission
                trades.append({
                    'type': 'BUY',
                    'timestamp': df['timestamp'].iloc[i],
                    'price': price,
                    'size': position_size,
                    'leverage': leverage,
                    'market_state': market_state,
                    'commission': commission
                })

            elif signal == 'SELL' and position == 'LONG':
                # 平仓（杠杆逻辑修正）
                position_value = position_size * price
                commission = position_value * self.commission_rate
                # 归还杠杆借款后的净收益
                pnl = position_value - (position_size * entry_price) - commission
                capital += pnl  # 只加盈亏，不加本金

                trades.append({
                    'type': 'SELL',
                    'timestamp': df['timestamp'].iloc[i],
                    'price': price,
                    'size': position_size,
                    'pnl': pnl,
                    'market_state': market_state,
                    'commission': commission
                })

                position = None
                position_size = 0.0

            # 4. 记录权益
            current_equity = capital
            if position == 'LONG':
                current_equity += position_size * price

            equity_curve.append({
                'timestamp': df['timestamp'].iloc[i],
                'equity': current_equity,
                'position': position
            })

        # 最终平仓（如果有持仓）
        if position == 'LONG':
            final_price = df['close'].iloc[-1]
            final_timestamp = df['timestamp'].iloc[-1]
            position_value = position_size * final_price
            commission = position_value * self.commission_rate
            pnl = position_value - (position_size * entry_price) - commission
            capital += pnl  # 只加盈亏

            trades.append({
                'type': 'SELL (FINAL)',
                'timestamp': final_timestamp,
                'price': final_price,
                'size': position_size,
                'pnl': pnl,
                'market_state': 'END',
                'commission': commission
            })

        # 计算统计指标
        total_return = (capital - self.initial_capital) / self.initial_capital

        # 计算市场状态分布
        state_counts = {}
        for state in market_states:
            s = state['state']
            state_counts[s] = state_counts.get(s, 0) + 1

        return {
            'initial_capital': self.initial_capital,
            'final_capital': capital,
            'total_return': total_return,
            'total_trades': len([t for t in trades if t['type'] == 'BUY']),
            'trades': trades,
            'equity_curve': equity_curve,
            'market_states': market_states,
            'state_distribution': state_counts
        }

    def reset(self):
        """重置所有策略状态"""
        self.bull_strategy.reset()
        self.ranging_strategy.reset()
