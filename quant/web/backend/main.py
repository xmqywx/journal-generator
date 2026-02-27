import sys
import logging
from pathlib import Path

# Add project root to sys.path so quant.* imports work
_project_root = str(Path(__file__).resolve().parents[3])
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from quant.web.backend.routes import backtest, candles

app = FastAPI(title="Quant Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(backtest.router)
app.include_router(candles.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
