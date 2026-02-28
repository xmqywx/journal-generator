# 回测系统实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为v3量化系统构建完整的回测功能，支持多交易对、参数配置、实时进度显示、K线图可视化和数据库持久化

**Architecture:**
- 后端使用Flask + Flask-SocketIO提供RESTful API和WebSocket通信
- PostgreSQL存储回测结果（3张主表 + 1张缓存表）
- 回测引擎复用MarketDetectorV2，使用数据缓存优化性能
- 前端使用TradingView Lightweight Charts绘制专业K线图，白色主题设计

**Tech Stack:** Flask, Flask-SocketIO, PostgreSQL, SQLAlchemy, TradingView Lightweight Charts, Socket.IO Client, Heroicons

---

## 前置条件

确保已安装：
- PostgreSQL（已有）
- Python 3.8+
- Node.js（用于前端资源CDN，可选）

---

## Task 1: 数据库表结构创建

**Files:**
- Create: `quant_v3/live/backtest/database.py`
- Create: `quant_v3/live/backtest/__init__.py`

**Step 1: 创建数据库连接配置**

创建 `quant_v3/live/backtest/__init__.py`:

```python
"""
回测系统模块
"""
```

创建 `quant_v3/live/backtest/database.py`:

```python
"""
数据库ORM模型定义
"""
from sqlalchemy import create_engine, Column, Integer, String, Numeric, Date, DateTime, TIMESTAMP, JSON, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

# 数据库连接URL（从环境变量读取，默认本地PostgreSQL）
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://postgres:password@localhost:5432/quant_backtest'
)

# 创建引擎
engine = create_engine(DATABASE_URL, echo=False)

# 创建Session工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 基类
Base = declarative_base()


class BacktestRun(Base):
    """回测运行记录"""
    __tablename__ = 'backtest_runs'

    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), nullable=False, index=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    initial_capital = Column(Numeric(15, 2), nullable=False)
    leverage = Column(Numeric(5, 2), nullable=False)
    fee_rate = Column(Numeric(6, 4), nullable=False)
    strategy_params = Column(JSON, nullable=False)
    status = Column(String(20), nullable=False, default='pending')
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime, nullable=True)

    # 关系
    result = relationship("BacktestResult", back_populates="run", uselist=False, cascade="all, delete-orphan")
    trades = relationship("BacktestTrade", back_populates="run", cascade="all, delete-orphan")


class BacktestResult(Base):
    """回测结果汇总"""
    __tablename__ = 'backtest_results'

    id = Column(Integer, primary_key=True)
    run_id = Column(Integer, ForeignKey('backtest_runs.id', ondelete='CASCADE'), unique=True, nullable=False)
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

    # 关系
    run = relationship("BacktestRun", back_populates="result")


class BacktestTrade(Base):
    """每笔交易明细"""
    __tablename__ = 'backtest_trades'

    id = Column(Integer, primary_key=True)
    run_id = Column(Integer, ForeignKey('backtest_runs.id', ondelete='CASCADE'), nullable=False, index=True)
    entry_date = Column(Date, nullable=False)
    entry_price = Column(Numeric(15, 2), nullable=False)
    entry_score = Column(Numeric(5, 2))
    exit_date = Column(Date, nullable=False)
    exit_price = Column(Numeric(15, 2), nullable=False)
    exit_score = Column(Numeric(5, 2))
    pnl = Column(Numeric(15, 2))
    return_pct = Column(Numeric(10, 4))
    holding_days = Column(Integer)

    # 关系
    run = relationship("BacktestRun", back_populates="trades")


class PriceDataCache(Base):
    """价格数据缓存"""
    __tablename__ = 'price_data_cache'

    symbol = Column(String(20), primary_key=True)
    date = Column(Date, primary_key=True)
    open = Column(Numeric(15, 2), nullable=False)
    high = Column(Numeric(15, 2), nullable=False)
    low = Column(Numeric(15, 2), nullable=False)
    close = Column(Numeric(15, 2), nullable=False)
    volume = Column(Numeric(20, 2), nullable=False)


# 创建索引
Index('idx_price_cache_symbol_date', PriceDataCache.symbol, PriceDataCache.date)


def init_db():
    """初始化数据库表"""
    Base.metadata.create_all(bind=engine)
    print("✅ 数据库表创建成功")


def get_db():
    """获取数据库会话（用于依赖注入）"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


if __name__ == '__main__':
    # 用于手动初始化数据库
    init_db()
```

**Step 2: 测试数据库连接和表创建**

创建数据库（如果不存在）:

```bash
# 在PostgreSQL中创建数据库
psql -U postgres -c "CREATE DATABASE quant_backtest;"
```

运行初始化脚本:

```bash
cd /Users/ying/Documents/Kris/quant
python3 -m quant_v3.live.backtest.database
```

预期输出: `✅ 数据库表创建成功`

验证表是否创建:

```bash
psql -U postgres -d quant_backtest -c "\dt"
```

预期输出: 应该看到4张表（backtest_runs, backtest_results, backtest_trades, price_data_cache）

**Step 3: 提交**

```bash
git add quant_v3/live/backtest/
git commit -m "feat(backtest): add database models and initialization

- Create SQLAlchemy ORM models for backtest system
- BacktestRun: stores backtest run metadata
- BacktestResult: stores aggregated results
- BacktestTrade: stores individual trade details
- PriceDataCache: caches historical price data
- Add init_db() function for table creation

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 2: 数据缓存服务

**Files:**
- Create: `quant_v3/live/backtest/cache_service.py`
- Create: `quant_v3/live/backtest/tests/test_cache_service.py`

**Step 1: 编写缓存服务测试**

创建测试目录和文件:

```bash
mkdir -p quant_v3/live/backtest/tests
touch quant_v3/live/backtest/tests/__init__.py
```

创建 `quant_v3/live/backtest/tests/test_cache_service.py`:

```python
"""
测试数据缓存服务
"""
import pytest
from datetime import date, timedelta
import pandas as pd
from quant_v3.live.backtest.cache_service import CacheService
from quant_v3.live.backtest.database import SessionLocal, init_db, PriceDataCache


@pytest.fixture
def db_session():
    """创建测试数据库会话"""
    init_db()
    session = SessionLocal()
    yield session
    # 清理测试数据
    session.query(PriceDataCache).delete()
    session.commit()
    session.close()


@pytest.fixture
def cache_service(db_session):
    """创建缓存服务实例"""
    return CacheService(db_session)


def test_cache_empty_initially(cache_service):
    """测试初始缓存为空"""
    start = date(2024, 1, 1)
    end = date(2024, 1, 10)
    cached = cache_service.get_cached_data('BTC-USDT', start, end)
    assert cached.empty


def test_save_and_retrieve_cache(cache_service):
    """测试保存和检索缓存"""
    # 创建测试数据
    df = pd.DataFrame({
        'date': [date(2024, 1, 1), date(2024, 1, 2)],
        'open': [50000.0, 51000.0],
        'high': [52000.0, 53000.0],
        'low': [49000.0, 50000.0],
        'close': [51000.0, 52000.0],
        'volume': [1000.0, 1200.0]
    })

    # 保存到缓存
    cache_service.save_to_cache('BTC-USDT', df)

    # 检索
    cached = cache_service.get_cached_data('BTC-USDT', date(2024, 1, 1), date(2024, 1, 2))

    assert len(cached) == 2
    assert cached.iloc[0]['close'] == 51000.0
    assert cached.iloc[1]['close'] == 52000.0


def test_get_missing_dates(cache_service, db_session):
    """测试识别缺失日期"""
    # 保存部分数据
    df = pd.DataFrame({
        'date': [date(2024, 1, 1), date(2024, 1, 3)],  # 缺少1月2日
        'open': [50000.0, 51000.0],
        'high': [52000.0, 53000.0],
        'low': [49000.0, 50000.0],
        'close': [51000.0, 52000.0],
        'volume': [1000.0, 1200.0]
    })
    cache_service.save_to_cache('BTC-USDT', df)

    # 检查缺失日期
    missing = cache_service.get_missing_dates(
        'BTC-USDT',
        date(2024, 1, 1),
        date(2024, 1, 3)
    )

    assert date(2024, 1, 2) in missing
    assert date(2024, 1, 1) not in missing
    assert date(2024, 1, 3) not in missing
```

**Step 2: 运行测试确认失败**

```bash
cd /Users/ying/Documents/Kris/quant
pytest quant_v3/live/backtest/tests/test_cache_service.py -v
```

预期输出: `ModuleNotFoundError: No module named 'quant_v3.live.backtest.cache_service'`

**Step 3: 实现缓存服务**

创建 `quant_v3/live/backtest/cache_service.py`:

```python
"""
数据缓存服务
用于缓存历史价格数据，避免重复API请求
"""
from datetime import date, timedelta
import pandas as pd
from sqlalchemy.orm import Session
from quant_v3.live.backtest.database import PriceDataCache


class CacheService:
    """价格数据缓存服务"""

    def __init__(self, db: Session):
        self.db = db

    def get_cached_data(self, symbol: str, start_date: date, end_date: date) -> pd.DataFrame:
        """
        从缓存获取数据

        Args:
            symbol: 交易对
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            pd.DataFrame: 缓存的价格数据
        """
        rows = self.db.query(PriceDataCache).filter(
            PriceDataCache.symbol == symbol,
            PriceDataCache.date >= start_date,
            PriceDataCache.date <= end_date
        ).order_by(PriceDataCache.date).all()

        if not rows:
            return pd.DataFrame()

        data = [{
            'date': row.date,
            'open': float(row.open),
            'high': float(row.high),
            'low': float(row.low),
            'close': float(row.close),
            'volume': float(row.volume)
        } for row in rows]

        return pd.DataFrame(data)

    def save_to_cache(self, symbol: str, df: pd.DataFrame):
        """
        保存数据到缓存

        Args:
            symbol: 交易对
            df: 价格数据 (包含列: date, open, high, low, close, volume)
        """
        if df.empty:
            return

        # 批量插入（使用upsert避免重复）
        records = []
        for _, row in df.iterrows():
            records.append({
                'symbol': symbol,
                'date': row['date'],
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
                'volume': float(row['volume'])
            })

        # 使用bulk_insert_mappings批量插入
        # 注意：这会跳过已存在的记录（因为主键冲突）
        try:
            self.db.bulk_insert_mappings(PriceDataCache, records)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            # 如果批量插入失败，尝试逐条插入并跳过重复
            for record in records:
                existing = self.db.query(PriceDataCache).filter_by(
                    symbol=record['symbol'],
                    date=record['date']
                ).first()
                if not existing:
                    cache_entry = PriceDataCache(**record)
                    self.db.add(cache_entry)
            self.db.commit()

    def get_missing_dates(self, symbol: str, start_date: date, end_date: date) -> list:
        """
        获取缺失的日期列表

        Args:
            symbol: 交易对
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            list: 缺失的日期列表
        """
        # 获取缓存中的日期
        cached_dates = set(
            row.date for row in self.db.query(PriceDataCache.date).filter(
                PriceDataCache.symbol == symbol,
                PriceDataCache.date >= start_date,
                PriceDataCache.date <= end_date
            ).all()
        )

        # 生成所有日期
        all_dates = []
        current = start_date
        while current <= end_date:
            all_dates.append(current)
            current += timedelta(days=1)

        # 返回缺失的日期
        return [d for d in all_dates if d not in cached_dates]

    def clear_old_cache(self, days: int = 90):
        """
        清理旧缓存数据

        Args:
            days: 保留最近N天的数据，删除更早的
        """
        cutoff_date = date.today() - timedelta(days=days)
        self.db.query(PriceDataCache).filter(
            PriceDataCache.date < cutoff_date
        ).delete()
        self.db.commit()
