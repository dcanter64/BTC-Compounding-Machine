"""Tests for local BTC data validation and caching."""

from __future__ import annotations

import pandas as pd
import pytest

from src.data_loader import DataValidationError, load_btc_data, validate_btc_data


def valid_prices() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=5, freq="D"),
            "open": [40_000, 40_100, 40_200, 40_300, 40_400],
            "high": [40_200, 40_300, 40_400, 40_500, 40_600],
            "low": [39_800, 39_900, 40_000, 40_100, 40_200],
            "close": [40_100, 40_200, 40_300, 40_400, 40_500],
            "volume": [1_000, 1_100, 1_200, 1_300, 1_400],
        }
    )


def test_validation_sorts_dates_and_normalises_to_daily_dates() -> None:
    data = valid_prices().iloc[::-1].copy()
    data["date"] = data["date"].astype("object")
    data.loc[data.index[0], "date"] = "2024-01-05T17:00:00Z"

    validated = validate_btc_data(data)

    assert validated["date"].tolist() == list(pd.date_range("2024-01-01", periods=5, freq="D"))


@pytest.mark.parametrize(
    ("column", "value", "message"),
    [("close", 0, "zero or negative"), ("volume", -1, "negative volume")],
)
def test_validation_rejects_unsafe_numeric_values(
    column: str, value: float, message: str
) -> None:
    data = valid_prices()
    data.loc[0, column] = value

    with pytest.raises(DataValidationError, match=message):
        validate_btc_data(data)


def test_validation_rejects_duplicate_dates() -> None:
    data = valid_prices()
    data.loc[1, "date"] = data.loc[0, "date"]

    with pytest.raises(DataValidationError, match="duplicate"):
        validate_btc_data(data)


def test_loader_writes_cache_and_uses_fresh_rows(tmp_path) -> None:
    cache_path = tmp_path / "btc.csv"
    source = valid_prices()

    def downloader(start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
        assert start == pd.Timestamp("2014-09-17")
        assert end == pd.Timestamp("2024-01-06")
        return source

    loaded = load_btc_data(cache_path, downloader=downloader, today=pd.Timestamp("2024-01-05"))

    assert cache_path.exists()
    assert loaded.equals(validate_btc_data(source))
