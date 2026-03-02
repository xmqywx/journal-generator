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
        # BTC级别：日波动2-3%
        returns = np.random.normal(0.001, 0.025, 365)
    elif volatility_level == 'moderate':
        # 主流币：日波动3-5%
        returns = np.random.normal(0.001, 0.04, 365)
    else:  # high
        # SOL级别：日波动5-8%
        returns = np.random.normal(0.001, 0.07, 365)

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

    assert result['volatility_level'] == 'STABLE'
    assert result['daily_volatility'] < 0.04
    assert 'atr_percentage' in result

def test_volatility_detector_high():
    """测试高波动币种识别（SOL）"""
    df = create_sample_data('high')
    detector = VolatilityDetector()
    result = detector.calculate_volatility(df)

    assert result['volatility_level'] == 'HIGH'
    assert result['daily_volatility'] > 0.04
