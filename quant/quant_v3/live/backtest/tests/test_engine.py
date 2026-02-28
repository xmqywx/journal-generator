"""
测试回测引擎
"""
import pytest
from datetime import date
import pandas as pd
from quant_v3.live.backtest.engine import BacktestEngine
from quant_v3.live.backtest.database import SessionLocal, init_db, BacktestRun


@pytest.fixture
def db_session():
    """创建测试数据库会话"""
    init_db()
    session = SessionLocal()
    yield session
    # 清理
    session.query(BacktestRun).delete()
    session.commit()
    session.close()


@pytest.fixture
def engine(db_session):
    """创建回测引擎实例"""
    return BacktestEngine(db_session, socketio=None)


def test_calculate_metrics_simple(engine):
    """测试简单场景的指标计算"""
    trades = [
        {'pnl': 100, 'return_pct': 0.05, 'holding_days': 30},
        {'pnl': 200, 'return_pct': 0.10, 'holding_days': 45},
        {'pnl': -50, 'return_pct': -0.025, 'holding_days': 20}
    ]
    initial_capital = 2000
    final_capital = 2250

    metrics = engine._calculate_metrics(trades, initial_capital, final_capital, date(2024, 1, 1), date(2024, 12, 31))

    assert metrics['num_trades'] == 3
    assert metrics['win_rate'] == pytest.approx(2/3, rel=1e-4)  # 2赢1亏
    assert metrics['total_return'] == pytest.approx(0.125, rel=1e-4)  # (2250-2000)/2000
    assert metrics['avg_holding_days'] == pytest.approx((30+45+20)/3, rel=1e-2)


def test_simulate_trade_with_fee(engine):
    """测试带手续费的交易模拟"""
    # 买入
    capital = 2000
    position = 0
    price = 50000
    leverage = 1.0
    fee_rate = 0.0004

    new_capital, new_position = engine._simulate_buy(capital, position, price, leverage, fee_rate)

    # 验证：扣除手续费后的资金购买BTC
    expected_fee = capital * fee_rate
    expected_btc = (capital - expected_fee) / price
    assert new_position == pytest.approx(expected_btc, rel=1e-6)
    assert new_capital == 0  # 全仓

    # 卖出
    sell_price = 55000
    final_capital, final_position = engine._simulate_sell(new_capital, new_position, sell_price, fee_rate)

    expected_gross = new_position * sell_price
    expected_sell_fee = expected_gross * fee_rate
    expected_final = expected_gross - expected_sell_fee

    assert final_position == 0
    assert final_capital == pytest.approx(expected_final, rel=1e-4)
