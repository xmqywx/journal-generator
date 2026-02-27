import pytest
from quant.engine.portfolio import Trade
from quant.report.analyzer import Analyzer


def test_total_return():
    a = Analyzer(initial_capital=1000.0, final_equity=1200.0, equity_curve=[1000, 1100, 1200])
    assert a.total_return() == pytest.approx(0.2, abs=0.001)


def test_max_drawdown():
    curve = [1000, 1100, 1200, 900, 1000]
    a = Analyzer(initial_capital=1000.0, final_equity=1000.0, equity_curve=curve)
    assert a.max_drawdown() == pytest.approx(0.25, abs=0.01)


def test_win_rate():
    trades = [
        Trade(entry_price=100, exit_price=110, size=1, side="long", pnl=10),
        Trade(entry_price=100, exit_price=90, size=1, side="long", pnl=-10),
        Trade(entry_price=100, exit_price=105, size=1, side="long", pnl=5),
    ]
    a = Analyzer(initial_capital=1000.0, final_equity=1005.0, equity_curve=[1000], trades=trades)
    assert a.win_rate() == pytest.approx(2 / 3, abs=0.01)


def test_no_trades():
    a = Analyzer(initial_capital=1000.0, final_equity=1000.0, equity_curve=[1000])
    assert a.win_rate() == 0.0
    assert a.total_trades() == 0


def test_summary_dict():
    trades = [
        Trade(entry_price=100, exit_price=110, size=1, side="long", pnl=10),
    ]
    a = Analyzer(initial_capital=1000.0, final_equity=1010.0, equity_curve=[1000, 1010], trades=trades)
    summary = a.summary()
    assert "total_return" in summary
    assert "max_drawdown" in summary
    assert "win_rate" in summary
    assert "total_trades" in summary
