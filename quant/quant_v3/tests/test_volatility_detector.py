# quant_v3/tests/test_volatility_detector.py
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from quant_v3.core.volatility_detector import VolatilityDetector

def create_sample_data(volatility_level='stable'):
    """创建测试数据"""
    dates = pd.date_range(end=datetime.now(), periods=365, freq='D')

    if volatility_level == 'stable':
        # STABLE级别：日波动<3%, 周波动<5%, 最大跌幅<8%
        # 使用更小的标准差确保稳定分类
        returns = np.random.normal(0.001, 0.015, 365)
    elif volatility_level == 'moderate':
        # MODERATE级别：介于STABLE和HIGH之间
        returns = np.random.normal(0.001, 0.04, 365)
    else:  # high
        # HIGH级别：日波动>5%, 周波动>10%, 最大跌幅>15%
        returns = np.random.normal(0.001, 0.08, 365)

    prices = 100 * (1 + returns).cumprod()

    df = pd.DataFrame({
        'timestamp': (dates.astype(int) // 10**6).values,
        'date': dates.date,
        'open': prices * np.random.uniform(0.98, 1.02, 365),
        'high': prices * np.random.uniform(1.0, 1.05, 365),
        'low': prices * np.random.uniform(0.95, 1.0, 365),
        'close': prices,
        'volume': np.random.uniform(1e6, 1e7, 365)
    })

    return df

def test_volatility_detector_stable():
    """测试稳定型币种识别（BTC）"""
    df = create_sample_data('stable')
    detector = VolatilityDetector()
    result = detector.calculate_volatility(df)

    # Verify volatility classification
    assert result['volatility_level'] == 'STABLE'

    # Verify daily_volatility
    assert result['daily_volatility'] < 0.04
    assert result['daily_volatility'] > 0
    assert not np.isnan(result['daily_volatility'])

    # Verify weekly_volatility
    assert 'weekly_volatility' in result
    assert result['weekly_volatility'] > 0
    assert not np.isnan(result['weekly_volatility'])

    # Verify atr_percentage
    assert 'atr_percentage' in result
    assert result['atr_percentage'] > 0
    assert not np.isnan(result['atr_percentage'])

    # Verify max_drawdown_speed
    assert 'max_drawdown_speed' in result
    assert result['max_drawdown_speed'] > 0
    assert not np.isnan(result['max_drawdown_speed'])

def test_volatility_detector_high():
    """测试高波动币种识别（SOL）"""
    df = create_sample_data('high')
    detector = VolatilityDetector()
    result = detector.calculate_volatility(df)

    # Verify volatility classification
    assert result['volatility_level'] == 'HIGH'

    # Verify daily_volatility
    assert result['daily_volatility'] > 0.04
    assert not np.isnan(result['daily_volatility'])

    # Verify weekly_volatility
    assert 'weekly_volatility' in result
    assert result['weekly_volatility'] > 0
    assert not np.isnan(result['weekly_volatility'])

    # Verify atr_percentage
    assert 'atr_percentage' in result
    assert result['atr_percentage'] > 0
    assert not np.isnan(result['atr_percentage'])

    # Verify max_drawdown_speed
    assert 'max_drawdown_speed' in result
    assert result['max_drawdown_speed'] > 0
    assert not np.isnan(result['max_drawdown_speed'])
