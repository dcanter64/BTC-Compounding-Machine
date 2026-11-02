"""Tests for the Phase 1 BTC log-trend chart."""

from __future__ import annotations

import pandas as pd

from src.charts import (
    create_backtest_performance_figure,
    create_btc_log_trend_figure,
    plot_backtest_performance,
    plot_btc_log_trend,
)
from src.trend_model import fit_log_trend
from tests.test_trend_model import prices_with_log_residuals


def test_log_trend_chart_renders_to_file(tmp_path) -> None:
    modeled_data = fit_log_trend(prices_with_log_residuals()).data
    chart_path = plot_btc_log_trend(modeled_data, tmp_path / "trend.png")

    assert chart_path.exists()
    assert chart_path.stat().st_size > 0


def test_log_trend_chart_renders_buy_and_sell_markers(tmp_path) -> None:
    modeled_data = fit_log_trend(prices_with_log_residuals()).data
    signal_events = modeled_data.iloc[[1, 6]][["date", "close"]].copy()
    signal_events["signal"] = ["BUY", "SELL"]

    chart_path = plot_btc_log_trend(modeled_data, tmp_path / "events.png", signal_events)

    assert chart_path.exists()
    assert chart_path.stat().st_size > 0


def test_backtest_performance_chart_renders_to_file(tmp_path) -> None:
    daily_values = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=3, freq="D"),
            "total_portfolio_value": [1_000.0, 1_100.0, 1_050.0],
            "buy_and_hold_value": [1_000.0, 1_200.0, 1_150.0],
        }
    )

    chart_path = plot_backtest_performance(daily_values, tmp_path / "backtest.png")

    assert chart_path.exists()
    assert chart_path.stat().st_size > 0


def test_dashboard_figures_are_created_in_memory() -> None:
    modeled_data = fit_log_trend(prices_with_log_residuals()).data
    trend_figure = create_btc_log_trend_figure(
        modeled_data,
        residual_sigma=fit_log_trend(prices_with_log_residuals()).residual_standard_deviation,
        buy_threshold=-1.5,
        sell_threshold=2.0,
    )
    performance_figure = create_backtest_performance_figure(
        pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=2, freq="D"),
                "total_portfolio_value": [1_000.0, 1_100.0],
                "buy_and_hold_value": [1_000.0, 1_200.0],
            }
        )
    )

    assert trend_figure.axes[0].get_yscale() == "log"
    assert performance_figure.axes[0].get_title() == "BTC Compounding Machine vs Buy and Hold"
