"""Tests for transparent log-trend calculations and price-space bands."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.trend_model import TrendCalculationError, fit_log_trend


def prices_with_log_residuals() -> pd.DataFrame:
    days = np.arange(8, dtype=float)
    base_log_price = 10.0 + 0.01 * days
    residuals = np.array([-0.08, 0.03, -0.02, 0.07, -0.04, 0.06, -0.03, 0.01])
    return pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=len(days), freq="D"),
            "close": np.exp(base_log_price + residuals),
        }
    )


def test_log_price_residual_z_score_and_trend_are_calculated_consistently() -> None:
    result = fit_log_trend(prices_with_log_residuals())
    data = result.data

    assert (data["trend_price"] > 0).all()
    assert np.allclose(data["actual_log_price"], np.log(data["close"]))
    assert np.allclose(data["residual"], data["actual_log_price"] - data["predicted_log_price"])
    assert np.allclose(data["z_score"], data["residual"] / result.residual_standard_deviation)
    assert (data.loc[data["residual"] > 0, "z_score"] > 0).all()
    assert (data.loc[data["residual"] < 0, "z_score"] < 0).all()


def test_sigma_bands_are_exponentiated_from_log_space() -> None:
    result = fit_log_trend(prices_with_log_residuals())
    data = result.data
    sigma = result.residual_standard_deviation

    assert np.allclose(data["band_pos_2_0_sigma"], np.exp(data["predicted_log_price"] + 2 * sigma))
    assert np.allclose(data["band_neg_1_5_sigma"], np.exp(data["predicted_log_price"] - 1.5 * sigma))
    assert (data["band_pos_2_0_sigma"] > data["trend_price"]).all()
    assert (data["band_neg_2_0_sigma"] < data["trend_price"]).all()


def test_flat_residuals_fail_clearly() -> None:
    data = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=4, freq="D"),
            "close": np.exp(10 + 0.01 * np.arange(4)),
        }
    )

    with pytest.raises(TrendCalculationError, match="standard deviation"):
        fit_log_trend(data)
