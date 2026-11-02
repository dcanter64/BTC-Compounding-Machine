"""Phase 1 charting for the BTC log-trend model."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def plot_btc_log_trend(
    modeled_data: pd.DataFrame,
    output_path: Path,
    signal_events: pd.DataFrame | None = None,
) -> Path:
    """Save the BTC log-trend chart, optionally with BUY and SELL event markers."""
    required_columns = {
        "date",
        "close",
        "trend_price",
        "band_neg_2_0_sigma",
        "band_neg_1_0_sigma",
        "band_pos_1_0_sigma",
        "band_pos_2_0_sigma",
    }
    missing = required_columns.difference(modeled_data.columns)
    if missing:
        raise ValueError(f"Chart data is missing columns: {', '.join(sorted(missing))}.")
    if signal_events is not None:
        event_columns = {"date", "close", "signal"}
        missing_event_columns = event_columns.difference(signal_events.columns)
        if missing_event_columns:
            raise ValueError(
                "Signal events are missing columns: "
                f"{', '.join(sorted(missing_event_columns))}."
            )

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure, axis = plt.subplots(figsize=(14, 8))
    axis.plot(modeled_data["date"], modeled_data["close"], label="BTC close", color="#f7931a", linewidth=1.4)
    axis.plot(modeled_data["date"], modeled_data["trend_price"], label="Log trend", color="#1f77b4", linewidth=2)
    axis.plot(modeled_data["date"], modeled_data["band_pos_1_0_sigma"], label="+1σ", color="#6baed6", linewidth=1)
    axis.plot(modeled_data["date"], modeled_data["band_neg_1_0_sigma"], label="−1σ", color="#6baed6", linewidth=1)
    axis.plot(modeled_data["date"], modeled_data["band_pos_2_0_sigma"], label="+2σ", color="#9ecae1", linestyle="--", linewidth=1)
    axis.plot(modeled_data["date"], modeled_data["band_neg_2_0_sigma"], label="−2σ", color="#9ecae1", linestyle="--", linewidth=1)
    if signal_events is not None:
        buy_events = signal_events.loc[signal_events["signal"] == "BUY"]
        sell_events = signal_events.loc[signal_events["signal"] == "SELL"]
        if not buy_events.empty:
            axis.scatter(
                buy_events["date"], buy_events["close"], label="BUY event", color="#2ca02c",
                marker="^", s=55, zorder=4,
            )
        if not sell_events.empty:
            axis.scatter(
                sell_events["date"], sell_events["close"], label="SELL event", color="#d62728",
                marker="v", s=55, zorder=4,
            )
    axis.set_yscale("log")
    axis.set_title("BTC Price vs Log Trend")
    axis.set_xlabel("Date")
    axis.set_ylabel("BTC-USD price (log scale)")
    axis.grid(True, which="both", alpha=0.25)
    axis.legend(ncol=4)
    figure.tight_layout()
    figure.savefig(output_path, dpi=160)
    plt.close(figure)
    return output_path


def plot_backtest_performance(daily_values: pd.DataFrame, output_path: Path) -> Path:
    """Save the Phase 4 strategy-versus-buy-and-hold value chart."""
    required_columns = {"date", "total_portfolio_value", "buy_and_hold_value"}
    missing = required_columns.difference(daily_values.columns)
    if missing:
        raise ValueError(
            f"Backtest chart data is missing columns: {', '.join(sorted(missing))}."
        )

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure, axis = plt.subplots(figsize=(14, 8))
    axis.plot(
        daily_values["date"], daily_values["total_portfolio_value"],
        label="Compounding Machine", color="#1f77b4", linewidth=2,
    )
    axis.plot(
        daily_values["date"], daily_values["buy_and_hold_value"],
        label="Bitcoin buy and hold", color="#f7931a", linewidth=1.6,
    )
    axis.set_title("BTC Compounding Machine vs Buy and Hold")
    axis.set_xlabel("Date")
    axis.set_ylabel("Portfolio value (USD)")
    axis.grid(True, alpha=0.25)
    axis.legend()
    figure.tight_layout()
    figure.savefig(output_path, dpi=160)
    plt.close(figure)
    return output_path


def create_btc_log_trend_figure(
    modeled_data: pd.DataFrame,
    *,
    signal_events: pd.DataFrame | None = None,
    residual_sigma: float | None = None,
    buy_threshold: float | None = None,
    sell_threshold: float | None = None,
):
    """Create an in-memory BTC log-trend figure for the Streamlit dashboard."""
    required_columns = {
        "date",
        "close",
        "trend_price",
        "predicted_log_price",
        "band_neg_2_0_sigma",
        "band_neg_1_0_sigma",
        "band_pos_1_0_sigma",
        "band_pos_2_0_sigma",
    }
    missing = required_columns.difference(modeled_data.columns)
    if missing:
        raise ValueError(f"Chart data is missing columns: {', '.join(sorted(missing))}.")
    if signal_events is not None:
        event_columns = {"date", "close", "signal"}
        missing_event_columns = event_columns.difference(signal_events.columns)
        if missing_event_columns:
            raise ValueError(
                "Signal events are missing columns: "
                f"{', '.join(sorted(missing_event_columns))}."
            )
    if (buy_threshold is None) != (sell_threshold is None):
        raise ValueError("BUY and SELL thresholds must be supplied together.")
    if buy_threshold is not None and (residual_sigma is None or residual_sigma <= 0):
        raise ValueError("A positive residual sigma is required for selected threshold bands.")

    figure, axis = plt.subplots(figsize=(14, 8))
    axis.plot(modeled_data["date"], modeled_data["close"], label="BTC close", color="#f7931a", linewidth=1.4)
    axis.plot(modeled_data["date"], modeled_data["trend_price"], label="Log trend", color="#1f77b4", linewidth=2)
    axis.plot(modeled_data["date"], modeled_data["band_pos_1_0_sigma"], label="+1 sigma", color="#6baed6", linewidth=1)
    axis.plot(modeled_data["date"], modeled_data["band_neg_1_0_sigma"], label="-1 sigma", color="#6baed6", linewidth=1)
    axis.plot(modeled_data["date"], modeled_data["band_pos_2_0_sigma"], label="+2 sigma", color="#9ecae1", linestyle="--", linewidth=1)
    axis.plot(modeled_data["date"], modeled_data["band_neg_2_0_sigma"], label="-2 sigma", color="#9ecae1", linestyle="--", linewidth=1)
    if buy_threshold is not None and sell_threshold is not None:
        predicted = modeled_data["predicted_log_price"]
        axis.plot(
            modeled_data["date"],
            np.exp(predicted + buy_threshold * residual_sigma),
            label=f"BUY threshold ({buy_threshold:+.2f})", color="#2ca02c", linestyle=":", linewidth=1.4,
        )
        axis.plot(
            modeled_data["date"],
            np.exp(predicted + sell_threshold * residual_sigma),
            label=f"SELL threshold ({sell_threshold:+.2f})", color="#d62728", linestyle=":", linewidth=1.4,
        )
    if signal_events is not None:
        buy_events = signal_events.loc[signal_events["signal"] == "BUY"]
        sell_events = signal_events.loc[signal_events["signal"] == "SELL"]
        if not buy_events.empty:
            axis.scatter(buy_events["date"], buy_events["close"], label="BUY event", color="#2ca02c", marker="^", s=55, zorder=4)
        if not sell_events.empty:
            axis.scatter(sell_events["date"], sell_events["close"], label="SELL event", color="#d62728", marker="v", s=55, zorder=4)
    axis.set_yscale("log")
    axis.set_title("BTC Price vs Log Trend")
    axis.set_xlabel("Date")
    axis.set_ylabel("BTC-USD price (log scale)")
    axis.grid(True, which="both", alpha=0.25)
    axis.legend(ncol=3)
    figure.tight_layout()
    return figure


def create_backtest_performance_figure(daily_values: pd.DataFrame):
    """Create an in-memory strategy-versus-buy-and-hold figure for Streamlit."""
    required_columns = {"date", "total_portfolio_value", "buy_and_hold_value"}
    missing = required_columns.difference(daily_values.columns)
    if missing:
        raise ValueError(
            f"Backtest chart data is missing columns: {', '.join(sorted(missing))}."
        )
    figure, axis = plt.subplots(figsize=(14, 8))
    axis.plot(
        daily_values["date"], daily_values["total_portfolio_value"],
        label="Compounding Machine", color="#1f77b4", linewidth=2,
    )
    axis.plot(
        daily_values["date"], daily_values["buy_and_hold_value"],
        label="Bitcoin buy and hold", color="#f7931a", linewidth=1.6,
    )
    axis.set_title("BTC Compounding Machine vs Buy and Hold")
    axis.set_xlabel("Date")
    axis.set_ylabel("Portfolio value (USD)")
    axis.grid(True, alpha=0.25)
    axis.legend()
    figure.tight_layout()
    return figure