```

**Step 4: 运行测试确认通过**

```bash
pytest quant_v3/live/backtest/tests/test_cache_service.py -v
```

预期输出: 所有测试通过 (3 passed)

**Step 5: 提交**

```bash
git add quant_v3/live/backtest/cache_service.py quant_v3/live/backtest/tests/
git commit -m "feat(backtest): add cache service for historical data

- Implement CacheService for price data caching
- get_cached_data(): retrieve cached data
- save_to_cache(): bulk insert with conflict handling
- get_missing_dates(): identify gaps in cache
- clear_old_cache(): cleanup old data
- Add comprehensive unit tests

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 3: 回测引擎核心逻辑

**Files:**
- Create: `quant_v3/live/backtest/engine.py`
- Create: `quant_v3/live/backtest/tests/test_engine.py`

**Step 1: 编写回测引擎测试**

创建 `quant_v3/live/backtest/tests/test_engine.py`:

```python
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
    assert metrics['win_rate'] == 2/3  # 2赢1亏
    assert metrics['total_return'] == 0.125  # (2250-2000)/2000
    assert metrics['avg_holding_days'] == (30+45+20)/3


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
```

**Step 2: 运行测试确认失败**

```bash
pytest quant_v3/live/backtest/tests/test_engine.py -v
```

预期输出: `ModuleNotFoundError: No module named 'quant_v3.live.backtest.engine'`

**Step 3: 实现回测引擎**

创建 `quant_v3/live/backtest/engine.py`:

```python
"""
回测引擎
执行回测逻辑，模拟交易，计算指标
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../'))

from datetime import date, datetime, timedelta
import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from typing import Optional, Dict, List

from data.fetcher import BinanceFetcher
from quant_v3.core.market_detector_v2 import MarketDetectorV2
from quant_v3.live.backtest.cache_service import CacheService
from quant_v3.live.backtest.database import BacktestRun, BacktestResult, BacktestTrade


class BacktestEngine:
    """回测引擎"""

    def __init__(self, db: Session, socketio=None):
        """
        Args:
            db: 数据库会话
            socketio: SocketIO实例（用于推送进度）
        """
        self.db = db
        self.socketio = socketio
        self.fetcher = BinanceFetcher()
        self.cache_service = CacheService(db)

    def run_backtest(
        self,
        run_id: int,
        symbol: str,
        start_date: date,
        end_date: date,
        initial_capital: float,
        leverage: float,
        fee_rate: float,
        strategy_params: dict
    ):
        """
        执行回测

        Args:
            run_id: 回测运行ID
            symbol: 交易对
            start_date: 开始日期
            end_date: 结束日期
            initial_capital: 初始资金
            leverage: 杠杆倍数
            fee_rate: 手续费率
            strategy_params: 策略参数
        """
        try:
            # 更新状态为running
            run = self.db.query(BacktestRun).get(run_id)
            run.status = 'running'
            self.db.commit()

            # 1. 获取数据（优先缓存）
            self._emit_progress(run_id, 10, "正在获取历史数据...")
            df = self._fetch_data_with_cache(symbol, start_date, end_date)

            if df.empty or len(df) < 180:
                raise ValueError("数据不足，需要至少180天数据")

            # 2. 初始化检测器
            self._emit_progress(run_id, 20, "初始化市场检测器...")
            detector = MarketDetectorV2(
                short_period=strategy_params['periods']['short'],
                medium_period=strategy_params['periods']['medium'],
                long_period=strategy_params['periods']['long'],
                super_long_period=strategy_params['periods']['super_long']
            )

            # 3. 执行交易模拟
            self._emit_progress(run_id, 30, "开始回测模拟...")
            trades, final_capital = self._simulate_trading(
                df, detector, initial_capital, leverage, fee_rate, strategy_params, run_id
            )

            # 4. 计算指标
            self._emit_progress(run_id, 90, "计算回测指标...")
            metrics = self._calculate_metrics(trades, initial_capital, final_capital, start_date, end_date)

            # 5. 保存结果
            self._save_results(run_id, trades, metrics, final_capital)

            # 6. 更新状态
            run.status = 'completed'
            run.completed_at = datetime.utcnow()
            self.db.commit()

            self._emit_progress(run_id, 100, "回测完成")
            self._emit_completed(run_id, metrics, trades)

        except Exception as e:
            # 错误处理
            run = self.db.query(BacktestRun).get(run_id)
            run.status = 'failed'
            self.db.commit()
            self._emit_error(run_id, str(e))
            raise

    def _fetch_data_with_cache(self, symbol: str, start_date: date, end_date: date) -> pd.DataFrame:
        """
        从缓存或API获取数据

        Args:
            symbol: 交易对
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            pd.DataFrame: 价格数据
        """
        # 检查缓存
        cached_df = self.cache_service.get_cached_data(symbol, start_date, end_date)

        # 获取缺失日期
        missing_dates = self.cache_service.get_missing_dates(symbol, start_date, end_date)

        if not missing_dates:
            # 全部命中缓存
            return cached_df

        # 获取缺失数据
        # 计算需要获取的天数范围
        days = (end_date - start_date).days + 200  # 多获取一些以确保数据充足
        new_df = self.fetcher.fetch_history(symbol, timeframe='1D', days=days)

        # 转换timestamp为date
        if 'timestamp' in new_df.columns:
            new_df['date'] = pd.to_datetime(new_df['timestamp'], unit='ms').dt.date

        # 筛选日期范围
        new_df = new_df[(new_df['date'] >= start_date) & (new_df['date'] <= end_date)]

        # 保存到缓存
        if not new_df.empty:
            self.cache_service.save_to_cache(symbol, new_df)

        # 合并缓存和新数据
        if cached_df.empty:
            result_df = new_df
        else:
            result_df = pd.concat([cached_df, new_df]).drop_duplicates(subset=['date']).sort_values('date')

        return result_df.reset_index(drop=True)

    def _simulate_trading(
        self, df: pd.DataFrame, detector: MarketDetectorV2,
        initial_capital: float, leverage: float, fee_rate: float,
        strategy_params: dict, run_id: int
    ) -> tuple:
        """
        模拟交易执行

        Returns:
            (trades, final_capital)
        """
        capital = initial_capital
        position = 0  # 0=空仓, BTC数量
        entry_price = 0
        entry_date = None
        entry_score = 0

        trades = []
        total_days = len(df)

        for idx, row in df.iterrows():
            # 每10%更新进度
            progress = 30 + int((idx / total_days) * 60)
            if idx % max(1, total_days // 10) == 0:
                self._emit_progress(run_id, progress, f"处理中: {row['date']}")

            # 获取当前数据窗口
            window_df = df.iloc[:idx+1]
            if len(window_df) < 180:
                continue  # 数据不足，跳过

            # 市场检测
            result = detector.detect(window_df)
            details = result['details']
            score = details['comprehensive_score']

            current_price = row['close']
            current_date = row['date']

            # 交易逻辑
            if position == 0:
                # 空仓，检查买入信号
                buy_threshold = strategy_params['buy_threshold']
                decel_filter = strategy_params['deceleration_filter']
                drawdown_filter = strategy_params['drawdown_filter']

                if (score >= buy_threshold and
                    details['deceleration_penalty'] > decel_filter and
                    details['drawdown_penalty'] > drawdown_filter):
                    # 买入
                    capital, position = self._simulate_buy(capital, position, current_price, leverage, fee_rate)
                    entry_price = current_price
                    entry_date = current_date
                    entry_score = score

            else:
                # 持仓，检查卖出信号
                sell_threshold = strategy_params['sell_threshold']

                if score < sell_threshold:
                    # 卖出
                    capital, position = self._simulate_sell(capital, position, current_price, fee_rate)

                    # 记录交易
                    pnl = capital - initial_capital
                    return_pct = (current_price / entry_price - 1) * leverage
                    holding_days = (current_date - entry_date).days

                    trades.append({
                        'entry_date': entry_date,
                        'entry_price': entry_price,
                        'entry_score': entry_score,
                        'exit_date': current_date,
                        'exit_price': current_price,
                        'exit_score': score,
                        'pnl': pnl,
                        'return_pct': return_pct,
                        'holding_days': holding_days
                    })

                    # 重置持仓
                    position = 0
                    entry_price = 0

        # 如果最后还持仓，强制平仓
        if position > 0:
            last_price = df.iloc[-1]['close']
            last_date = df.iloc[-1]['date']
            capital, position = self._simulate_sell(capital, position, last_price, fee_rate)

            pnl = capital - initial_capital
            return_pct = (last_price / entry_price - 1) * leverage
            holding_days = (last_date - entry_date).days

            trades.append({
                'entry_date': entry_date,
                'entry_price': entry_price,
                'entry_score': entry_score,
                'exit_date': last_date,
                'exit_price': last_price,
                'exit_score': 0,  # 强制平仓，无评分
                'pnl': pnl,
                'return_pct': return_pct,
                'holding_days': holding_days
            })

        return trades, capital

    def _simulate_buy(self, capital: float, position: float, price: float, leverage: float, fee_rate: float) -> tuple:
        """
        模拟买入

        Returns:
            (new_capital, new_position)
        """
        fee = capital * fee_rate
        usable = capital - fee
        btc_amount = usable / price
        return 0, btc_amount  # 全仓买入

    def _simulate_sell(self, capital: float, position: float, price: float, fee_rate: float) -> tuple:
        """
        模拟卖出

        Returns:
            (new_capital, new_position)
        """
        gross = position * price
        fee = gross * fee_rate
        net = gross - fee
        return capital + net, 0

    def _calculate_metrics(
        self, trades: List[dict], initial_capital: float,
        final_capital: float, start_date: date, end_date: date
    ) -> dict:
        """
        计算回测指标

        Returns:
            dict: 包含所有指标的字典
        """
        if not trades:
            return {
                'total_return': 0,
                'annual_return': 0,
                'num_trades': 0,
                'win_rate': 0,
                'max_drawdown': 0,
                'sharpe_ratio': 0,
                'avg_holding_days': 0,
                'profit_loss_ratio': 0,
                'max_consecutive_losses': 0
            }

        # 基础指标
        total_return = (final_capital - initial_capital) / initial_capital

        # 年化收益
        days = (end_date - start_date).days
        years = days / 365.25
        annual_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0

        # 交易统计
        num_trades = len(trades)
        wins = [t for t in trades if t['pnl'] > 0]
        losses = [t for t in trades if t['pnl'] < 0]
        win_rate = len(wins) / num_trades if num_trades > 0 else 0

        # 平均持仓天数
        avg_holding_days = sum(t['holding_days'] for t in trades) / num_trades if num_trades > 0 else 0

        # 盈亏比
        avg_win = sum(t['pnl'] for t in wins) / len(wins) if wins else 0
        avg_loss = abs(sum(t['pnl'] for t in losses) / len(losses)) if losses else 0
        profit_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 0

        # 最大回撤（简化版：基于交易）
        max_drawdown = 0
        peak = initial_capital
        for trade in trades:
            capital_after = initial_capital + sum(t['pnl'] for t in trades[:trades.index(trade)+1])
            if capital_after > peak:
                peak = capital_after
            drawdown = (peak - capital_after) / peak if peak > 0 else 0
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        # 夏普比率（简化版）
        returns = [t['return_pct'] for t in trades]
        if returns:
            avg_return = np.mean(returns)
            std_return = np.std(returns)
            sharpe_ratio = avg_return / std_return * np.sqrt(252) if std_return > 0 else 0
        else:
            sharpe_ratio = 0

        # 最大连续亏损
        max_consecutive_losses = 0
        current_losses = 0
        for trade in trades:
            if trade['pnl'] < 0:
                current_losses += 1
                max_consecutive_losses = max(max_consecutive_losses, current_losses)
            else:
                current_losses = 0

        return {
            'total_return': round(total_return, 4),
            'annual_return': round(annual_return, 4),
            'num_trades': num_trades,
            'win_rate': round(win_rate, 4),
            'max_drawdown': round(max_drawdown, 4),
            'sharpe_ratio': round(sharpe_ratio, 4),
            'avg_holding_days': round(avg_holding_days, 2),
            'profit_loss_ratio': round(profit_loss_ratio, 4),
            'max_consecutive_losses': max_consecutive_losses
        }

    def _save_results(self, run_id: int, trades: List[dict], metrics: dict, final_capital: float):
        """保存回测结果到数据库"""
        # 保存汇总结果
        result = BacktestResult(
            run_id=run_id,
            total_return=metrics['total_return'],
            annual_return=metrics['annual_return'],
            num_trades=metrics['num_trades'],
            win_rate=metrics['win_rate'],
            max_drawdown=metrics['max_drawdown'],
            sharpe_ratio=metrics['sharpe_ratio'],
            avg_holding_days=metrics['avg_holding_days'],
            profit_loss_ratio=metrics['profit_loss_ratio'],
            max_consecutive_losses=metrics['max_consecutive_losses'],
            final_capital=final_capital
        )
        self.db.add(result)

        # 批量保存交易明细
        trade_records = [
            BacktestTrade(
                run_id=run_id,
                entry_date=t['entry_date'],
                entry_price=t['entry_price'],
                entry_score=t['entry_score'],
                exit_date=t['exit_date'],
                exit_price=t['exit_price'],
                exit_score=t['exit_score'],
                pnl=t['pnl'],
                return_pct=t['return_pct'],
                holding_days=t['holding_days']
            )
            for t in trades
        ]
        self.db.bulk_save_objects(trade_records)
        self.db.commit()

    def _emit_progress(self, run_id: int, progress: int, message: str):
        """推送进度更新"""
        if self.socketio:
            self.socketio.emit('backtest_progress', {
                'run_id': run_id,
                'progress': progress,
                'message': message
            })

    def _emit_completed(self, run_id: int, metrics: dict, trades: List[dict]):
        """推送完成消息"""
        if self.socketio:
            self.socketio.emit('backtest_completed', {
                'run_id': run_id,
                'metrics': metrics,
                'num_trades': len(trades)
            })

    def _emit_error(self, run_id: int, error: str):
        """推送错误消息"""
        if self.socketio:
            self.socketio.emit('backtest_error', {
                'run_id': run_id,
                'error': error
            })
```

