"""
回测系统数据库模型
"""
import os
from datetime import datetime
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Date,
    DateTime,
    Numeric,
    JSON,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

# Database connection
# Default: Use system user without password (typical for Homebrew PostgreSQL on macOS)
# Override with DATABASE_URL environment variable if needed
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql://{os.getenv('USER', 'postgres')}@localhost:5432/quant_backtest"
)

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class BacktestRun(Base):
    """回测运行记录表"""
    __tablename__ = "backtest_runs"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    initial_capital = Column(Numeric(15, 2), nullable=False)
    leverage = Column(Numeric(5, 2), nullable=False)
    fee_rate = Column(Numeric(6, 4), nullable=False)
    strategy_params = Column(JSON, nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    result = relationship(
        "BacktestResult",
        back_populates="run",
        uselist=False,
        cascade="all, delete-orphan"
    )
    trades = relationship(
        "BacktestTrade",
        back_populates="run",
        cascade="all, delete-orphan"
    )


class BacktestResult(Base):
    """回测结果汇总表"""
    __tablename__ = "backtest_results"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(
        Integer,
        ForeignKey("backtest_runs.id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )
    total_return = Column(Numeric(10, 4))
    annual_return = Column(Numeric(10, 4))
    num_trades = Column(Integer)
    win_rate = Column(Numeric(5, 4))
    max_drawdown = Column(Numeric(10, 4))
    sharpe_ratio = Column(Numeric(10, 4))
    avg_holding_days = Column(Numeric(10, 2))
    profit_loss_ratio = Column(Numeric(10, 4))
    max_consecutive_losses = Column(Integer)
    final_capital = Column(Numeric(15, 2))

    # Relationship
    run = relationship("BacktestRun", back_populates="result")


class BacktestTrade(Base):
    """回测交易明细表"""
    __tablename__ = "backtest_trades"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(
        Integer,
        ForeignKey("backtest_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    entry_date = Column(Date, nullable=False)
    entry_price = Column(Numeric(15, 2), nullable=False)
    entry_score = Column(Numeric(5, 2))
    exit_date = Column(Date, nullable=False)
    exit_price = Column(Numeric(15, 2), nullable=False)
    exit_score = Column(Numeric(5, 2))
    pnl = Column(Numeric(15, 2))
    return_pct = Column(Numeric(10, 4))
    holding_days = Column(Integer)

    # Relationship
    run = relationship("BacktestRun", back_populates="trades")


class PriceDataCache(Base):
    """历史价格数据缓存表"""
    __tablename__ = "price_data_cache"

    symbol = Column(String(20), primary_key=True)
    date = Column(Date, primary_key=True)
    open = Column(Numeric(15, 2), nullable=False)
    high = Column(Numeric(15, 2), nullable=False)
    low = Column(Numeric(15, 2), nullable=False)
    close = Column(Numeric(15, 2), nullable=False)
    volume = Column(Numeric(20, 2), nullable=False)

    # Composite index
    __table_args__ = (
        Index("ix_price_data_symbol_date", "symbol", "date"),
    )


def init_db():
    """初始化数据库，创建所有表"""
    Base.metadata.create_all(bind=engine)
    print("✓ 数据库表创建成功！")
    print("创建的表:")
    print("  - backtest_runs (回测运行记录)")
    print("  - backtest_results (回测结果汇总)")
    print("  - backtest_trades (回测交易明细)")
    print("  - price_data_cache (历史价格数据缓存)")


def get_db():
    """获取数据库会话（用于依赖注入）"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


if __name__ == "__main__":
    print("正在初始化回测系统数据库...")
    init_db()
