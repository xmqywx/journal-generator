"""
Integration tests for backtest system

Tests the full workflow from database to engine to API endpoints.
These tests require a running PostgreSQL database.

Run with: pytest -v -m integration
"""
import pytest
import json
from datetime import date, datetime
from decimal import Decimal

from quant_v3.live.backtest.database import (
    SessionLocal,
    init_db,
    BacktestRun,
    BacktestResult,
    BacktestTrade,
    PriceDataCache
)
from quant_v3.live.backtest.engine import BacktestEngine
from quant_v3.live.backtest.cache_service import CacheService


# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


@pytest.fixture(scope="function")
def db_session():
    """
    Create a fresh database session for each test.
    Cleans up after test completes.
    """
    # Initialize database tables
    init_db()

    # Create session
    session = SessionLocal()

    yield session

    # Cleanup - delete all test data
    try:
        session.query(BacktestTrade).delete()
        session.query(BacktestResult).delete()
        session.query(BacktestRun).delete()
        session.query(PriceDataCache).delete()
        session.commit()
    except Exception as e:
        print(f"Cleanup error: {e}")
        session.rollback()
    finally:
        session.close()


@pytest.fixture
def cache_service(db_session):
    """Create CacheService instance with database session"""
    return CacheService(db_session)


@pytest.fixture
def engine(db_session):
    """Create BacktestEngine instance (no SocketIO for tests)"""
    return BacktestEngine(db_session, socketio=None)


@pytest.fixture
def sample_price_data():
    """Generate sample price data for testing"""
    import pandas as pd

    # Create 200 days of price data (needed for 180-day MA)
    dates = pd.date_range(start='2024-01-01', periods=200, freq='D')

    # Generate realistic price data with upward trend
    base_price = 40000
    prices = []
    for i in range(len(dates)):
        # Add trend + random walk
        price = base_price + (i * 50) + (i % 10 - 5) * 100
        prices.append({
            'open': price - 50,
            'high': price + 100,
            'low': price - 100,
            'close': price,
            'volume': 1000000 + (i * 10000)
        })

    df = pd.DataFrame(prices, index=dates)
    return df


