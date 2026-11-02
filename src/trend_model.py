"""Transparent long-term logarithmic BTC price-trend calculations."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

BAND_MULTIPLIERS = (-2.0, -1.5, -1.0, 1.0, 2.0)


class TrendCalculationError(ValueError):
    """Raised when a log-trend model cannot be calculated safely."""


@dataclass(frozen=True)
class LogTrendResult:
    """Fitted coefficients and the daily history augmented with model values."""

    data: pd.DataFrame
    intercept: float
    slope: float
    residual_standard_deviation: float
    start_date: pd.Timestamp


def _band_column_name(multiplier: float) -> str:
    sign = "pos" if multiplier > 0 else "neg"
    magnitude = str(abs(multiplier)).replace(".", "_")
    return f"band_{sign}_{magnitude}_sigma"


def fit_log_trend(price_data: pd.DataFrame) -> LogTrendResult:
    """Fit ``ln(close) = intercept + slope * days_since_start``.

    The model uses every supplied observation. Its residual standard deviation is
    the population standard deviation (``ddof=0``) of in-sample residuals. This
    produces a descriptive valuation measure, not point-in-time backtest signals.
    """
    required_columns = {"date", "close"}
    missing = required_columns.difference(price_data.columns)
    if missing:
        raise TrendCalculationError(
            f"Trend input is missing columns: {', '.join(sorted(missing))}."
        )

    data = price_data.copy()
    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    data["close"] = pd.to_numeric(data["close"], errors="coerce")
    if data[["date", "close"]].isna().any().any():
        raise TrendCalculationError("Trend input contains invalid dates or close prices.")
    if (data["close"] <= 0).any():
        raise TrendCalculationError("Log trend requires strictly positive close prices.")

    data = data.sort_values("date").reset_index(drop=True)
    if data["date"].duplicated().any():
        raise TrendCalculationError("Trend input contains duplicate dates.")
    if len(data) < 3:
        raise TrendCalculationError("At least three daily prices are required for a log trend.")

    start_date = data["date"].iloc[0]
    days_since_start = (data["date"] - start_date).dt.total_seconds() / 86_400
    actual_log_price = np.log(data["close"].to_numpy(dtype=float))
    slope, intercept = np.polyfit(days_since_start.to_numpy(dtype=float), actual_log_price, deg=1)
    predicted_log_price = intercept + slope * days_since_start.to_numpy(dtype=float)
    residual = actual_log_price - predicted_log_price
    residual_standard_deviation = float(np.std(residual, ddof=0))
    if (
        not np.isfinite(residual_standard_deviation)
        or residual_standard_deviation <= np.finfo(float).eps
    ):
        raise TrendCalculationError(
            "Residual standard deviation must be finite and greater than zero."
        )

    data["days_since_start"] = days_since_start.to_numpy(dtype=float)
    data["actual_log_price"] = actual_log_price
    data["predicted_log_price"] = predicted_log_price
    data["trend_price"] = np.exp(predicted_log_price)
    data["residual"] = residual
    data["z_score"] = residual / residual_standard_deviation
    for multiplier in BAND_MULTIPLIERS:
        data[_band_column_name(multiplier)] = np.exp(
            predicted_log_price + multiplier * residual_standard_deviation
        )

    return LogTrendResult(
        data=data,
        intercept=float(intercept),
        slope=float(slope),
        residual_standard_deviation=residual_standard_deviation,
        start_date=start_date,
    )
