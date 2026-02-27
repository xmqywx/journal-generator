import pytest
from quant.config import Config


def test_config_strategy_weights_sum():
    """测试策略权重总和为1.0"""
    config = Config()
    total = (
        config.dual_ma_weight +
        config.rsi_weight +
        config.bollinger_weight +
        config.grid_weight +
        config.random_weight
    )
    assert abs(total - 1.0) < 0.01, f"Strategy weights sum to {total}, expected 1.0"


def test_config_grid_params():
    """测试网格策略参数"""
    config = Config()
    assert config.grid_atr_period == 14
    assert config.grid_base_spacing == 0.02
    assert config.grid_atr_multiplier == 1.0
    assert config.grid_levels == 7
    assert config.grid_leverage == 2.0
    assert config.grid_stop_loss == 0.05


def test_config_random_params():
    """测试随机策略参数"""
    config = Config()
    assert config.random_seed == 42
    assert config.random_buy_prob == 0.30
    assert config.random_sell_prob == 0.30
    assert config.random_stop_loss == 0.03

    # 验证概率总和不超过1.0
    total_prob = config.random_buy_prob + config.random_sell_prob
    assert total_prob <= 1.0