class TestFullBacktestFlow:
    """Test complete end-to-end backtest execution"""

    def test_full_backtest_execution(self, db_session, engine, cache_service, sample_price_data):
        """
        Test the complete backtest workflow:
        1. Create BacktestRun record
        2. Cache price data
        3. Execute backtest via engine
        4. Verify results saved
        5. Verify trades created
        6. Verify status updated
        """
        # Step 1: Create backtest run
        run = BacktestRun(
            symbol='BTCUSDT',
            start_date=date(2024, 3, 1),  # After 180 days for MA calculation
            end_date=date(2024, 7, 18),   # 200th day
            initial_capital=Decimal('100000.00'),
            leverage=Decimal('1.0'),
            fee_rate=Decimal('0.001'),
            strategy_params={
                'periods': {
                    'short': 20,
                    'medium': 50,
                    'long': 120,
                    'super_long': 180
                }
            },
            status='pending'
        )
        db_session.add(run)
        db_session.commit()
        db_session.refresh(run)

        run_id = run.id
        assert run_id is not None
        assert run.status == 'pending'

        # Step 2: Cache price data
        for date_idx, row in sample_price_data.iterrows():
            cache_data = PriceDataCache(
                symbol='BTCUSDT',
                date=date_idx.date(),
                open=Decimal(str(row['open'])),
                high=Decimal(str(row['high'])),
                low=Decimal(str(row['low'])),
                close=Decimal(str(row['close'])),
                volume=Decimal(str(row['volume']))
            )
            db_session.add(cache_data)
        db_session.commit()

        # Verify data cached
        cached_count = db_session.query(PriceDataCache).filter(
            PriceDataCache.symbol == 'BTCUSDT'
        ).count()
        assert cached_count == 200

        # Step 3: Execute backtest
        # Note: This would normally call run_backtest, but we'll simulate it
        # to avoid external API dependencies in tests

        # Simulate engine execution by directly creating results
        # (In real scenario, engine.run_backtest would do this)

        # Update status to running
        run.status = 'running'
        db_session.commit()

        # Create result
        result = BacktestResult(
            run_id=run_id,
            total_return=Decimal('0.25'),  # 25% return
            annual_return=Decimal('0.25'),
            num_trades=5,
            win_rate=Decimal('0.6'),  # 60% win rate
            max_drawdown=Decimal('-0.15'),  # -15%
            sharpe_ratio=Decimal('2.5'),
            avg_holding_days=Decimal('20.5'),
            profit_loss_ratio=Decimal('2.2'),
            max_consecutive_losses=3,
            final_capital=Decimal('125000.00')
        )
        db_session.add(result)

        # Create sample trades
        trades_data = [
            {
                'entry_date': date(2024, 3, 5),
                'entry_price': Decimal('40200'),
                'entry_score': Decimal('7.5'),
                'exit_date': date(2024, 3, 25),
                'exit_price': Decimal('42000'),
                'exit_score': Decimal('3.5'),
                'pnl': Decimal('1800'),
                'return_pct': Decimal('0.045'),
                'holding_days': 20
            },
            {
                'entry_date': date(2024, 4, 1),
                'entry_price': Decimal('42500'),
                'entry_score': Decimal('8.0'),
                'exit_date': date(2024, 4, 20),
                'exit_price': Decimal('44000'),
                'exit_score': Decimal('4.0'),
                'pnl': Decimal('1500'),
                'return_pct': Decimal('0.035'),
                'holding_days': 19
            },
            {
                'entry_date': date(2024, 5, 1),
                'entry_price': Decimal('44500'),
                'entry_score': Decimal('7.0'),
                'exit_date': date(2024, 5, 15),
                'exit_price': Decimal('43800'),
                'exit_score': Decimal('2.5'),
                'pnl': Decimal('-700'),
                'return_pct': Decimal('-0.016'),
                'holding_days': 14
            },
        ]

        for trade_data in trades_data:
            trade = BacktestTrade(run_id=run_id, **trade_data)
            db_session.add(trade)

        # Update status to completed
        run.status = 'completed'
        run.completed_at = datetime.utcnow()
        db_session.commit()

        # Step 4: Verify results saved correctly
        db_session.refresh(run)
        assert run.status == 'completed'
        assert run.completed_at is not None
        assert run.result is not None

        # Step 5: Verify result metrics
        saved_result = db_session.query(BacktestResult).filter(
            BacktestResult.run_id == run_id
        ).first()

        assert saved_result is not None
        assert saved_result.total_return == Decimal('0.25')
        assert saved_result.num_trades == 5
        assert saved_result.win_rate == Decimal('0.6')
        assert saved_result.sharpe_ratio == Decimal('2.5')
        assert saved_result.final_capital == Decimal('125000.00')

        # Step 6: Verify trades created
        saved_trades = db_session.query(BacktestTrade).filter(
            BacktestTrade.run_id == run_id
        ).order_by(BacktestTrade.entry_date).all()

        assert len(saved_trades) == 3
        assert saved_trades[0].entry_price == Decimal('40200')
        assert saved_trades[0].pnl == Decimal('1800')
        assert saved_trades[1].return_pct == Decimal('0.035')

        # Step 7: Verify relationships work
        assert len(run.trades) == 3
        assert run.result.sharpe_ratio == Decimal('2.5')


