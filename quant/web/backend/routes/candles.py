import logging

from fastapi import APIRouter, HTTPException

from quant.web.backend.schemas import CandleData
from quant.web.backend.services.backtest_service import _fetch_data

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


@router.get("/candles", response_model=list[CandleData])
async def get_candles(
    symbol: str = "BTC-USDT",
    timeframe: str = "1H",
    lookback_days: int = 365,
    data_source: str = "okx",
):
    logger.info(f"GET /api/candles symbol={symbol} timeframe={timeframe}")
    try:
        df = _fetch_data(symbol, timeframe, lookback_days, data_source)
        if df.empty:
            logger.warning(f"No candle data for {symbol}/{timeframe}")
            return []
        logger.info(f"Returning {len(df)} candles for {symbol}/{timeframe}")
        return [
            CandleData(
                timestamp=int(row["timestamp"]),
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=float(row["volume"]),
            )
            for _, row in df.iterrows()
        ]
    except Exception as e:
        logger.error(f"Candles failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
