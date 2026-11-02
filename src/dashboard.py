"""Pure dashboard calculations shared by the Streamlit interface and tests."""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np
import pandas as pd

from src.signals import build_signal_history, find_signal_events, validate_thresholds
from src.trend_model import LogTrendResult, fit_log_trend


@dataclass(frozen=True)
class CurrentDashboardState:
    """Current descriptive valuation and selected threshold levels."""

    trend: LogTrendResult
    signal_history: pd.DataFrame
    signal_events: pd.DataFrame
    current_price: float
    current_trend_price: float
    current_z_score: float
    current_signal: str
    buy_threshold_price: float
    sell_threshold_price: float
    distance_to_buy: float
    distance_to_sell: float


def build_current_dashboard_state(
    price_data: pd.DataFrame, buy_threshold: float, sell_threshold: float
) -> CurrentDashboardState:
    """Calculate the current display state using the transparent full-history model."""
    buy, sell = validate_thresholds(buy_threshold, sell_threshold)
    trend = fit_log_trend(price_data)
    signal_history = build_signal_history(trend.data, buy, sell)
    signal_events = find_signal_events(signal_history, buy, sell)
    latest = signal_history.iloc[-1]
    predicted_log_price = float(latest["predicted_log_price"])
    sigma = trend.residual_standard_deviation
    if not math.isfinite(sigma) or sigma <= 0:
        raise ValueError("Current residual sigma must be finite and greater than zero.")

    return CurrentDashboardState(
        trend=trend,
        signal_history=signal_history,
        signal_events=signal_events,
        current_price=float(latest["close"]),
        current_trend_price=float(latest["trend_price"]),
        current_z_score=float(latest["z_score"]),
        current_signal=str(latest["signal"]),
        buy_threshold_price=float(np.exp(predicted_log_price + buy * sigma)),
        sell_threshold_price=float(np.exp(predicted_log_price + sell * sigma)),
        distance_to_buy=float(latest["z_score"] - buy),
        distance_to_sell=float(sell - latest["z_score"]),
    )