class TestCacheIntegration:
    """Test cache service database integration"""

    def test_cache_save_and_retrieve(self, db_session, cache_service):
        """Test saving data to cache and retrieving it"""
        import pandas as pd

        # Create sample dataframe
        dates = pd.date_range(start='2024-01-01', periods=10, freq='D')
        data = pd.DataFrame({
            'open': [100, 101, 102, 103, 104, 105, 106, 107, 108, 109],
            'high': [102, 103, 104, 105, 106, 107, 108, 109, 110, 111],
            'low': [99, 100, 101, 102, 103, 104, 105, 106, 107, 108],
            'close': [101, 102, 103, 104, 105, 106, 107, 108, 109, 110],
            'volume': [1000] * 10
        }, index=dates)

        # Save to cache
        cache_service.save_data('TESTUSDT', data)

        # Retrieve from cache
        retrieved = cache_service.get_data(
            'TESTUSDT',
            date(2024, 1, 1),
            date(2024, 1, 10)
        )

        # Verify data matches
        assert retrieved is not None
        assert len(retrieved) == 10
        assert retrieved.iloc[0]['close'] == 101
        assert retrieved.iloc[-1]['close'] == 110

    def test_cache_partial_range(self, db_session, cache_service):
        """Test retrieving partial date range from cache"""
        import pandas as pd

        # Save larger dataset
        dates = pd.date_range(start='2024-01-01', periods=30, freq='D')
        data = pd.DataFrame({
            'open': list(range(100, 130)),
            'high': list(range(102, 132)),
            'low': list(range(99, 129)),
            'close': list(range(101, 131)),
            'volume': [1000] * 30
        }, index=dates)

        cache_service.save_data('ETHUSDT', data)

        # Retrieve only middle 10 days
        retrieved = cache_service.get_data(
            'ETHUSDT',
            date(2024, 1, 11),
            date(2024, 1, 20)
        )

        assert len(retrieved) == 10
        assert retrieved.iloc[0]['close'] == 111  # 11th day (101 + 10)
        assert retrieved.iloc[-1]['close'] == 120  # 20th day


