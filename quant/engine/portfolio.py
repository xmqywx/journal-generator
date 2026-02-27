from dataclasses import dataclass, field


@dataclass
class Trade:
    entry_price: float
    exit_price: float
    size: float
    side: str  # "long" or "short"
    pnl: float
    entry_time: int = 0
    exit_time: int = 0


class Portfolio:
    """Track positions, cash, and trade history."""

    def __init__(
        self,
        initial_capital: float = 690.0,
        fee_rate: float = 0.001,
        slippage_rate: float = 0.0005,
        leverage: float = 1.0,
        stop_loss: float = 0.0,
    ):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.fee_rate = fee_rate
        self.slippage_rate = slippage_rate
        self.leverage = leverage
        self.stop_loss = stop_loss
        self.position = 0.0
        self.entry_price = 0.0
        self.trades: list[Trade] = []
        self.equity_curve: list[float] = []

    def open_position(self, price: float, size: float, side: str) -> None:
        slipped_price = price * (1 + self.slippage_rate) if side == "long" else price * (1 - self.slippage_rate)
        cost = slipped_price * size
        fee = cost * self.fee_rate

        if side == "long":
            margin = cost / self.leverage
            self.cash -= margin + fee
            self.position = size
        else:
            margin = cost / self.leverage
            self.cash -= margin + fee
            self.position = -size

        self.entry_price = slipped_price

    def close_position(self, price: float, timestamp: int = 0) -> None:
        if self.position == 0:
            return

        size = abs(self.position)
        side = "long" if self.position > 0 else "short"
        slipped_price = price * (1 - self.slippage_rate) if side == "long" else price * (1 + self.slippage_rate)

        if side == "long":
            pnl = (slipped_price - self.entry_price) * size
        else:
            pnl = (self.entry_price - slipped_price) * size

        fee = slipped_price * size * self.fee_rate
        margin = self.entry_price * size / self.leverage
        self.cash += margin + pnl - fee

        self.trades.append(Trade(
            entry_price=self.entry_price,
            exit_price=slipped_price,
            size=size,
            side=side,
            pnl=pnl - fee,
            exit_time=timestamp,
        ))
        self.position = 0.0
        self.entry_price = 0.0

    def should_stop_loss(self, price: float) -> bool:
        if self.stop_loss <= 0 or self.position == 0:
            return False
        if self.position > 0:
            return (self.entry_price - price) / self.entry_price >= self.stop_loss
        else:
            return (price - self.entry_price) / self.entry_price >= self.stop_loss

    def equity(self, current_price: float) -> float:
        if self.position == 0:
            return self.cash
        size = abs(self.position)
        if self.position > 0:
            unrealized = (current_price - self.entry_price) * size
        else:
            unrealized = (self.entry_price - current_price) * size
        margin = self.entry_price * size / self.leverage
        return self.cash + margin + unrealized

    def position_size(self, price: float, weight: float) -> float:
        available = self.cash * weight
        return available / price
