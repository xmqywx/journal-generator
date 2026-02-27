import pandas as pd
from quant.config import Config
from quant.strategies.base import Strategy, Signal
from quant.engine.portfolio import Portfolio


class Backtester:
    """Run strategy against historical data and record results."""

    def __init__(self, config: Config):
        self.config = config

    def run(
        self,
        df: pd.DataFrame,
        strategy: Strategy,
        capital: float = 690.0,
        fee_rate: float = 0.001,
        leverage: float = 1.0,
        stop_loss: float = 0.0,
    ) -> dict:
        portfolio = Portfolio(
            initial_capital=capital,
            fee_rate=fee_rate,
            slippage_rate=self.config.slippage_rate,
            leverage=leverage,
            stop_loss=stop_loss,
        )

        equity_curve = []

        for i in range(len(df)):
            price = df["close"].iloc[i]
            ts = int(df["timestamp"].iloc[i])

            # Check stop-loss first
            if portfolio.position != 0 and portfolio.should_stop_loss(price):
                portfolio.close_position(price, timestamp=ts)

            # Generate signal
            signal = strategy.generate_signal(df, i)

            # Execute signal
            if signal == Signal.BUY and portfolio.position <= 0:
                if portfolio.position < 0:
                    portfolio.close_position(price, timestamp=ts)
                size = portfolio.position_size(price, weight=1.0)
                if size > 0 and portfolio.cash > price * size * (1 / leverage) * 0.1:
                    portfolio.open_position(price, size, side="long")

            elif signal == Signal.SELL and portfolio.position >= 0:
                if portfolio.position > 0:
                    portfolio.close_position(price, timestamp=ts)
                size = portfolio.position_size(price, weight=1.0)
                if size > 0 and leverage > 1.0:
                    portfolio.open_position(price, size, side="short")

            equity_curve.append(portfolio.equity(price))

        # Close any remaining position at end
        if portfolio.position != 0:
            final_price = df["close"].iloc[-1]
            portfolio.close_position(final_price, timestamp=int(df["timestamp"].iloc[-1]))

        return {
            "equity_curve": equity_curve,
            "trades": portfolio.trades,
            "final_equity": portfolio.equity(df["close"].iloc[-1]),
            "initial_capital": capital,
        }
