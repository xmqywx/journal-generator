import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class BacktestStorage:
    """Persistent storage for backtest results.

    Saves backtest data to JSON files for later analysis.
    """

    def __init__(self, storage_dir: str = "data/backtests"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"BacktestStorage initialized at {self.storage_dir}")

    def save(self, result: dict, metadata: dict) -> str:
        """Save backtest result to JSON file.

        Args:
            result: Backtest result dictionary
            metadata: Metadata about the backtest (strategy, symbol, dates, etc.)

        Returns:
            file_id: Unique identifier for saved backtest
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        strategy_name = metadata.get('strategy', 'unknown').replace(' ', '_')
        symbol = metadata.get('symbol', 'unknown').replace('-', '')

        file_id = f"{timestamp}_{strategy_name}_{symbol}"

        data = {
            "metadata": metadata,
            "result": result
        }

        filepath = self.storage_dir / f"{file_id}.json"

        try:
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved backtest: {file_id}")
            return file_id
        except Exception as e:
            logger.error(f"Failed to save backtest {file_id}: {e}")
            raise

    def load(self, file_id: str) -> dict:
        """Load historical backtest result.

        Args:
            file_id: Backtest identifier

        Returns:
            dict with 'metadata' and 'result' keys
        """
        filepath = self.storage_dir / f"{file_id}.json"

        if not filepath.exists():
            raise FileNotFoundError(f"Backtest {file_id} not found")

        try:
            with open(filepath, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load backtest {file_id}: {e}")
            raise

    def list_all(self) -> list[dict]:
        """List all saved backtests.

        Returns:
            List of dicts with 'id' and 'metadata' keys, sorted newest first
        """
        results = []

        try:
            for filepath in self.storage_dir.glob("*.json"):
                try:
                    with open(filepath, "r") as f:
                        data = json.load(f)
                        results.append({
                            "id": filepath.stem,
                            "metadata": data.get("metadata", {})
                        })
                except Exception as e:
                    logger.warning(f"Failed to read {filepath}: {e}")
                    continue

            # Sort by ID (timestamp) descending
            results.sort(key=lambda x: x["id"], reverse=True)
            logger.info(f"Listed {len(results)} backtests")
            return results
        except Exception as e:
            logger.error(f"Failed to list backtests: {e}")
            raise

    def delete(self, file_id: str) -> None:
        """Delete a saved backtest.

        Args:
            file_id: Backtest identifier
        """
        filepath = self.storage_dir / f"{file_id}.json"

        if not filepath.exists():
            raise FileNotFoundError(f"Backtest {file_id} not found")

        try:
            filepath.unlink()
            logger.info(f"Deleted backtest: {file_id}")
        except Exception as e:
            logger.error(f"Failed to delete backtest {file_id}: {e}")
            raise
