"""
Cache service for historical price data.

Provides methods to:
- Cache historical price data in PostgreSQL
- Retrieve cached data
- Identify gaps in cached data
- Clean up old data
"""
from datetime import date, datetime, timedelta
from typing import List
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from .database import PriceDataCache


class CacheService:
    """Service for managing price data cache."""

    def __init__(self, db: Session):
        """
        Initialize cache service.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def get_cached_data(
        self,
        symbol: str,
        start_date: date,
        end_date: date
    ) -> pd.DataFrame:
        """
        Retrieve cached price data for a symbol and date range.

        Args:
            symbol: Trading symbol (e.g., "BTC/USDT")
            start_date: Start date for data retrieval
            end_date: End date for data retrieval

        Returns:
            DataFrame with columns: date, open, high, low, close, volume
            Returns empty DataFrame if no data found
        """
        query = self.db.query(PriceDataCache).filter(
            PriceDataCache.symbol == symbol,
            PriceDataCache.date >= start_date,
            PriceDataCache.date <= end_date
        ).order_by(PriceDataCache.date)

        results = query.all()

        if not results:
            return pd.DataFrame(columns=['date', 'open', 'high', 'low', 'close', 'volume'])

        # Convert to DataFrame
        data = {
            'date': [r.date for r in results],
            'open': [float(r.open) for r in results],
            'high': [float(r.high) for r in results],
            'low': [float(r.low) for r in results],
            'close': [float(r.close) for r in results],
            'volume': [float(r.volume) for r in results]
        }

        return pd.DataFrame(data)

    def save_to_cache(self, symbol: str, df: pd.DataFrame) -> None:
        """
        Save price data to cache.

        Uses bulk insert for performance with conflict handling.

        Args:
            symbol: Trading symbol (e.g., "BTC/USDT")
            df: DataFrame with columns: date, open, high, low, close, volume
        """
        if df.empty:
            return

        # Prepare records for bulk insert
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

        try:
            # Try bulk insert first
            self.db.bulk_insert_mappings(PriceDataCache, records)
            self.db.commit()
        except IntegrityError:
            # If bulk insert fails due to conflicts, rollback and insert individually
            self.db.rollback()

            for record in records:
                try:
                    # Check if record already exists
                    existing = self.db.query(PriceDataCache).filter(
                        PriceDataCache.symbol == record['symbol'],
                        PriceDataCache.date == record['date']
                    ).first()

                    if not existing:
                        # Only insert if doesn't exist
                        cache_entry = PriceDataCache(**record)
                        self.db.add(cache_entry)
                        self.db.commit()
                except Exception:
                    # Skip individual conflicts
                    self.db.rollback()
                    continue

    def get_missing_dates(
        self,
        symbol: str,
        start_date: date,
        end_date: date
    ) -> List[date]:
        """
        Identify dates with missing data in the cache.

        Args:
            symbol: Trading symbol (e.g., "BTC/USDT")
            start_date: Start date for range check
            end_date: End date for range check

        Returns:
            List of dates that are missing from the cache
        """
        # Query all cached dates in the range
        query = self.db.query(PriceDataCache.date).filter(
            PriceDataCache.symbol == symbol,
            PriceDataCache.date >= start_date,
            PriceDataCache.date <= end_date
        )

        cached_dates = {row.date for row in query.all()}

        # Generate all dates in the range
        all_dates = []
        current_date = start_date
        while current_date <= end_date:
            all_dates.append(current_date)
            current_date += timedelta(days=1)

        # Find missing dates
        missing_dates = [d for d in all_dates if d not in cached_dates]

        return missing_dates

    def clear_old_cache(self, days: int = 90) -> None:
        """
        Delete cached data older than specified number of days.

        Args:
            days: Number of days to keep (default: 90)
        """
        cutoff_date = date.today() - timedelta(days=days)

        self.db.query(PriceDataCache).filter(
            PriceDataCache.date < cutoff_date
        ).delete()

        self.db.commit()