**Step 4: 运行测试确认通过**

```bash
pytest quant_v3/live/backtest/tests/test_engine.py -v
```

预期输出: 测试通过

**Step 5: 提交**

```bash
git add quant_v3/live/backtest/engine.py quant_v3/live/backtest/tests/test_engine.py
git commit -m "feat(backtest): implement backtest engine core logic

- Fetch data with cache optimization
- Simulate trading with fee and leverage
- Calculate comprehensive metrics:
  - Total/annual return, win rate, max drawdown
  - Sharpe ratio, profit/loss ratio, holding days
  - Max consecutive losses
- Real-time progress emission via SocketIO
- Bulk save results to database
- Add unit tests for metrics and simulation

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 4: Flask-SocketIO集成

**Files:**
- Modify: `quant_v3/live/web_app.py`
- Modify: `quant_v3/live/requirements.txt`

**Step 1: 安装依赖**

修改 `quant_v3/live/requirements.txt`:

```
Flask==3.0.0
flask-socketio==5.3.5
python-socketio==5.10.0
eventlet==0.33.3
psycopg2-binary==2.9.9
sqlalchemy==2.0.23
```

安装:

```bash
cd quant_v3/live
source venv/bin/activate
pip install -r requirements.txt
```

**Step 2: 修改web_app.py集成SocketIO**

在 `quant_v3/live/web_app.py` 开头添加导入:

```python
from flask_socketio import SocketIO, emit
import eventlet
eventlet.monkey_patch()
```

在创建Flask app后添加SocketIO初始化:

```python
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'  # 生产环境应使用环境变量
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

trader = LiveTrader()
```

在文件末尾修改启动方式:

```python
if __name__ == '__main__':
    # 创建templates目录
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)

    print("\n" + "="*80)
    print("v3量化系统 - Web界面")
    print("="*80)
    print("\n正在启动Web服务器...")
    print("\n访问地址: http://localhost:5001")
    print("\n按 Ctrl+C 停止服务器\n")

    # 使用SocketIO运行
    socketio.run(app, host='0.0.0.0', port=5001, debug=False)
```

**Step 3: 测试SocketIO启动**

```bash
cd quant_v3/live
./start.sh
```

在浏览器访问 http://localhost:5001，确认页面正常加载。

检查终端输出，应该看到 "WebSocket transport activated"。

按 Ctrl+C 停止服务器。

**Step 4: 提交**

```bash
git add quant_v3/live/web_app.py quant_v3/live/requirements.txt
git commit -m "feat(backtest): integrate Flask-SocketIO for real-time communication

- Add flask-socketio and eventlet dependencies
- Configure SocketIO with CORS support
- Update server startup to use socketio.run()
- Enable async_mode='eventlet' for better performance

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 5: 回测API路由

**Files:**
- Create: `quant_v3/live/backtest/routes.py`
- Modify: `quant_v3/live/web_app.py`

**Step 1: 创建回测路由**

创建 `quant_v3/live/backtest/routes.py`:

```python
"""
回测系统API路由
"""
from flask import Blueprint, request, jsonify
from flask_socketio import SocketIO
from sqlalchemy.orm import Session
from datetime import datetime, date
import threading

from quant_v3.live.backtest.database import SessionLocal, BacktestRun, BacktestResult, BacktestTrade
from quant_v3.live.backtest.engine import BacktestEngine

# 创建Blueprint
backtest_bp = Blueprint('backtest', __name__, url_prefix='/api/backtest')

# SocketIO实例（将在web_app.py中设置）
socketio_instance = None


def init_routes(app, socketio):
    """
    初始化路由

    Args:
        app: Flask应用实例
        socketio: SocketIO实例
    """
    global socketio_instance
    socketio_instance = socketio

    # 注册Blueprint
    app.register_blueprint(backtest_bp)

    # 注册SocketIO事件
    @socketio.on('start_backtest')
    def handle_start_backtest(data):
        """处理开始回测事件"""
        try:
            # 验证参数
            required_fields = ['symbol', 'start_date', 'end_date', 'initial_capital',
                             'leverage', 'fee_rate', 'strategy_params']
            for field in required_fields:
                if field not in data:
                    emit('backtest_error', {'error': f'缺少参数: {field}'})
                    return

            # 创建回测记录
            db = SessionLocal()
            run = BacktestRun(
                symbol=data['symbol'],
                start_date=datetime.strptime(data['start_date'], '%Y-%m-%d').date(),
                end_date=datetime.strptime(data['end_date'], '%Y-%m-%d').date(),
                initial_capital=float(data['initial_capital']),
                leverage=float(data['leverage']),
                fee_rate=float(data['fee_rate']),
                strategy_params=data['strategy_params'],
                status='pending'
            )
            db.add(run)
            db.commit()
            db.refresh(run)
            run_id = run.id
            db.close()

            # 后台线程执行回测
            def run_backtest_async():
                db = SessionLocal()
                engine = BacktestEngine(db, socketio)
                try:
                    engine.run_backtest(
                        run_id=run_id,
                        symbol=data['symbol'],
                        start_date=datetime.strptime(data['start_date'], '%Y-%m-%d').date(),
                        end_date=datetime.strptime(data['end_date'], '%Y-%m-%d').date(),
                        initial_capital=float(data['initial_capital']),
                        leverage=float(data['leverage']),
                        fee_rate=float(data['fee_rate']),
                        strategy_params=data['strategy_params']
                    )
                except Exception as e:
                    print(f"回测错误: {e}")
                finally:
                    db.close()

            thread = threading.Thread(target=run_backtest_async)
            thread.daemon = True
            thread.start()

            # 返回run_id
            emit('backtest_started', {'run_id': run_id})

        except Exception as e:
            emit('backtest_error', {'error': str(e)})

    @socketio.on('cancel_backtest')
    def handle_cancel_backtest(data):
        """处理取消回测事件"""
        try:
            run_id = data.get('run_id')
            if not run_id:
                emit('backtest_error', {'error': '缺少run_id'})
                return

            db = SessionLocal()
            run = db.query(BacktestRun).get(run_id)
            if run:
                run.status = 'cancelled'
                db.commit()
                emit('backtest_cancelled', {'run_id': run_id})
            db.close()

        except Exception as e:
            emit('backtest_error', {'error': str(e)})


@backtest_bp.route('/history', methods=['GET'])
def get_backtest_history():
    """获取历史回测列表"""
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))

        db = SessionLocal()
        query = db.query(BacktestRun).order_by(BacktestRun.created_at.desc())

        total = query.count()
        runs = query.offset((page - 1) * per_page).limit(per_page).all()

        result = {
            'total': total,
            'page': page,
            'per_page': per_page,
            'runs': [{
                'id': run.id,
                'symbol': run.symbol,
                'start_date': run.start_date.isoformat(),
                'end_date': run.end_date.isoformat(),
                'initial_capital': float(run.initial_capital),
                'status': run.status,
                'created_at': run.created_at.isoformat(),
                'total_return': float(run.result.total_return) if run.result else None,
                'num_trades': run.result.num_trades if run.result else None
            } for run in runs]
        }

        db.close()
        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@backtest_bp.route('/<int:run_id>', methods=['GET'])
def get_backtest_detail(run_id):
    """获取回测详情"""
    try:
        db = SessionLocal()
        run = db.query(BacktestRun).get(run_id)

        if not run:
            db.close()
            return jsonify({'error': '回测记录不存在'}), 404

        result = {
            'id': run.id,
            'symbol': run.symbol,
            'start_date': run.start_date.isoformat(),
            'end_date': run.end_date.isoformat(),
            'initial_capital': float(run.initial_capital),
            'leverage': float(run.leverage),
            'fee_rate': float(run.fee_rate),
            'strategy_params': run.strategy_params,
            'status': run.status,
            'created_at': run.created_at.isoformat(),
            'completed_at': run.completed_at.isoformat() if run.completed_at else None
        }

        if run.result:
            result['metrics'] = {
                'total_return': float(run.result.total_return),
                'annual_return': float(run.result.annual_return),
                'num_trades': run.result.num_trades,
                'win_rate': float(run.result.win_rate),
                'max_drawdown': float(run.result.max_drawdown),
                'sharpe_ratio': float(run.result.sharpe_ratio),
                'avg_holding_days': float(run.result.avg_holding_days),
                'profit_loss_ratio': float(run.result.profit_loss_ratio),
                'max_consecutive_losses': run.result.max_consecutive_losses,
                'final_capital': float(run.result.final_capital)
            }

        db.close()
        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@backtest_bp.route('/<int:run_id>/trades', methods=['GET'])
def get_backtest_trades(run_id):
    """获取交易明细"""
    try:
        db = SessionLocal()
        trades = db.query(BacktestTrade).filter_by(run_id=run_id).order_by(BacktestTrade.entry_date).all()

        result = [{
            'id': t.id,
            'entry_date': t.entry_date.isoformat(),
            'entry_price': float(t.entry_price),
            'entry_score': float(t.entry_score) if t.entry_score else None,
            'exit_date': t.exit_date.isoformat(),
            'exit_price': float(t.exit_price),
            'exit_score': float(t.exit_score) if t.exit_score else None,
            'pnl': float(t.pnl),
            'return_pct': float(t.return_pct),
            'holding_days': t.holding_days
        } for t in trades]

        db.close()
        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@backtest_bp.route('/<int:run_id>', methods=['DELETE'])
def delete_backtest(run_id):
    """删除回测记录"""
    try:
        db = SessionLocal()
        run = db.query(BacktestRun).get(run_id)

        if not run:
            db.close()
            return jsonify({'error': '回测记录不存在'}), 404

        db.delete(run)
        db.commit()
        db.close()

        return jsonify({'success': True, 'message': '删除成功'})

    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

**Step 2: 集成到web_app.py**

在 `quant_v3/live/web_app.py` 中添加导入和初始化:

```python
from quant_v3.live.backtest.routes import init_routes

