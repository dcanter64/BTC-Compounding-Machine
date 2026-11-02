"""Tests for the expanding-window historical backtest."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.backtest import (
    BacktestConfig,
    add_buy_and_hold_benchmark,
    build_daily_portfolio_values,
    calculate_expanding_log_trend,
    calculate_performance_metrics,
    run_backtest,
    schedule_next_open_executions,
)


def synthetic_prices() -> pd.DataFrame:
    days = np.arange(12, dtype=float)
    residuals = np.array([0.00, 0.10, -0.04, 0.07, -0.06, 0.03, 0.11, -0.03, 0.05, -0.08, 0.02, 0.09])
    close_prices = np.exp(10.0 + 0.01 * days + residuals)
    return pd.DataFrame(
        {
            "date": pd.date_range("2020-01-01", periods=len(days), freq="D"),
            "open": close_prices,
            "close": close_prices,
        }
    )


def test_expanding_model_does_not_use_current_or_future_close_to_fit_its_trend() -> None:
    prices = synthetic_prices()
    start_date = prices.loc[3, "date"]
    baseline = calculate_expanding_log_trend(
        prices, starting_date=start_date, min_training_observations=3
    )
    current_changed = prices.copy()
    current_changed.loc[3, "close"] *= 10
    current_comparison = calculate_expanding_log_trend(
        current_changed, starting_date=start_date, min_training_observations=3
    )
    future_changed = prices.copy()
    future_changed.loc[11, "close"] *= 20
    future_comparison = calculate_expanding_log_trend(
        future_changed, starting_date=start_date, min_training_observations=3
    )

    first_date = start_date
    baseline_first = baseline.loc[baseline["date"] == first_date].iloc[0]
    current_comparison_first = current_comparison.loc[
        current_comparison["date"] == first_date
    ].iloc[0]
    assert baseline_first["predicted_log_price"] == pytest.approx(
        current_comparison_first["predicted_log_price"]
    )
    assert baseline_first["residual_standard_deviation"] == pytest.approx(
        current_comparison_first["residual_standard_deviation"]
    )
    assert baseline_first["z_score"] != pytest.approx(current_comparison_first["z_score"])

    dates_before_future_change = baseline["date"] < prices.loc[11, "date"]
    assert np.allclose(
        baseline.loc[dates_before_future_change, "predicted_log_price"],
        future_comparison.loc[dates_before_future_change, "predicted_log_price"],
    )


def test_daily_portfolio_values_and_benchmark_use_the_same_initial_capital() -> None:
    modeled_data = pd.DataFrame(
        {
            "date": pd.date_range("2020-01-01", periods=3, freq="D"),
            "close": [100.0, 200.0, 150.0],
            "model_available": [True, True, True],
        }
    )
    ledger = pd.DataFrame(
        {
            "date": [pd.Timestamp("2020-01-02")],
            "cash_after": [500.0],
            "btc_holdings_after": [2.5],
        }
    )

    daily_values = build_daily_portfolio_values(
        modeled_data, ledger, starting_cash=1_000.0, starting_btc=0.0
    )
    benchmarked = add_buy_and_hold_benchmark(
        daily_values, starting_cash=1_000.0, starting_btc=0.0
    )

    assert daily_values["total_portfolio_value"].tolist() == pytest.approx([1_000.0, 1_000.0, 875.0])
    assert benchmarked["buy_and_hold_value"].tolist() == pytest.approx([1_000.0, 2_000.0, 1_500.0])


def test_performance_metrics_calculate_return_and_maximum_drawdown() -> None:
    metrics = calculate_performance_metrics(pd.Series([1_000.0, 1_200.0, 900.0, 1_080.0]))

    assert metrics["total_return"] == pytest.approx(0.08)
    assert metrics["maximum_drawdown"] == pytest.approx(-0.25)


def test_close_signal_executes_at_the_next_available_open() -> None:
    modeled_data = pd.DataFrame(
        {
            "date": pd.date_range("2020-01-01", periods=3, freq="D"),
            "open": [100.0, 110.0, 120.0],
            "model_available": [True, True, True],
        }
    )
    signal_events = pd.DataFrame(
        {
            "date": [pd.Timestamp("2020-01-01")],
            "close": [105.0],
            "trend_price": [100.0],
            "z_score": [-1.6],
            "signal": ["BUY"],
        }
    )

    execution_events, unexecuted_events = schedule_next_open_executions(
        signal_events, modeled_data
    )

    assert unexecuted_events.empty
    assert execution_events.loc[0, "signal_date"] == pd.Timestamp("2020-01-01")
    assert execution_events.loc[0, "date"] == pd.Timestamp("2020-01-02")
    assert execution_events.loc[0, "close"] == pytest.approx(110.0)
    assert execution_events.loc[0, "execution_price_source"] == "next_day_open"


def test_backtest_uses_expanding_signals_and_returns_daily_values() -> None:
    prices = synthetic_prices()
    config = BacktestConfig(
        starting_date="2020-01-04",
        starting_cash=1_000.0,
        starting_btc=0.0,
        buy_threshold=-0.5,
        sell_threshold=0.5,
        buy_amount=1_000.0,
        sell_amount=500.0,
        min_training_observations=3,
    )

    result = run_backtest(prices, config)

    assert not result.daily_values.empty
    assert result.daily_values["date"].min() == pd.Timestamp("2020-01-04")
    assert "buy_and_hold_value" in result.daily_values
    assert result.summary["starting_date"] == "2020-01-04"
