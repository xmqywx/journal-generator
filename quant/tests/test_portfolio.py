import pytest
from quant.engine.portfolio import Portfolio, Trade


def test_initial_state():
    p = Portfolio(initial_capital=1000.0)
    assert p.cash == 1000.0
    assert p.position == 0.0
    assert p.equity(100.0) == 1000.0


def test_buy_spot():
    p = Portfolio(initial_capital=1000.0, fee_rate=0.001, slippage_rate=0.0)
    p.open_position(price=100.0, size=5.0, side="long")
    assert p.position == 5.0
    assert p.cash == pytest.approx(1000.0 - 500.0 - 0.5, abs=0.01)


def test_sell_spot():
    p = Portfolio(initial_capital=1000.0, fee_rate=0.001, slippage_rate=0.0)
    p.open_position(price=100.0, size=5.0, side="long")
    p.close_position(price=110.0)
    assert p.position == 0.0
    assert p.cash > 1000.0


def test_short_futures():
    p = Portfolio(initial_capital=1000.0, fee_rate=0.0005, leverage=2.0, slippage_rate=0.0)
    p.open_position(price=100.0, size=5.0, side="short")
    assert p.position == -5.0
    p.close_position(price=90.0)
    assert p.position == 0.0
    assert p.cash > 1000.0


def test_stop_loss():
    p = Portfolio(initial_capital=1000.0, fee_rate=0.001, stop_loss=0.05, slippage_rate=0.0)
    p.open_position(price=100.0, size=5.0, side="long")
    assert p.should_stop_loss(price=94.0) is True
    assert p.should_stop_loss(price=96.0) is False


def test_equity_with_position():
    p = Portfolio(initial_capital=1000.0, fee_rate=0.001, slippage_rate=0.0)
    p.open_position(price=100.0, size=5.0, side="long")
    equity = p.equity(current_price=110.0)
    assert equity > 1000.0


def test_trade_history():
    p = Portfolio(initial_capital=1000.0, fee_rate=0.001, slippage_rate=0.0)
    p.open_position(price=100.0, size=5.0, side="long")
    p.close_position(price=110.0)
    assert len(p.trades) == 1
    assert p.trades[0].pnl > 0