# 在创建socketio后添加
init_routes(app, socketio)
```

**Step 3: 测试API端点**

启动服务器:

```bash
cd quant_v3/live
./start.sh
```

测试历史列表API:

```bash
curl http://localhost:5001/api/backtest/history
```

预期输出: `{"total": 0, "page": 1, "per_page": 10, "runs": []}`

**Step 4: 提交**

```bash
git add quant_v3/live/backtest/routes.py quant_v3/live/web_app.py
git commit -m "feat(backtest): add API routes and WebSocket handlers

REST API:
- GET /api/backtest/history: list backtest runs with pagination
- GET /api/backtest/<id>: get backtest details and metrics
- GET /api/backtest/<id>/trades: get trade history
- DELETE /api/backtest/<id>: delete backtest record

WebSocket events:
- start_backtest: initiate backtest in background thread
- cancel_backtest: cancel running backtest

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 6: 前端 - 回测配置页面

**Files:**
- Create: `quant_v3/live/templates/backtest.html`
- Create: `quant_v3/live/static/backtest.js`
- Modify: `quant_v3/live/web_app.py`

**Step 1: 创建回测页面路由**

在 `quant_v3/live/web_app.py` 添加路由:

```python
@app.route('/backtest')
def backtest():
    """回测页面"""
    return render_template('backtest.html')
```

**Step 2: 创建HTML模板**

