"""Tests for the dashboard's pure current-valuation calculations."""

from __future__ import annotations

import numpy as np

from src.dashboard import build_current_dashboard_state
from tests.test_trend_model import prices_with_log_residuals


def test_current_dashboard_state_calculates_levels_distances_and_signal_history() -> None:
    state = build_current_dashboard_state(prices_with_log_residuals(), -1.5, 2.0)
    latest = state.signal_history.iloc[-1]
    expected_buy_price = np.exp(
        latest["predicted_log_price"] - 1.5 * state.trend.residual_standard_deviation
    )
    expected_sell_price = np.exp(
        latest["predicted_log_price"] + 2.0 * state.trend.residual_standard_deviation
    )

    assert state.current_price == latest["close"]
    assert state.current_signal == latest["signal"]
    assert state.buy_threshold_price == expected_buy_price
    assert state.sell_threshold_price == expected_sell_price
    assert state.distance_to_buy == latest["z_score"] + 1.5
    assert state.distance_to_sell == 2.0 - latest["z_score"]
    assert state.buy_threshold_price < state.current_trend_price < state.sell_threshold_price
