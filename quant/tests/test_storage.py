import os
import pandas as pd
import pytest
from quant.data.storage import CsvStorage


@pytest.fixture
def tmp_data_dir(tmp_path):
    return str(tmp_path / "data")


@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "timestamp": [1000, 2000, 3000],
        "open": [100.0, 101.0, 102.0],
        "high": [105.0, 106.0, 107.0],
        "low": [95.0, 96.0, 97.0],
        "close": [103.0, 104.0, 105.0],
        "volume": [1000.0, 1100.0, 1200.0],
    })


def test_save_and_load(tmp_data_dir, sample_df):
    storage = CsvStorage(tmp_data_dir)
    storage.save(sample_df, "BTC-USDT", "1H")
    loaded = storage.load("BTC-USDT", "1H")
    assert len(loaded) == 3
    assert loaded["close"].iloc[2] == 105.0


def test_load_nonexistent_returns_empty(tmp_data_dir):
    storage = CsvStorage(tmp_data_dir)
    loaded = storage.load("FAKE-USDT", "1H")
    assert loaded.empty


def test_file_path_format(tmp_data_dir, sample_df):
    storage = CsvStorage(tmp_data_dir)
    storage.save(sample_df, "BTC-USDT", "1H")
    expected_path = os.path.join(tmp_data_dir, "BTC-USDT_1H.csv")
    assert os.path.exists(expected_path)
