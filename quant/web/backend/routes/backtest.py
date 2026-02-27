import logging

from fastapi import APIRouter, HTTPException

from quant.web.backend.schemas import BacktestRequest, BacktestResponse
from quant.web.backend.services.backtest_service import run_backtest
from quant.web.backend.services.backtest_storage import BacktestStorage

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")
storage = BacktestStorage()


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


@router.post("/api/backtest/save")
async def save_backtest(data: dict):
    """Save backtest result for later analysis.

    Request body:
    {
        "result": {...},  # Full BacktestResponse
        "metadata": {
            "strategy": "EMA_Triple(9/21/200)",
            "symbol": "BTC-USDT",
            "timeframe": "1H",
            "start_time": "2025-01-01",
            "end_time": "2026-01-01"
        }
    }
    """
    try:
        result = data.get("result")
        metadata = data.get("metadata", {})
        file_id = storage.save(result, metadata)
        return {"id": file_id, "message": "Backtest saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/backtest/history")
async def list_backtests():
    """List all saved backtests."""
    try:
        return storage.list_all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/backtest/{file_id}")
async def load_backtest(file_id: str):
    """Load historical backtest result."""
    try:
        return storage.load(file_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Backtest {file_id} not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/backtest/{file_id}")
async def delete_backtest(file_id: str):
    """Delete a saved backtest."""
    try:
        storage.delete(file_id)
        return {"message": f"Backtest {file_id} deleted successfully"}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Backtest {file_id} not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
