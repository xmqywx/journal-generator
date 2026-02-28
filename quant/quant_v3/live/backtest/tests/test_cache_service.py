"""Tests for cache service."""
import pytest
import pandas as pd
from datetime import datetime, date
from sqlalchemy.orm import Session

from quant_v3.live.backtest.cache_service import CacheService
from quant_v3.live.backtest.database import SessionLocal, PriceDataCache


@pytest.fixture
def db_session():
    """Create a database session for testing."""
    db = SessionLocal()
    try:
        yield db
    finally:
        # Clean up test data
        db.query(PriceDataCache).delete()
        db.commit()
        db.close()


@pytest.fixture
def cache_service(db_session):
    """Create a cache service instance."""
    return CacheService(db_session)


def test_cache_empty_initially(cache_service):
    """Test that cache returns empty DataFrame when no data exists."""
    start_date = date(2024, 1, 1)
    end_date = date(2024, 1, 10)

    df = cache_service.get_cached_data("BTC/USDT", start_date, end_date)

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 0


def test_save_and_retrieve_cache(cache_service):
    """Test saving data to cache and retrieving it."""
    # Create sample data
    data = {
        'date': [date(2024, 1, 1), date(2024, 1, 2)],
        'open': [100.0, 101.0],
        'high': [102.0, 103.0],
        'low': [99.0, 100.0],
        'close': [101.0, 102.0],
        'volume': [1000.0, 1100.0]
    }
    df = pd.DataFrame(data)

    # Save to cache
    cache_service.save_to_cache("BTC/USDT", df)

    # Retrieve from cache
    start_date = date(2024, 1, 1)
    end_date = date(2024, 1, 2)
    result_df = cache_service.get_cached_data("BTC/USDT", start_date, end_date)

    assert len(result_df) == 2
    assert result_df['close'].tolist() == [101.0, 102.0]


def test_get_missing_dates(cache_service):
    """Test identifying missing dates in cache."""
    # Save data for Jan 1 and Jan 3 (skip Jan 2)
    data = {
        'date': [date(2024, 1, 1), date(2024, 1, 3)],
        'open': [100.0, 102.0],
        'high': [102.0, 104.0],
        'low': [99.0, 101.0],
        'close': [101.0, 103.0],
        'volume': [1000.0, 1200.0]
    }
    df = pd.DataFrame(data)
    cache_service.save_to_cache("BTC/USDT", df)

    # Check for missing dates
    start_date = date(2024, 1, 1)
    end_date = date(2024, 1, 3)
    missing = cache_service.get_missing_dates("BTC/USDT", start_date, end_date)

    assert date(2024, 1, 2) in missing
    assert date(2024, 1, 1) not in missing
    assert date(2024, 1, 3) not in missing
