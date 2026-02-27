import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from quant.engine.portfolio import Trade


class Analyzer:
    """Analyze backtesting results and generate reports."""

    def __init__(
        self,
        initial_capital: float,
        final_equity: float,
        equity_curve: list[float],
        trades: list[Trade] | None = None,
    ):
        self.initial_capital = initial_capital
        self.final_equity = final_equity
        self.equity_curve = equity_curve
        self.trades = trades or []

    def total_return(self) -> float:
        return (self.final_equity - self.initial_capital) / self.initial_capital

    def max_drawdown(self) -> float:
        if len(self.equity_curve) < 2:
            return 0.0
        peak = self.equity_curve[0]
        max_dd = 0.0
        for eq in self.equity_curve:
            if eq > peak:
                peak = eq
            dd = (peak - eq) / peak if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd
        return max_dd

    def sharpe_ratio(self, risk_free_rate: float = 0.0, periods_per_year: float = 8760) -> float:
        if len(self.equity_curve) < 2:
            return 0.0
        returns = []
        for i in range(1, len(self.equity_curve)):
            r = (self.equity_curve[i] - self.equity_curve[i - 1]) / self.equity_curve[i - 1]
            returns.append(r)
        arr = np.array(returns)
        if arr.std() == 0:
            return 0.0
        return (arr.mean() - risk_free_rate / periods_per_year) / arr.std() * np.sqrt(periods_per_year)

    def win_rate(self) -> float:
        if not self.trades:
            return 0.0
        wins = sum(1 for t in self.trades if t.pnl > 0)
        return wins / len(self.trades)

    def total_trades(self) -> int:
        return len(self.trades)

    def avg_pnl(self) -> float:
        if not self.trades:
            return 0.0
        return sum(t.pnl for t in self.trades) / len(self.trades)

    def summary(self) -> dict:
        return {
            "initial_capital": self.initial_capital,
            "final_equity": round(self.final_equity, 2),
            "total_return": round(self.total_return() * 100, 2),
            "max_drawdown": round(self.max_drawdown() * 100, 2),
            "sharpe_ratio": round(self.sharpe_ratio(), 2),
            "win_rate": round(self.win_rate() * 100, 2),
            "total_trades": self.total_trades(),
            "avg_pnl": round(self.avg_pnl(), 4),
        }

    def plot(self, title: str = "Equity Curve", save_path: str | None = None) -> None:
        plt.figure(figsize=(12, 6))
        plt.plot(self.equity_curve, linewidth=1)
        plt.title(title)
        plt.xlabel("Time (candles)")
        plt.ylabel("Equity (USDT)")
        plt.grid(True, alpha=0.3)
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches="tight")
        plt.close()

    def print_summary(self, strategy_name: str = "") -> None:
        s = self.summary()
        print(f"\n{'=' * 50}")
        print(f"  {strategy_name or 'Strategy'} Backtest Results")
        print(f"{'=' * 50}")
        print(f"  Initial Capital:   ${s['initial_capital']:.2f}")
        print(f"  Final Equity:      ${s['final_equity']:.2f}")
        print(f"  Total Return:      {s['total_return']:.2f}%")
        print(f"  Max Drawdown:      {s['max_drawdown']:.2f}%")
        print(f"  Sharpe Ratio:      {s['sharpe_ratio']:.2f}")
        print(f"  Win Rate:          {s['win_rate']:.2f}%")
        print(f"  Total Trades:      {s['total_trades']}")
        print(f"  Avg PnL/Trade:     ${s['avg_pnl']:.4f}")
        print(f"{'=' * 50}\n")
