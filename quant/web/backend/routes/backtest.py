import logging

from fastapi import APIRouter, HTTPException

from quant.web.backend.schemas import BacktestRequest, BacktestResponse
from quant.web.backend.services.backtest_service import run_backtest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


@router.post("/backtest", response_model=BacktestResponse)
async def backtest(request: BacktestRequest):
    logger.info(f"POST /api/backtest symbol={request.symbol} timeframe={request.timeframe}")
    try:
        result = run_backtest(request)
        logger.info(f"Backtest done: {len(result.strategies)} strategies, {len(result.timestamps)} timestamps")
        return result
    except Exception as e:
        logger.error(f"Backtest failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
