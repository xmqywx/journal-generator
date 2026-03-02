# quant_v3/core/adaptive_exit_strategy.py
"""
自适应卖出策略
根据波动率类型使用不同的卖出参数
"""
from typing import Dict, Literal

VolatilityLevel = Literal['STABLE', 'MODERATE', 'HIGH']
ExitAction = Literal['HOLD', 'SELL_PARTIAL', 'SELL_ALL']


class AdaptiveExitStrategy:
    """自适应卖出策略"""

    # 策略参数库
    STRATEGIES = {
        'STABLE': {
            'name': '稳定型策略（BTC/ETH）',
            'sell_threshold': 6.0,
            'stop_loss_pct': 12.0,
            'profit_protection': [
                {'profit_pct': 80.0, 'drawback_pct': 20.0},  # 提高阈值，允许追大趋势
                {'profit_pct': 50.0, 'drawback_pct': 15.0},  # 保持原有第二档
            ],
            'quick_profit_lock': None,
        },
        'MODERATE': {
            'name': '中等型策略（主流币）',
            'sell_threshold': 6.3,
            'stop_loss_pct': 11.0,
            'profit_protection': [
                {'profit_pct': 40.0, 'drawback_pct': 12.0},
                {'profit_pct': 25.0, 'drawback_pct': 10.0},
            ],
            'quick_profit_lock': None,
        },
        'HIGH': {
            'name': '激进型策略（SOL/山寨币）',
            'sell_threshold': 6.5,
            'stop_loss_pct': 10.0,
            'profit_protection': [
                {'profit_pct': 35.0, 'drawback_pct': 8.0},
                {'profit_pct': 20.0, 'drawback_pct': 10.0},
            ],
            'quick_profit_lock': {
                'trigger_pct': 25.0,
                'sell_ratio': 0.4,
            },
        },
    }

    def check_exit(
        self,
        position_info: Dict,
        vol_level: VolatilityLevel
    ) -> Dict:
        """
        检查是否应该卖出

        Args:
            position_info: {
                'entry_price': 买入价,
                'current_price': 当前价,
                'peak_price': 持仓期间最高价,
                'entry_capital': 买入资金,
                'score': 当前评分
            }
            vol_level: 波动率类型

        Returns:
            {
                'action': 'HOLD' / 'SELL_PARTIAL' / 'SELL_ALL',
                'sell_ratio': 卖出比例（仅SELL_PARTIAL时有效）,
                'reason': 原因说明
            }
        """
        strategy = self.STRATEGIES[vol_level]

        entry_price = position_info['entry_price']
        current_price = position_info['current_price']
        peak_price = position_info['peak_price']
        score = position_info['score']

        # 计算盈亏
        price_change_pct = (current_price - entry_price) / entry_price * 100
        drawback_from_peak = (peak_price - current_price) / peak_price * 100 if peak_price > 0 else 0

        # 使用实际资金盈亏百分比（考虑杠杆影响）
        actual_profit_pct = position_info.get('actual_profit_pct', price_change_pct)

        # 1. 止损（最高优先级 - 风险控制）使用实际资金亏损
        if actual_profit_pct <= -strategy['stop_loss_pct']:
            return {
                'action': 'SELL_ALL',
                'sell_ratio': 1.0,
                'reason': f'触发止损（资金亏损{abs(actual_profit_pct):.1f}%）'
            }

        # 2. 快速锁定利润（仅HIGH型）- 基于价格涨幅
        quick_lock = strategy.get('quick_profit_lock')
        if quick_lock:
            if price_change_pct >= quick_lock['trigger_pct']:
                return {
                    'action': 'SELL_PARTIAL',
                    'sell_ratio': quick_lock['sell_ratio'],
                    'reason': f'高波动币种快速锁定利润（价格涨{price_change_pct:.1f}%）'
                }

        # 3. 分段止盈 - 基于价格涨幅
        for level in strategy['profit_protection']:
            if price_change_pct >= level['profit_pct']:
                if drawback_from_peak >= level['drawback_pct']:
                    if price_change_pct < 50:
                        # 中小盈利：部分卖出
                        return {
                            'action': 'SELL_PARTIAL',
                            'sell_ratio': 0.5,
                            'reason': f'价格涨{price_change_pct:.1f}%，从峰值回撤{drawback_from_peak:.1f}%，部分止盈'
                        }
                    else:
                        # 大盈利：全部卖出
                        return {
                            'action': 'SELL_ALL',
                            'sell_ratio': 1.0,
                            'reason': f'价格涨{price_change_pct:.1f}%，从峰值回撤{drawback_from_peak:.1f}%，全部止盈'
                        }

        # 4. 评分卖出
        if score < strategy['sell_threshold']:
            return {
                'action': 'SELL_ALL',
                'sell_ratio': 1.0,
                'reason': f'评分{score:.2f}低于阈值{strategy["sell_threshold"]}'
            }

        # 5. 持有
        return {
            'action': 'HOLD',
            'sell_ratio': 0.0,
            'reason': '持仓条件满足'
        }