创建 `quant_v3/live/templates/backtest.html`:

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>v3量化交易系统 - 回测系统</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <script src="https://unpkg.com/lightweight-charts/dist/lightweight-charts.standalone.production.js"></script>
    <style>
        body {
            background: #FFFFFF;
            color: #1F2937;
        }
        .nav-tab {
            padding: 12px 24px;
            cursor: pointer;
            border-bottom: 3px solid transparent;
            transition: all 0.3s;
        }
        .nav-tab.active {
            border-bottom-color: #2563EB;
            color: #2563EB;
            font-weight: 600;
        }
        .symbol-card {
            cursor: pointer;
            transition: all 0.3s;
            border: 2px solid #E5E7EB;
        }
        .symbol-card.selected {
            border-color: #2563EB;
            background: #EFF6FF;
        }
        .symbol-card:hover {
            border-color: #93C5FD;
        }
        .metric-card {
            background: white;
            border: 1px solid #E5E7EB;
            border-radius: 8px;
            padding: 16px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        .chart-container {
            position: relative;
            height: 500px;
            width: 100%;
            background: white;
            border: 1px solid #E5E7EB;
            border-radius: 8px;
        }
        .modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            overflow: auto;
            background-color: rgba(0,0,0,0.5);
        }
        .modal.active {
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .modal-content {
            background-color: white;
            padding: 32px;
            border-radius: 12px;
            width: 90%;
            max-width: 500px;
            box-shadow: 0 20px 25px -5px rgba(0,0,0,0.1);
        }
        .progress-bar {
            height: 8px;
            background: #E5E7EB;
            border-radius: 4px;
            overflow: hidden;
        }
        .progress-fill {
            height: 100%;
            background: #2563EB;
            transition: width 0.3s;
        }
    </style>
</head>
<body class="min-h-screen">
    <!-- 顶部导航 -->
    <div class="bg-white border-b border-gray-200">
        <div class="container mx-auto px-4">
            <div class="flex items-center space-x-8">
                <div class="nav-tab" onclick="window.location.href='/'">实盘监控</div>
                <div class="nav-tab active">回测系统</div>
            </div>
        </div>
    </div>

    <!-- 主内容区 -->
    <div class="container mx-auto px-4 py-8">

        <!-- 回测配置面板 -->
        <div class="bg-white border border-gray-200 rounded-lg p-6 mb-8 shadow-sm">
            <h2 class="text-xl font-bold mb-6 text-gray-900">📊 回测配置</h2>

            <!-- 交易对选择 -->
            <div class="mb-6">
                <label class="block text-sm font-medium text-gray-700 mb-3">交易对选择</label>
                <div class="grid grid-cols-3 gap-4">
                    <div class="symbol-card selected rounded-lg p-4 text-center" data-symbol="BTC-USDT">
                        <div class="text-2xl mb-2">₿</div>
                        <div class="font-semibold">BTC-USDT</div>
                    </div>
                    <div class="symbol-card rounded-lg p-4 text-center" data-symbol="ETH-USDT">
                        <div class="text-2xl mb-2">Ξ</div>
                        <div class="font-semibold">ETH-USDT</div>
                    </div>
                    <div class="symbol-card rounded-lg p-4 text-center" data-symbol="BNB-USDT">
                        <div class="text-2xl mb-2">◆</div>
                        <div class="font-semibold">BNB-USDT</div>
                    </div>
                </div>
            </div>

            <!-- 时间范围 -->
            <div class="mb-6">
                <label class="block text-sm font-medium text-gray-700 mb-3">时间范围</label>
                <div class="flex items-center space-x-4 mb-3">
                    <label class="inline-flex items-center">
                        <input type="radio" name="timeRange" value="365" class="form-radio text-blue-600" checked>
                        <span class="ml-2">最近1年</span>
                    </label>
                    <label class="inline-flex items-center">
                        <input type="radio" name="timeRange" value="730" class="form-radio text-blue-600">
                        <span class="ml-2">最近2年</span>
                    </label>
                    <label class="inline-flex items-center">
                        <input type="radio" name="timeRange" value="1095" class="form-radio text-blue-600">
                        <span class="ml-2">最近3年</span>
                    </label>
                    <label class="inline-flex items-center">
                        <input type="radio" name="timeRange" value="custom" class="form-radio text-blue-600">
                        <span class="ml-2">自定义</span>
                    </label>
                </div>
                <div id="customDateRange" class="hidden flex items-center space-x-3">
                    <input type="date" id="startDate" class="px-3 py-2 border border-gray-300 rounded-lg">
                    <span>至</span>
                    <input type="date" id="endDate" class="px-3 py-2 border border-gray-300 rounded-lg">
                </div>
            </div>

            <!-- 资金配置 -->
            <div class="grid grid-cols-3 gap-4 mb-6">
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-2">初始资金 (USDT)</label>
                    <input type="number" id="initialCapital" value="2000" class="w-full px-3 py-2 border border-gray-300 rounded-lg">
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-2">杠杆倍数</label>
                    <select id="leverage" class="w-full px-3 py-2 border border-gray-300 rounded-lg">
                        <option value="1.0">1.0x</option>
                        <option value="2.0">2.0x</option>
                        <option value="3.0">3.0x</option>
                    </select>
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-2">手续费率 (%)</label>
                    <input type="number" id="feeRate" value="0.04" step="0.01" class="w-full px-3 py-2 border border-gray-300 rounded-lg">
                </div>
            </div>

            <!-- 高级参数（可折叠） -->
            <details class="mb-6">
                <summary class="cursor-pointer text-sm font-medium text-gray-700 mb-3">▸ 高级策略参数</summary>
                <div class="grid grid-cols-2 gap-4 mt-3 pl-4">
                    <div>
                        <label class="block text-sm text-gray-600 mb-2">买入阈值</label>
                        <input type="number" id="buyThreshold" value="7.5" step="0.1" class="w-full px-3 py-2 border border-gray-300 rounded-lg">
                    </div>
                    <div>
                        <label class="block text-sm text-gray-600 mb-2">卖出阈值</label>
                        <input type="number" id="sellThreshold" value="4.0" step="0.1" class="w-full px-3 py-2 border border-gray-300 rounded-lg">
                    </div>
                </div>
            </details>

            <!-- 操作按钮 -->
            <div class="flex space-x-3">
                <button id="startBacktest" class="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-semibold transition">
                    ▶ 开始回测
                </button>
                <button id="resetConfig" class="px-6 py-3 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 font-semibold transition">
                    ↻ 重置
                </button>
            </div>
        </div>

        <!-- 图表区域（初始隐藏） -->
        <div id="resultsSection" class="hidden">
            <!-- K线图 -->
            <div class="bg-white border border-gray-200 rounded-lg p-6 mb-8 shadow-sm">
                <h2 class="text-xl font-bold mb-4 text-gray-900">📈 价格走势与交易信号</h2>
                <div id="chartContainer" class="chart-container"></div>
            </div>

            <!-- 回测结果指标 -->
            <div class="bg-white border border-gray-200 rounded-lg p-6 mb-8 shadow-sm">
                <h2 class="text-xl font-bold mb-4 text-gray-900">📊 回测结果概览</h2>
                <div class="grid grid-cols-4 gap-4">
                    <div class="metric-card">
                        <div class="text-sm text-gray-500 mb-1">总收益率</div>
                        <div id="metricTotalReturn" class="text-2xl font-bold text-green-600">-</div>
                    </div>
                    <div class="metric-card">
                        <div class="text-sm text-gray-500 mb-1">年化收益率</div>
                        <div id="metricAnnualReturn" class="text-2xl font-bold text-blue-600">-</div>
                    </div>
                    <div class="metric-card">
                        <div class="text-sm text-gray-500 mb-1">交易次数</div>
                        <div id="metricNumTrades" class="text-2xl font-bold text-gray-900">-</div>
                    </div>
                    <div class="metric-card">
                        <div class="text-sm text-gray-500 mb-1">胜率</div>
                        <div id="metricWinRate" class="text-2xl font-bold text-purple-600">-</div>
                    </div>
                    <div class="metric-card">
                        <div class="text-sm text-gray-500 mb-1">最大回撤</div>
                        <div id="metricMaxDrawdown" class="text-2xl font-bold text-red-600">-</div>
                    </div>
                    <div class="metric-card">
                        <div class="text-sm text-gray-500 mb-1">夏普比率</div>
                        <div id="metricSharpe" class="text-2xl font-bold text-indigo-600">-</div>
                    </div>
                    <div class="metric-card">
                        <div class="text-sm text-gray-500 mb-1">平均持仓天数</div>
                        <div id="metricAvgHolding" class="text-2xl font-bold text-gray-900">-</div>
                    </div>
                    <div class="metric-card">
                        <div class="text-sm text-gray-500 mb-1">盈亏比</div>
                        <div id="metricProfitLoss" class="text-2xl font-bold text-teal-600">-</div>
                    </div>
                </div>
            </div>

            <!-- 交易明细表 -->
            <div class="bg-white border border-gray-200 rounded-lg p-6 mb-8 shadow-sm">
                <h2 class="text-xl font-bold mb-4 text-gray-900">📋 交易明细</h2>
                <div class="overflow-x-auto">
                    <table class="w-full">
                        <thead class="bg-gray-50 border-b border-gray-200">
                            <tr>
                                <th class="px-4 py-3 text-left text-sm font-semibold text-gray-700">日期</th>
                                <th class="px-4 py-3 text-right text-sm font-semibold text-gray-700">开仓价</th>
                                <th class="px-4 py-3 text-right text-sm font-semibold text-gray-700">平仓价</th>
                                <th class="px-4 py-3 text-right text-sm font-semibold text-gray-700">收益</th>
                                <th class="px-4 py-3 text-right text-sm font-semibold text-gray-700">持仓天数</th>
                            </tr>
                        </thead>
                        <tbody id="tradesTableBody" class="divide-y divide-gray-200">
                            <!-- 动态填充 -->
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- 历史回测记录 -->
        <div class="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
            <h2 class="text-xl font-bold mb-4 text-gray-900">🕐 历史回测记录</h2>
            <div id="historyList">
                <!-- 动态填充 -->
            </div>
        </div>
    </div>

    <!-- 进度模态框 -->
    <div id="progressModal" class="modal">
        <div class="modal-content">
            <h3 class="text-lg font-bold mb-4 text-center">⟳ 回测进行中</h3>
            <div class="progress-bar mb-3">
                <div id="progressFill" class="progress-fill" style="width: 0%"></div>
            </div>
            <div id="progressText" class="text-center text-sm text-gray-600 mb-4">准备中...</div>
            <button id="cancelBacktest" class="w-full px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700">
                取消回测
            </button>
        </div>
    </div>

    <script src="/static/backtest.js"></script>
</body>
</html>
```

由于内容过长，我将继续在下一个消息中完成剩余的任务...

**Step 3: 提交当前进度**

```bash
git add quant_v3/live/templates/backtest.html quant_v3/live/web_app.py
git commit -m "feat(backtest): add backtest UI page (part 1)

- Create backtest.html with professional white theme
- Trading pair selection (BTC/ETH/BNB)
- Time range configuration (presets + custom)
- Capital/leverage/fee configuration
- Advanced strategy parameters (collapsible)
- Results section layout (charts + metrics + trades)
- Progress modal for backtest execution

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

由于完整实现计划非常详细（还有Task 7-12待完成），我将把剩余任务保存到文件中。这样你就有了一个完整的、可执行的实现计划。

---

## Task 7: Frontend JavaScript Logic

**Files:**
- Create: `quant_v3/live/static/backtest.js`

**Step 1: Create basic Socket.IO client connection**

Create `quant_v3/live/static/backtest.js`:

```javascript
// Socket.IO connection
const socket = io();

// State management
let currentBacktestId = null;
let chart = null;

// Socket event listeners
socket.on('connect', () => {
    console.log('Connected to server');
});

socket.on('backtest_progress', (data) => {
    updateProgress(data);
});

socket.on('backtest_complete', (data) => {
    handleBacktestComplete(data);
});

socket.on('backtest_error', (data) => {
    handleBacktestError(data);
});

// Helper functions
function updateProgress(data) {
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');

    if (progressBar && progressText) {
        progressBar.style.width = `${data.progress}%`;
        progressText.textContent = data.message;
    }
}

function handleBacktestComplete(data) {
    currentBacktestId = data.backtest_id;
    hideProgressModal();
    loadBacktestResult(data.backtest_id);
}

function handleBacktestError(data) {
    hideProgressModal();
    showError(data.error);
}

function showError(message) {
    // Create toast notification
    const toast = document.createElement('div');
    toast.className = 'fixed top-4 right-4 bg-red-500 text-white px-6 py-3 rounded-lg shadow-lg z-50';
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.remove();
    }, 5000);
}

function showProgressModal() {
    const modal = document.getElementById('progress-modal');
    if (modal) {
        modal.classList.remove('hidden');
    }
}

function hideProgressModal() {
    const modal = document.getElementById('progress-modal');
    if (modal) {
        modal.classList.add('hidden');
    }
}
```

**Step 2: Verify Socket.IO connection**

Run: Open browser DevTools console and check for "Connected to server" message

Expected: Console shows connection message without errors

**Step 3: Implement backtest configuration submission**

Add to `backtest.js`:

```javascript
// Form submission
document.getElementById('start-backtest-btn').addEventListener('click', async () => {
    const config = getBacktestConfig();

    if (!validateConfig(config)) {
        return;
    }

    try {
        showProgressModal();

        const response = await fetch('/api/backtest/create', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(config)
        });

        const data = await response.json();

        if (data.success) {
            currentBacktestId = data.backtest_id;
            // Start backtest via Socket.IO
            socket.emit('start_backtest', { backtest_id: data.backtest_id });
        } else {
            throw new Error(data.error || 'Failed to create backtest');
        }
    } catch (error) {
        hideProgressModal();
        showError(error.message);
    }
});

function getBacktestConfig() {
    // Get selected symbol
    const selectedCard = document.querySelector('.symbol-card.ring-2');
    const symbol = selectedCard ? selectedCard.dataset.symbol : 'BTC/USDT';

    // Get time range
    const timeRangeType = document.getElementById('time-range-type').value;
    let startDate, endDate;

    if (timeRangeType === 'custom') {
        startDate = document.getElementById('custom-start-date').value;
        endDate = document.getElementById('custom-end-date').value;
    } else {
        const dates = getPresetDateRange(timeRangeType);
        startDate = dates.start;
        endDate = dates.end;
    }

    // Get capital and trading params
    const initialCapital = parseFloat(document.getElementById('initial-capital').value);
    const leverage = parseFloat(document.getElementById('leverage').value);
    const feeRate = parseFloat(document.getElementById('fee-rate').value);

    // Get strategy params
    const strategyParams = {
        buy_threshold: parseFloat(document.getElementById('buy-threshold').value),
        sell_threshold: parseFloat(document.getElementById('sell-threshold').value),
        stop_loss: parseFloat(document.getElementById('stop-loss').value),
        take_profit: parseFloat(document.getElementById('take-profit').value)
    };

    return {
        symbol,
        start_date: startDate,
        end_date: endDate,
        initial_capital: initialCapital,
        leverage,
        fee_rate: feeRate,
        strategy_params: strategyParams
    };
}

function validateConfig(config) {
    if (!config.symbol) {
        showError('Please select a trading pair');
        return false;
    }

    if (!config.start_date || !config.end_date) {
        showError('Please select time range');
        return false;
    }

    if (new Date(config.start_date) >= new Date(config.end_date)) {
        showError('Start date must be before end date');
        return false;
    }

    if (config.initial_capital <= 0) {
        showError('Initial capital must be greater than 0');
        return false;
    }

    if (config.leverage < 1 || config.leverage > 10) {
        showError('Leverage must be between 1x and 10x');
        return false;
    }

    return true;
}

function getPresetDateRange(preset) {
    const end = new Date();
    const start = new Date();

    switch (preset) {
        case '3m':
            start.setMonth(start.getMonth() - 3);
            break;
        case '6m':
            start.setMonth(start.getMonth() - 6);
            break;
        case '1y':
            start.setFullYear(start.getFullYear() - 1);
            break;
        case '2y':
            start.setFullYear(start.getFullYear() - 2);
            break;
        case '5y':
            start.setFullYear(start.getFullYear() - 5);
            break;
    }

    return {
        start: start.toISOString().split('T')[0],
        end: end.toISOString().split('T')[0]
    };
}
```

**Step 4: Test form submission**

Run: Fill in backtest form and click "Start Backtest" button

Expected: Progress modal appears, no console errors

**Step 5: Implement symbol card selection**

Add to `backtest.js`:

```javascript
// Symbol card selection
document.querySelectorAll('.symbol-card').forEach(card => {
    card.addEventListener('click', () => {
        // Remove selection from all cards
        document.querySelectorAll('.symbol-card').forEach(c => {
            c.classList.remove('ring-2', 'ring-blue-500');
        });

        // Add selection to clicked card
        card.classList.add('ring-2', 'ring-blue-500');
    });
});

// Time range type toggle
document.getElementById('time-range-type').addEventListener('change', (e) => {
    const customInputs = document.getElementById('custom-date-inputs');
    if (e.target.value === 'custom') {
        customInputs.classList.remove('hidden');
    } else {
        customInputs.classList.add('hidden');
    }
});

// Advanced params toggle
document.getElementById('toggle-advanced').addEventListener('click', () => {
    const advancedSection = document.getElementById('advanced-params');
    const isHidden = advancedSection.classList.contains('hidden');

    if (isHidden) {
        advancedSection.classList.remove('hidden');
    } else {
        advancedSection.classList.add('hidden');
    }
});
```

**Step 6: Test UI interactions**

Run: Test clicking symbol cards, toggling time range, toggling advanced params

Expected: UI responds correctly, selections are visible

**Step 7: Commit**

```bash
git add quant_v3/live/static/backtest.js
git commit -m "feat(backtest): add frontend JavaScript logic

- Socket.IO client connection and event handlers
- Backtest configuration form submission
- Form validation and error handling
- Symbol card selection
- Time range configuration (preset and custom)
- Advanced parameters toggle
- Progress modal management

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 8: TradingView Chart Integration

**Files:**
- Modify: `quant_v3/live/static/backtest.js`

**Step 1: Add chart initialization function**

Add to `backtest.js`:

```javascript
// Chart initialization
function initChart() {
    const chartContainer = document.getElementById('chart-container');

    if (!chartContainer) {
        console.error('Chart container not found');
        return;
    }

    chart = LightweightCharts.createChart(chartContainer, {
        width: chartContainer.clientWidth,
        height: 500,
        layout: {
            background: { color: '#ffffff' },
            textColor: '#333333',
        },
        grid: {
            vertLines: { color: '#f0f0f0' },
            horzLines: { color: '#f0f0f0' },
        },
        crosshair: {
            mode: LightweightCharts.CrosshairMode.Normal,
        },
        rightPriceScale: {
            borderColor: '#cccccc',
        },
        timeScale: {
            borderColor: '#cccccc',
            timeVisible: true,
            secondsVisible: false,
        },
    });

    // Responsive resize
    window.addEventListener('resize', () => {
        chart.applyOptions({
            width: chartContainer.clientWidth
        });
    });
}

// Call on page load
document.addEventListener('DOMContentLoaded', () => {
    initChart();
});
```

**Step 2: Verify chart initialization**

Run: Open backtest page in browser

Expected: Empty chart renders without errors, white background, grid lines visible

**Step 3: Implement candlestick series and markers**

Add to `backtest.js`:

```javascript
function renderChart(priceData, trades) {
    if (!chart) {
        initChart();
    }

    // Clear existing series
    chart.remove();
    chart = LightweightCharts.createChart(document.getElementById('chart-container'), {
        width: document.getElementById('chart-container').clientWidth,
        height: 500,
        layout: {
            background: { color: '#ffffff' },
            textColor: '#333333',
        },
        grid: {
            vertLines: { color: '#f0f0f0' },
            horzLines: { color: '#f0f0f0' },
        },
        crosshair: {
            mode: LightweightCharts.CrosshairMode.Normal,
        },
        rightPriceScale: {
            borderColor: '#cccccc',
        },
        timeScale: {
            borderColor: '#cccccc',
            timeVisible: true,
            secondsVisible: false,
        },
    });

    // Add candlestick series
    const candlestickSeries = chart.addCandlestickSeries({
        upColor: '#26a69a',
        downColor: '#ef5350',
        borderVisible: false,
        wickUpColor: '#26a69a',
        wickDownColor: '#ef5350',
    });

    // Convert price data to TradingView format
    const chartData = priceData.map(candle => ({
        time: candle.timestamp / 1000, // Convert to seconds
        open: parseFloat(candle.open),
        high: parseFloat(candle.high),
        low: parseFloat(candle.low),
        close: parseFloat(candle.close),
    }));

    candlestickSeries.setData(chartData);

    // Add trade markers
    const markers = trades.map(trade => {
        const isBuy = trade.side === 'buy';
        return {
            time: new Date(trade.timestamp).getTime() / 1000,
            position: isBuy ? 'belowBar' : 'aboveBar',
            color: isBuy ? '#2196F3' : '#e91e63',
            shape: isBuy ? 'arrowUp' : 'arrowDown',
            text: `${isBuy ? 'BUY' : 'SELL'} @ ${trade.price}`,
        };
    });

    candlestickSeries.setMarkers(markers);

    // Fit content
    chart.timeScale().fitContent();
}
```

**Step 4: Test chart rendering with mock data**

Add test function to `backtest.js`:

```javascript
// Test chart with mock data
function testChart() {
    const mockPriceData = [];
    const baseTime = new Date('2024-01-01').getTime();
    let price = 40000;

    for (let i = 0; i < 100; i++) {
        const time = baseTime + i * 86400000; // Daily candles
        const change = (Math.random() - 0.5) * 1000;
        price += change;

        const high = price + Math.random() * 500;
        const low = price - Math.random() * 500;
        const open = price - change / 2;
        const close = price + change / 2;

        mockPriceData.push({
            timestamp: time,
            open: open.toFixed(2),
            high: high.toFixed(2),
            low: low.toFixed(2),
            close: close.toFixed(2),
        });
    }

    const mockTrades = [
        { timestamp: new Date(baseTime + 10 * 86400000).toISOString(), side: 'buy', price: 41000 },
        { timestamp: new Date(baseTime + 50 * 86400000).toISOString(), side: 'sell', price: 43000 },
        { timestamp: new Date(baseTime + 70 * 86400000).toISOString(), side: 'buy', price: 42000 },
    ];

    renderChart(mockPriceData, mockTrades);
}

// Add to window for console testing
window.testChart = testChart;
```

Run: In browser console, execute `testChart()`

Expected: Chart renders with candlesticks and buy/sell markers visible

**Step 5: Integrate chart with backtest results**

Add to `backtest.js`:

```javascript
async function loadBacktestResult(backtestId) {
    try {
        // Fetch backtest details
        const response = await fetch(`/api/backtest/${backtestId}`);
        const data = await response.json();

        if (!data.success) {
            throw new Error(data.error || 'Failed to load backtest result');
        }

        // Render chart
        renderChart(data.price_data, data.trades);

        // Display metrics
        displayMetrics(data.result);

        // Display trade details
        displayTrades(data.trades);

        // Show results section
        document.getElementById('results-section').classList.remove('hidden');
    } catch (error) {
        showError(error.message);
    }
}

function displayMetrics(result) {
    document.getElementById('total-return').textContent = `${result.total_return.toFixed(2)}%`;
    document.getElementById('annual-return').textContent = `${result.annual_return.toFixed(2)}%`;
    document.getElementById('sharpe-ratio').textContent = result.sharpe_ratio.toFixed(2);
    document.getElementById('max-drawdown').textContent = `${result.max_drawdown.toFixed(2)}%`;
    document.getElementById('win-rate').textContent = `${result.win_rate.toFixed(2)}%`;
    document.getElementById('profit-loss-ratio').textContent = result.profit_loss_ratio.toFixed(2);
    document.getElementById('num-trades').textContent = result.num_trades;
    document.getElementById('final-capital').textContent = `$${result.final_capital.toFixed(2)}`;
}

function displayTrades(trades) {
    const tbody = document.getElementById('trades-table-body');
    tbody.innerHTML = '';

    trades.forEach(trade => {
        const row = document.createElement('tr');
        row.className = 'border-b';

        const sideClass = trade.side === 'buy' ? 'text-blue-600' : 'text-pink-600';
        const pnlClass = trade.pnl >= 0 ? 'text-green-600' : 'text-red-600';

        row.innerHTML = `
            <td class="px-4 py-3 text-sm">${new Date(trade.timestamp).toLocaleString('zh-CN')}</td>
            <td class="px-4 py-3 text-sm font-medium ${sideClass}">${trade.side.toUpperCase()}</td>
            <td class="px-4 py-3 text-sm">$${trade.price.toFixed(2)}</td>
            <td class="px-4 py-3 text-sm">${trade.quantity.toFixed(4)}</td>
            <td class="px-4 py-3 text-sm ${pnlClass}">${trade.pnl ? `$${trade.pnl.toFixed(2)}` : '-'}</td>
            <td class="px-4 py-3 text-sm">${trade.signal_score.toFixed(2)}</td>
        `;

        tbody.appendChild(row);
    });
}
```

**Step 6: Test complete flow**

Run: Complete backtest and verify chart loads with actual data

Expected: Chart shows K-lines with buy/sell markers, metrics displayed, trade table populated

**Step 7: Commit**

```bash
git add quant_v3/live/static/backtest.js
git commit -m "feat(backtest): integrate TradingView chart with markers

- Initialize TradingView Lightweight Charts
- Render candlestick series with price data
- Add buy/sell markers on chart
- Display backtest metrics in dashboard
- Populate trade details table
- Responsive chart resizing

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 9: Backtest History Management

**Files:**
- Modify: `quant_v3/live/static/backtest.js`
- Modify: `quant_v3/live/templates/backtest.html`

**Step 1: Add history list UI to template**

Add to `backtest.html` before closing `</body>` tag:

```html
<!-- History Section -->
<div class="mt-8">
    <div class="flex items-center justify-between mb-4">
        <h2 class="text-xl font-semibold text-gray-900">Backtest History</h2>
        <button id="refresh-history-btn" class="px-4 py-2 text-sm text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors">
            <svg class="w-4 h-4 inline-block mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
            </svg>
            Refresh
        </button>
    </div>

    <div id="history-list" class="space-y-3">
        <!-- History items will be inserted here -->
    </div>
</div>
```

**Step 2: Implement history loading**

Add to `backtest.js`:

```javascript
// Load backtest history
async function loadHistory() {
    try {
        const response = await fetch('/api/backtest/list');
        const data = await response.json();

        if (!data.success) {
            throw new Error(data.error || 'Failed to load history');
        }

        displayHistory(data.backtests);
    } catch (error) {
        showError(error.message);
    }
}

function displayHistory(backtests) {
    const historyList = document.getElementById('history-list');
    historyList.innerHTML = '';

    if (backtests.length === 0) {
        historyList.innerHTML = `
            <div class="text-center py-12 text-gray-500">
                <svg class="w-16 h-16 mx-auto mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                </svg>
                <p>No backtest history yet</p>
                <p class="text-sm mt-2">Run your first backtest to see results here</p>
            </div>
        `;
        return;
    }

    backtests.forEach(backtest => {
        const item = createHistoryItem(backtest);
        historyList.appendChild(item);
    });
}

function createHistoryItem(backtest) {
    const div = document.createElement('div');
    div.className = 'bg-white border rounded-lg p-4 hover:shadow-md transition-shadow cursor-pointer';

    const returnClass = backtest.result.total_return >= 0 ? 'text-green-600' : 'text-red-600';
    const statusClass = backtest.status === 'completed' ? 'bg-green-100 text-green-800' :
                       backtest.status === 'running' ? 'bg-blue-100 text-blue-800' :
                       'bg-red-100 text-red-800';

    div.innerHTML = `
        <div class="flex items-center justify-between mb-2">
            <div class="flex items-center space-x-3">
                <span class="text-lg font-semibold">${backtest.symbol}</span>
                <span class="px-2 py-1 text-xs rounded ${statusClass}">${backtest.status}</span>
            </div>
            <div class="flex items-center space-x-2">
                <button class="view-btn p-2 text-gray-600 hover:text-blue-600 transition-colors" data-id="${backtest.id}">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path>
                    </svg>
                </button>
                <button class="delete-btn p-2 text-gray-600 hover:text-red-600 transition-colors" data-id="${backtest.id}">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                    </svg>
                </button>
            </div>
        </div>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
            <div>
                <span class="text-gray-500">Period:</span>
                <p class="font-medium">${backtest.start_date} ~ ${backtest.end_date}</p>
            </div>
            <div>
                <span class="text-gray-500">Return:</span>
                <p class="font-medium ${returnClass}">${backtest.result.total_return.toFixed(2)}%</p>
            </div>
            <div>
                <span class="text-gray-500">Trades:</span>
                <p class="font-medium">${backtest.result.num_trades}</p>
            </div>
            <div>
                <span class="text-gray-500">Created:</span>
                <p class="font-medium">${new Date(backtest.created_at).toLocaleDateString('zh-CN')}</p>
            </div>
        </div>
    `;

    // Add event listeners
    div.querySelector('.view-btn').addEventListener('click', (e) => {
        e.stopPropagation();
        loadBacktestResult(backtest.id);
    });

    div.querySelector('.delete-btn').addEventListener('click', (e) => {
        e.stopPropagation();
        confirmDelete(backtest.id);
    });

    div.addEventListener('click', () => {
        loadBacktestResult(backtest.id);
    });

    return div;
}

// Delete backtest
async function confirmDelete(backtestId) {
    if (!confirm('Are you sure you want to delete this backtest?')) {
        return;
    }

    try {
        const response = await fetch(`/api/backtest/${backtestId}`, {
            method: 'DELETE'
        });

        const data = await response.json();

        if (data.success) {
            loadHistory(); // Refresh list
        } else {
            throw new Error(data.error || 'Failed to delete backtest');
        }
    } catch (error) {
        showError(error.message);
    }
}

// Event listeners
document.getElementById('refresh-history-btn').addEventListener('click', loadHistory);

// Load history on page load
document.addEventListener('DOMContentLoaded', () => {
    loadHistory();
});
```

**Step 3: Test history list**

Run: Open backtest page and verify history loads

Expected: History list displays all backtests, empty state shows when no data

**Step 4: Test view and delete buttons**

Run: Click view button on history item

Expected: Results section loads with chart and metrics

Run: Click delete button on history item

Expected: Confirmation dialog appears, item removed after confirming

**Step 5: Commit**

```bash
git add quant_v3/live/templates/backtest.html quant_v3/live/static/backtest.js
git commit -m "feat(backtest): add history management UI

- Display backtest history list with summary
- View button to load historical results
- Delete button with confirmation
- Refresh button to reload list
- Empty state for no history
- Color-coded returns (green/red)
- Status badges for backtest state

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 10: Database Configuration

**Files:**
- Create: `quant_v3/live/.env.example`
- Modify: `.gitignore`
- Modify: `quant_v3/live/backtest/database.py`

**Step 1: Create environment variable template**

Create `quant_v3/live/.env.example`:

```bash
# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/quant_v3

# Flask Configuration
FLASK_ENV=development
SECRET_KEY=your-secret-key-here

# Backtest Configuration
MAX_CONCURRENT_BACKTESTS=3
CACHE_EXPIRY_DAYS=30
```

**Step 2: Update .gitignore**

Add to `.gitignore`:

```
# Environment variables
.env
.env.local

# Database
*.db
*.sqlite

# Backtest cache
quant_v3/live/backtest/cache/
```

**Step 3: Add environment loading to database.py**

Modify `quant_v3/live/backtest/database.py`:

```python
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Load environment variables
load_dotenv()

# Get database URL from environment
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://localhost:5432/quant_v3')

# Create engine
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=os.getenv('FLASK_ENV') == 'development'
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

# ... (rest of the models stay the same)
```

**Step 4: Create database initialization script**

Create `quant_v3/live/backtest/init_db.py`:

```python
"""Database initialization script."""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from quant_v3.live.backtest.database import Base, engine

def init_database():
    """Create all database tables."""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✓ Database tables created successfully")

if __name__ == '__main__':
    init_database()
```

**Step 5: Test database initialization**

Run:
```bash
cd quant_v3/live
cp .env.example .env
# Edit .env with your database credentials
python -m backtest.init_db
```

Expected: Output shows "✓ Database tables created successfully"

**Step 6: Verify tables in PostgreSQL**

Run:
```bash
psql -U username -d quant_v3 -c "\dt"
```

Expected: Lists tables: backtest_runs, backtest_results, backtest_trades, price_data_cache

**Step 7: Commit**

```bash
git add quant_v3/live/.env.example quant_v3/live/backtest/database.py quant_v3/live/backtest/init_db.py .gitignore
git commit -m "feat(backtest): add database configuration and initialization

- Environment variable template (.env.example)
- Load DATABASE_URL from environment
- Database initialization script
- Update .gitignore for env files
- SQLAlchemy engine with connection pooling

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 11: Integration Tests

**Files:**
- Create: `quant_v3/live/tests/test_backtest_integration.py`

**Step 1: Create integration test file**

Create `quant_v3/live/tests/test_backtest_integration.py`:

```python
"""Integration tests for backtest system."""
import pytest
import asyncio
from datetime import date, datetime, timedelta
from decimal import Decimal
from quant_v3.live.backtest.database import SessionLocal, BacktestRun, BacktestResult, BacktestTrade
from quant_v3.live.backtest.engine import BacktestEngine
from quant_v3.live.backtest.cache_service import CacheService

@pytest.fixture
def db_session():
    """Create a test database session."""
    session = SessionLocal()
    yield session
    session.close()

@pytest.fixture
def cache_service():
    """Create cache service instance."""
    return CacheService()

@pytest.fixture
def backtest_engine(cache_service):
    """Create backtest engine instance."""
    # Mock SocketIO for testing
    class MockSocketIO:
        def emit(self, event, data):
            pass

    return BacktestEngine(cache_service, MockSocketIO())

@pytest.mark.integration
def test_full_backtest_flow(db_session, backtest_engine):
    """Test complete backtest workflow from creation to results."""
    # Create backtest run
    backtest = BacktestRun(
        symbol='BTC/USDT',
        start_date=date.today() - timedelta(days=90),
        end_date=date.today(),
        initial_capital=Decimal('10000'),
        leverage=Decimal('1.0'),
        fee_rate=Decimal('0.001'),
        strategy_params={
            'buy_threshold': 7.5,
            'sell_threshold': 3.0,
            'stop_loss': 0.05,
            'take_profit': 0.15
        },
        status='pending'
    )

    db_session.add(backtest)
    db_session.commit()

    assert backtest.id is not None

    # Run backtest
    result = asyncio.run(backtest_engine.run_backtest(backtest.id))

    assert result is not None
    assert result.backtest_id == backtest.id
    assert result.num_trades >= 0
    assert result.final_capital > 0

    # Verify trades were created
    trades = db_session.query(BacktestTrade).filter_by(backtest_id=backtest.id).all()
    assert len(trades) == result.num_trades

    # Verify status updated
    db_session.refresh(backtest)
    assert backtest.status == 'completed'

@pytest.mark.integration
def test_cache_service_integration(cache_service, db_session):
    """Test cache service with database."""
    symbol = 'ETH/USDT'
    start_date = date.today() - timedelta(days=30)
    end_date = date.today()

    # First fetch - should hit API
    data1 = cache_service.get_price_data(symbol, start_date, end_date)
    assert len(data1) > 0

    # Second fetch - should hit cache
    data2 = cache_service.get_price_data(symbol, start_date, end_date)
    assert data1 == data2

    # Verify cache entry in database
    from quant_v3.live.backtest.database import PriceDataCache
    cache_entry = db_session.query(PriceDataCache).filter_by(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date
    ).first()

    assert cache_entry is not None
    assert cache_entry.price_data == data1

@pytest.mark.integration
def test_api_endpoints(client):
    """Test backtest API endpoints."""
    # Create backtest
    response = client.post('/api/backtest/create', json={
        'symbol': 'BTC/USDT',
        'start_date': '2024-01-01',
        'end_date': '2024-03-01',
        'initial_capital': 10000,
        'leverage': 1.0,
        'fee_rate': 0.001,
        'strategy_params': {
            'buy_threshold': 7.5,
            'sell_threshold': 3.0
        }
    })

    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert 'backtest_id' in data

    backtest_id = data['backtest_id']

    # List backtests
    response = client.get('/api/backtest/list')
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert len(data['backtests']) > 0

    # Get specific backtest
    response = client.get(f'/api/backtest/{backtest_id}')
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert data['backtest']['id'] == backtest_id

    # Delete backtest
    response = client.delete(f'/api/backtest/{backtest_id}')
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True

@pytest.fixture
def client():
    """Create Flask test client."""
    from quant_v3.live.web_app import app
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.mark.integration
def test_socketio_events(socketio_client):
    """Test SocketIO event handling."""
    # Connect
    assert socketio_client.is_connected()

    # Start backtest
    socketio_client.emit('start_backtest', {'backtest_id': 1})

    # Receive progress events
    received = socketio_client.get_received()
    assert any(event['name'] == 'backtest_progress' for event in received)

    # Should eventually receive complete or error
    # (This test assumes backtest completes quickly or is mocked)

@pytest.fixture
def socketio_client():
    """Create SocketIO test client."""
    from quant_v3.live.web_app import app, socketio
    client = socketio.test_client(app)
    yield client
    client.disconnect()
```

**Step 2: Run integration tests**

Run:
```bash
cd quant_v3/live
pytest tests/test_backtest_integration.py -v -m integration
```

Expected: All integration tests pass

**Step 3: Create test configuration**

Create `quant_v3/live/pytest.ini`:

```ini
[pytest]
markers =
    unit: Unit tests (fast, no external dependencies)
    integration: Integration tests (requires database)
    slow: Slow tests (may take >10s)

testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
```

**Step 4: Run all tests**

Run:
```bash
pytest tests/ -v
```

Expected: All tests pass (unit + integration)

**Step 5: Commit**

```bash
git add quant_v3/live/tests/test_backtest_integration.py quant_v3/live/pytest.ini
git commit -m "test(backtest): add comprehensive integration tests

- Full backtest workflow test
- Cache service database integration
- API endpoint tests (create, list, get, delete)
- SocketIO event handling tests
- Pytest configuration with markers
- Test fixtures for db session, engine, client

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 12: Documentation and Final Acceptance

**Files:**
- Create: `quant_v3/live/docs/BACKTEST_GUIDE.md`
- Modify: `quant_v3/live/README.md`

**Step 1: Create backtest user guide**

Create `quant_v3/live/docs/BACKTEST_GUIDE.md`:

```markdown
# Backtest System User Guide

## Overview

The backtest system allows you to test your trading strategies against historical data before deploying them live. This helps validate strategy performance and optimize parameters.

## Features

- **Multiple Trading Pairs**: BTC/USDT, ETH/USDT, BNB/USDT
- **Flexible Time Ranges**: Preset (3m, 6m, 1y, 2y, 5y) or custom dates
- **TradingView Charts**: Professional K-line visualization with buy/sell markers
- **Comprehensive Metrics**: Total return, annual return, Sharpe ratio, max drawdown, win rate, P/L ratio
- **Real-time Progress**: WebSocket-based progress updates during backtest execution
- **History Management**: Save, view, and compare backtest results
- **Data Caching**: Optimized performance for repeated backtests

## Getting Started

### 1. Access the Backtest Page

Navigate to: `http://localhost:5000/backtest`

### 2. Configure Your Backtest

#### Select Trading Pair
Click on one of the three trading pair cards:
- BTC/USDT (Bitcoin)
- ETH/USDT (Ethereum)
- BNB/USDT (Binance Coin)

#### Choose Time Range
Select a preset period or choose custom dates:
- **Presets**: 3 months, 6 months, 1 year, 2 years, 5 years
- **Custom**: Pick any start and end date

#### Set Capital and Trading Parameters
- **Initial Capital**: Starting balance (default: $10,000)
- **Leverage**: Multiplier for position size (1x-10x, default: 1x)
- **Fee Rate**: Trading fee percentage (default: 0.1%)

#### Advanced Strategy Parameters (Optional)
Click "Advanced Parameters" to configure:
- **Buy Threshold**: Minimum score to trigger buy (default: 7.5)
- **Sell Threshold**: Maximum score to trigger sell (default: 3.0)
- **Stop Loss**: Maximum acceptable loss (default: 5%)
- **Take Profit**: Target profit level (default: 15%)

### 3. Run the Backtest

Click **"Start Backtest"** button. A progress modal will show:
- Data fetching progress
- Analysis progress
- Trade simulation progress

### 4. View Results

After completion, the results section displays:

#### TradingView Chart
- Candlestick chart with historical price data
- Buy signals marked with blue up arrows
- Sell signals marked with pink down arrows
- Hover over markers to see trade details

#### Performance Metrics
- **Total Return**: Overall profit/loss percentage
- **Annual Return**: Annualized return rate
- **Sharpe Ratio**: Risk-adjusted return (>1 is good, >2 is excellent)
- **Max Drawdown**: Largest peak-to-trough decline
- **Win Rate**: Percentage of profitable trades
- **P/L Ratio**: Average profit vs average loss
- **Number of Trades**: Total trades executed
- **Final Capital**: Ending balance

#### Trade Details Table
Complete list of all trades with:
- Timestamp
- Side (BUY/SELL)
- Price
- Quantity
- P/L (for closing trades)
- Signal Score

## Managing Backtest History

### View Past Backtests
All completed backtests are saved and displayed in the "Backtest History" section below the configuration form.

Each history item shows:
- Trading pair and status
- Date range
- Total return
- Number of trades
- Creation date

### Load Historical Results
Click the **eye icon** or click on the history item to reload its results into the chart and metrics sections.

### Delete Backtests
Click the **trash icon** to permanently delete a backtest (confirmation required).

### Refresh List
Click the **Refresh** button to reload the history list.

## Understanding the Metrics

### Total Return
```
Total Return = (Final Capital - Initial Capital) / Initial Capital × 100%
```

### Sharpe Ratio
Risk-adjusted return metric. Formula:
```
Sharpe Ratio = (Average Return - Risk-free Rate) / Standard Deviation of Returns
```
- **<0**: Losing money
- **0-1**: Suboptimal, high risk for return
- **1-2**: Good, acceptable risk/reward
- **2-3**: Very good
- **>3**: Excellent, but verify data quality

### Max Drawdown
Largest percentage drop from peak to trough:
```
Max Drawdown = (Trough Value - Peak Value) / Peak Value × 100%
```
Lower is better. Indicates worst-case loss scenario.

## Tips for Effective Backtesting

### 1. Test Multiple Time Periods
- Bull markets (e.g., 2020-2021)
- Bear markets (e.g., 2022)
- Ranging markets (e.g., 2019)

### 2. Compare Different Pairs
Test the same strategy on BTC, ETH, and BNB to see consistency.

### 3. Optimize Parameters Gradually
Change one parameter at a time to understand its impact.

### 4. Watch for Overfitting
If a strategy works perfectly on one period but fails on others, it may be overfitted.

### 5. Consider Transaction Costs
Higher fee rates significantly impact profitability, especially for frequent trading.

## Troubleshooting

### Backtest Takes Too Long
- Reduce time range
- Check internet connection (data fetching may be slow)
- Verify database connection

### No Trades Generated
- Lower buy_threshold
- Check if market conditions matched strategy criteria
- Verify signal generation logic

### Unrealistic Returns
- Check leverage settings (high leverage amplifies both gains and losses)
- Verify fee rate is realistic (0.1% is typical for spot trading)
- Review individual trades for anomalies

## Technical Details

### Data Source
Historical price data is fetched from Binance API with 1-day candles.

### Caching
Price data is cached in PostgreSQL to speed up subsequent backtests with overlapping date ranges.

### Signal Generation
Uses MarketDetectorV2 to generate buy/sell signals based on multi-timeframe trend analysis.

### Trade Simulation
Simulates realistic trading:
- Buys executed at signal price
- Sells executed at signal price or stop-loss/take-profit levels
- Fees deducted from each trade
- Leverage applied to position sizing

## API Reference

### Create Backtest
```http
POST /api/backtest/create
Content-Type: application/json

{
  "symbol": "BTC/USDT",
  "start_date": "2024-01-01",
  "end_date": "2024-03-01",
  "initial_capital": 10000,
  "leverage": 1.0,
  "fee_rate": 0.001,
  "strategy_params": {
    "buy_threshold": 7.5,
    "sell_threshold": 3.0,
    "stop_loss": 0.05,
    "take_profit": 0.15
  }
}
```

### List Backtests
```http
GET /api/backtest/list
```

### Get Backtest Details
```http
GET /api/backtest/{backtest_id}
```

### Delete Backtest
```http
DELETE /api/backtest/{backtest_id}
```

### WebSocket Events

**Client to Server:**
```javascript
socket.emit('start_backtest', { backtest_id: 123 });
```

**Server to Client:**
```javascript
socket.on('backtest_progress', (data) => {
  // data: { progress: 50, message: 'Analyzing data...' }
});

socket.on('backtest_complete', (data) => {
  // data: { backtest_id: 123 }
});

socket.on('backtest_error', (data) => {
  // data: { error: 'Error message' }
});
```

## Support

For issues or questions, please check:
1. Browser console for JavaScript errors
2. Flask server logs for backend errors
3. Database connection status
4. Binance API rate limits

---

Built with ❤️ for better trading decisions
```

**Step 2: Update main README**

Add to `quant_v3/live/README.md`:

```markdown
## Backtest System

The V3 live trading system includes a comprehensive backtesting module for strategy validation.

### Quick Start

1. **Setup Database**
   ```bash
   cp .env.example .env
   # Edit .env with your PostgreSQL credentials
   python -m backtest.init_db
   ```

2. **Start Server**
   ```bash
   ./start.sh
   ```

3. **Access Backtest UI**
   Navigate to: http://localhost:5000/backtest

### Features

- Test strategies on BTC/USDT, ETH/USDT, BNB/USDT
- TradingView charts with buy/sell markers
- Comprehensive performance metrics
- Real-time progress tracking
- Backtest history management

For detailed usage instructions, see [Backtest Guide](docs/BACKTEST_GUIDE.md).

### Architecture

- **Backend**: Flask + Flask-SocketIO + PostgreSQL
- **Frontend**: Vanilla JS + TradingView Lightweight Charts + Tailwind CSS
- **Data**: Binance historical API with PostgreSQL caching
- **Strategy**: MarketDetectorV2 signal generation

### Running Tests

```bash
# Unit tests only
pytest tests/ -v -m "not integration"

# Integration tests (requires database)
pytest tests/ -v -m integration

# All tests
pytest tests/ -v
```
```

**Step 3: Perform final acceptance test**

Run complete acceptance test:

```bash
# 1. Database initialization
cd quant_v3/live
python -m backtest.init_db

# 2. Run all tests
pytest tests/ -v

# 3. Start server
./start.sh

# 4. Manual UI test
# - Open http://localhost:5000/backtest
# - Create backtest (BTC/USDT, last 3 months, $10k capital)
# - Verify progress modal shows
# - Verify results load (chart + metrics + trades)
# - Verify history list shows new entry
# - View historical backtest
# - Delete a backtest
# - Refresh history
```

Expected: All automated tests pass, manual UI test completes without errors

**Step 4: Document deployment**

Add deployment section to `BACKTEST_GUIDE.md`:

```markdown
## Deployment

### Production Checklist

- [ ] Set `FLASK_ENV=production` in `.env`
- [ ] Use strong `SECRET_KEY` in `.env`
- [ ] Configure PostgreSQL with production credentials
- [ ] Set up database backups
- [ ] Configure reverse proxy (Nginx) for WebSocket support
- [ ] Enable SSL/TLS certificates
- [ ] Set `MAX_CONCURRENT_BACKTESTS` based on server capacity
- [ ] Configure `CACHE_EXPIRY_DAYS` for data retention
- [ ] Set up monitoring and logging
- [ ] Test WebSocket connection through proxy

### Nginx Configuration Example

```nginx
location /socket.io {
    proxy_pass http://127.0.0.1:5000/socket.io;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_cache_bypass $http_upgrade;
}
```

### Database Maintenance

```bash
# Vacuum database
psql -U username -d quant_v3 -c "VACUUM ANALYZE;"

# Clean old cache entries
python -c "from backtest.cache_service import CacheService; CacheService().clean_old_cache()"
```
```

**Step 5: Final verification**

Run final checklist:

```bash
# Verify all files exist
ls -la quant_v3/live/backtest/
ls -la quant_v3/live/static/backtest.js
ls -la quant_v3/live/templates/backtest.html
ls -la quant_v3/live/docs/BACKTEST_GUIDE.md

# Verify database tables
psql -U username -d quant_v3 -c "\d backtest_runs"

# Verify tests pass
pytest tests/ -v

# Verify server starts
./start.sh
# Check http://localhost:5000/backtest loads
```

Expected: All files present, database accessible, tests pass, server runs

**Step 6: Commit documentation**

```bash
git add quant_v3/live/docs/BACKTEST_GUIDE.md quant_v3/live/README.md
git commit -m "docs(backtest): add comprehensive documentation

- Complete user guide with examples
- API reference documentation
- Metrics explanation
- Troubleshooting guide
- Deployment checklist
- Update main README with backtest section

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

**Step 7: Final commit and summary**

```bash
git log --oneline | head -12
```

Expected: Shows all 12 commits for Tasks 1-12

---

## Implementation Complete

All 12 tasks have been detailed with:
- ✅ Exact file paths for every file to create or modify
- ✅ Complete code implementations (no placeholders)
- ✅ Step-by-step verification commands
- ✅ Expected outputs for each test
- ✅ Git commit messages for each task
- ✅ TDD approach (test before implement where applicable)
- ✅ Professional white theme UI with Heroicons
- ✅ PostgreSQL database with caching optimization
- ✅ Flask-SocketIO for real-time updates
- ✅ TradingView Lightweight Charts integration
- ✅ Comprehensive testing strategy
- ✅ Complete documentation

## Next Steps

**Option 1: Subagent-Driven Development (this session)**
- Stay in current session
- Dispatch fresh subagent per task
- Two-stage review after each: spec compliance → code quality
- Fast iteration with review checkpoints

**Option 2: Parallel Session (separate)**
- Open new session with executing-plans skill
- Batch execution with periodic checkpoints
- Allows you to continue other work in this session

Which execution approach would you like to use?
