# quant_v3/tests/test_adaptive_exit_strategy.py
import pytest
from quant_v3.core.adaptive_exit_strategy import AdaptiveExitStrategy

def test_high_volatility_quick_lock():
    """测试高波动币种快速锁定利润"""
    strategy = AdaptiveExitStrategy()

    position_info = {
        'entry_price': 100.0,
        'current_price': 130.0,  # +30%盈利
        'peak_price': 130.0,
        'entry_capital': 2000.0,
        'score': 7.5
    }

    result = strategy.check_exit(position_info, 'HIGH')

    # 盈利30% > 25%，应该触发快速锁定
    assert result['action'] == 'SELL_PARTIAL'
    assert result['sell_ratio'] == 0.4
    assert '快速锁定' in result['reason']

def test_stable_profit_protection():
    """测试稳定型止盈保护"""
    strategy = AdaptiveExitStrategy()

    position_info = {
        'entry_price': 100.0,
        'current_price': 135.0,  # +35%盈利
        'peak_price': 150.0,     # 从峰值回撤10%
        'entry_capital': 2000.0,
        'score': 7.0
    }

    result = strategy.check_exit(position_info, 'STABLE')

    # 盈利30%，回撤10%，但STABLE允许12%回撤
    assert result['action'] == 'HOLD'

    # 回撤超过12%
    position_info['current_price'] = 131.0  # 回撤12.7%
    result = strategy.check_exit(position_info, 'STABLE')
    assert result['action'] in ['SELL_PARTIAL', 'SELL_ALL']

def test_stop_loss():
    """测试止损"""
    strategy = AdaptiveExitStrategy()

    position_info = {
        'entry_price': 100.0,
        'current_price': 89.0,  # -11%亏损
        'peak_price': 100.0,
        'entry_capital': 2000.0,
        'score': 6.5
    }

    # MODERATE型止损11%
    result = strategy.check_exit(position_info, 'MODERATE')
    assert result['action'] == 'SELL_ALL'
    assert '止损' in result['reason']

def test_score_exit():
    """测试评分卖出"""
    strategy = AdaptiveExitStrategy()

    position_info = {
        'entry_price': 100.0,
        'current_price': 105.0,
        'peak_price': 110.0,
        'entry_capital': 2000.0,
        'score': 6.2  # 低于HIGH型阈值6.5
    }

    result = strategy.check_exit(position_info, 'HIGH')
    assert result['action'] == 'SELL_ALL'
    assert '评分' in result['reason']