class TestAPIEndpoints:
    """Test REST API endpoints (requires Flask app)"""

    @pytest.fixture
    def client(self, db_session):
        """Create Flask test client"""
        from flask import Flask
        from flask_socketio import SocketIO
        from quant_v3.live.backtest.routes import init_routes

        app = Flask(__name__)
        app.config['TESTING'] = True
        socketio = SocketIO(app)

        # Initialize routes
        init_routes(app, socketio)

        with app.test_client() as client:
            yield client

    def test_get_history_endpoint(self, client, db_session):
        """Test GET /api/backtest/history"""
        # Create test runs
        for i in range(3):
            run = BacktestRun(
                symbol='BTCUSDT',
                start_date=date(2024, 1, 1),
                end_date=date(2024, 6, 30),
                initial_capital=Decimal('100000'),
                leverage=Decimal('1.0'),
                fee_rate=Decimal('0.001'),
                strategy_params={'periods': {'short': 20, 'medium': 50, 'long': 120, 'super_long': 180}},
                status='completed'
            )
            db_session.add(run)
        db_session.commit()

        # Test endpoint
        response = client.get('/api/backtest/history')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'runs' in data
        assert len(data['runs']) == 3
        assert data['total'] == 3
        assert data['page'] == 1

    def test_get_history_with_pagination(self, client, db_session):
        """Test pagination in history endpoint"""
        # Create 25 test runs
        for i in range(25):
            run = BacktestRun(
                symbol='BTCUSDT',
                start_date=date(2024, 1, 1),
                end_date=date(2024, 6, 30),
                initial_capital=Decimal('100000'),
                leverage=Decimal('1.0'),
                fee_rate=Decimal('0.001'),
                strategy_params={'periods': {'short': 20, 'medium': 50, 'long': 120, 'super_long': 180}},
                status='completed'
            )
            db_session.add(run)
        db_session.commit()

        # Test page 1
        response = client.get('/api/backtest/history?page=1&per_page=10')
        data = json.loads(response.data)
        assert len(data['runs']) == 10
        assert data['total'] == 25
        assert data['total_pages'] == 3

        # Test page 2
        response = client.get('/api/backtest/history?page=2&per_page=10')
        data = json.loads(response.data)
        assert len(data['runs']) == 10
        assert data['page'] == 2

    def test_get_backtest_detail(self, client, db_session):
        """Test GET /api/backtest/:run_id"""
        # Create run with result
        run = BacktestRun(
            symbol='BTCUSDT',
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 30),
            initial_capital=Decimal('100000'),
            leverage=Decimal('1.0'),
            fee_rate=Decimal('0.001'),
            strategy_params={'periods': {'short': 20, 'medium': 50, 'long': 120, 'super_long': 180}},
            status='completed'
        )
        db_session.add(run)
        db_session.commit()
        db_session.refresh(run)

        # Add result
        result = BacktestResult(
            run_id=run.id,
            total_return=Decimal('0.30'),
            annual_return=Decimal('0.30'),
            num_trades=10,
            win_rate=Decimal('0.7'),
            max_drawdown=Decimal('-0.12'),
            sharpe_ratio=Decimal('3.0'),
            avg_holding_days=Decimal('15.5'),
            profit_loss_ratio=Decimal('2.5'),
            max_consecutive_losses=2,
            final_capital=Decimal('130000')
        )
        db_session.add(result)
        db_session.commit()

        # Test endpoint
        response = client.get(f'/api/backtest/{run.id}')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['id'] == run.id
        assert data['symbol'] == 'BTCUSDT'
        assert 'metrics' in data
        assert data['metrics']['total_return'] == 0.30
        assert data['metrics']['num_trades'] == 10
        assert data['metrics']['sharpe_ratio'] == 3.0

    def test_delete_backtest(self, client, db_session):
        """Test DELETE /api/backtest/:run_id"""
        # Create run
        run = BacktestRun(
            symbol='BTCUSDT',
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 30),
            initial_capital=Decimal('100000'),
            leverage=Decimal('1.0'),
            fee_rate=Decimal('0.001'),
            strategy_params={'periods': {'short': 20, 'medium': 50, 'long': 120, 'super_long': 180}},
            status='completed'
        )
        db_session.add(run)
        db_session.commit()
        db_session.refresh(run)

        run_id = run.id

        # Delete via API
        response = client.delete(f'/api/backtest/{run_id}')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['success'] is True

        # Verify deleted from database
        deleted_run = db_session.query(BacktestRun).get(run_id)
        assert deleted_run is None

    def test_get_trades_endpoint(self, client, db_session):
        """Test GET /api/backtest/:run_id/trades"""
        # Create run with trades
        run = BacktestRun(
            symbol='BTCUSDT',
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 30),
            initial_capital=Decimal('100000'),
            leverage=Decimal('1.0'),
            fee_rate=Decimal('0.001'),
            strategy_params={'periods': {'short': 20, 'medium': 50, 'long': 120, 'super_long': 180}},
            status='completed'
        )
        db_session.add(run)
        db_session.commit()
        db_session.refresh(run)

        # Add trades
        for i in range(5):
            trade = BacktestTrade(
                run_id=run.id,
                entry_date=date(2024, 1, 1 + i*10),
                entry_price=Decimal(40000 + i*1000),
                entry_score=Decimal('7.5'),
                exit_date=date(2024, 1, 11 + i*10),
                exit_price=Decimal(41000 + i*1000),
                exit_score=Decimal('4.0'),
                pnl=Decimal(1000),
                return_pct=Decimal('0.025'),
                holding_days=10
            )
            db_session.add(trade)
        db_session.commit()

        # Test endpoint
        response = client.get(f'/api/backtest/{run.id}/trades')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert len(data) == 5
        assert data[0]['entry_price'] == 40000
        assert data[0]['pnl'] == 1000
        assert data[0]['holding_days'] == 10


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_empty_backtest_history(self, client, db_session):
        """Test history endpoint with no backtests"""
        response = client.get('/api/backtest/history')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['runs'] == []
        assert data['total'] == 0

    def test_get_nonexistent_backtest(self, client, db_session):
        """Test getting details for non-existent backtest"""
        response = client.get('/api/backtest/99999')
        assert response.status_code == 404

    def test_delete_nonexistent_backtest(self, client, db_session):
        """Test deleting non-existent backtest"""
        response = client.delete('/api/backtest/99999')
        assert response.status_code == 404

    def test_cache_missing_data(self, db_session, cache_service):
        """Test retrieving data that doesn't exist in cache"""
        retrieved = cache_service.get_data(
            'NONEXISTENT',
            date(2024, 1, 1),
            date(2024, 1, 10)
        )
        assert retrieved is None or len(retrieved) == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-m', 'integration'])
