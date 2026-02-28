"""
AdaptiveEngine - 自适应引擎

根据市场环境自动切换策略：
- 牛市 → 2倍杠杆买入持有
- 熊市 → 2倍杠杆做空
- 震荡 → 统计套利
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

import pandas as pd
import numpy as np
from typing import Dict, List

from quant_v3.core.market_detector import MarketDetector
from quant_v3.strategies.bull_market_hold import BullMarketHold
from quant_v3.strategies.bear_market_short import BearMarketShort
from quant_v3.strategies.ranging_hold import RangingHold


class AdaptiveEngine:
    """自适应回测引擎

    根据市场环境自动切换策略
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

        # 三个策略
        self.bull_strategy = BullMarketHold(leverage=2.0)
        self.bear_strategy = BearMarketShort(leverage=2.0)
        self.ranging_strategy = RangingHold()

    def backtest(self, df: pd.DataFrame) -> Dict:
        """运行自适应回测

        Args:
            df: OHLCV数据

        Returns:
            回测结果字典
        """
        capital = self.initial_capital
        position = None  # 'LONG', 'SHORT', or None
        position_size = 0.0  # BTC数量
        entry_price = 0.0

        trades = []
        equity_curve = []
        market_states = []

        # 从100小时开始（确保有足够历史数据）
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

            # 2. 根据市场状态选择策略
            if market_state == 'BULL':
                signal, strength = self.bull_strategy.generate_signal(df, i, market_state)
            elif market_state == 'BEAR':
                signal, strength = self.bear_strategy.generate_signal(df, i, market_state)
            else:  # RANGING
                signal, strength = self.ranging_strategy.generate_signal(df, i)

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

            elif signal == 'SHORT' and position is None:
                # 做空
                position = 'SHORT'
                leverage = strength if strength > 0 else 1.0
                position_value = capital * leverage
                commission = position_value * self.commission_rate
                position_size = (position_value - commission) / price
                entry_price = price

                capital -= commission
                trades.append({
                    'type': 'SHORT',
                    'timestamp': df['timestamp'].iloc[i],
                    'price': price,
                    'size': position_size,
                    'leverage': leverage,
                    'market_state': market_state,
                    'commission': commission
                })

            elif signal in ['SELL', 'CLOSE'] and position is not None:
                # 平仓
                if position == 'LONG':
                    # 平多仓
                    position_value = position_size * price
                    commission = position_value * self.commission_rate
                    pnl = position_value - (position_size * entry_price) - commission
                    capital += position_value - commission

                    trades.append({
                        'type': 'SELL',
                        'timestamp': df['timestamp'].iloc[i],
                        'price': price,
                        'size': position_size,
                        'pnl': pnl,
                        'market_state': market_state,
                        'commission': commission
                    })

                elif position == 'SHORT':
                    # 平空仓
                    pnl = (entry_price - price) * position_size
                    commission = position_size * price * self.commission_rate
                    capital += pnl - commission

                    trades.append({
                        'type': 'CLOSE_SHORT',
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
            elif position == 'SHORT':
                current_equity += (entry_price - price) * position_size

            equity_curve.append({
                'timestamp': df['timestamp'].iloc[i],
                'equity': current_equity,
                'position': position
            })

        # 最终平仓（如果有持仓）
        if position is not None:
            final_price = df['close'].iloc[-1]
            if position == 'LONG':
                position_value = position_size * final_price
                commission = position_value * self.commission_rate
                capital += position_value - commission
            elif position == 'SHORT':
                pnl = (entry_price - final_price) * position_size
                commission = position_size * final_price * self.commission_rate
                capital += pnl - commission

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
            'total_trades': len([t for t in trades if t['type'] in ['BUY', 'SHORT']]),
            'trades': trades,
            'equity_curve': equity_curve,
            'market_states': market_states,
            'state_distribution': state_counts
        }

    def reset(self):
        """重置所有策略状态"""
        self.bull_strategy.reset()
        self.bear_strategy.reset()
        self.ranging_strategy.reset()
