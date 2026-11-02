"""Streamlit dashboard for the BTC Compounding Machine."""

from __future__ import annotations

import logging

import matplotlib.pyplot as plt
import streamlit as st

from config import (
    BACKTEST_MIN_TRAINING_OBSERVATIONS,
    BACKTEST_START_DATE,
    BACKTEST_STARTING_BTC,
    BACKTEST_STARTING_CASH,
    DEFAULT_BUY_AMOUNT,
    DEFAULT_BUY_THRESHOLD,
    DEFAULT_SELL_AMOUNT,
    DEFAULT_SELL_THRESHOLD,
)
from src.backtest import BacktestConfig, run_backtest
from src.charts import create_backtest_performance_figure, create_btc_log_trend_figure
from src.dashboard import build_current_dashboard_state
from src.data_loader import DataUnavailableError, DataValidationError, load_btc_data


LOGGER = logging.getLogger(__name__)


st.set_page_config(page_title="BTC Compounding Machine", page_icon="BTC", layout="wide")


@st.cache_data(ttl=900, max_entries=1, show_spinner=False)
def cached_price_data():
    """Load validated BTC data once per short dashboard cache interval."""
    return load_btc_data()


@st.cache_data(ttl=3600, max_entries=32, show_spinner=False)
def cached_backtest(
    price_data,
    buy_threshold: float,
    sell_threshold: float,
    buy_amount: float,
    sell_amount: float,
):
    """Recompute only when data or user strategy settings change."""
    config = BacktestConfig(
        starting_date=BACKTEST_START_DATE,
        starting_cash=BACKTEST_STARTING_CASH,
        starting_btc=BACKTEST_STARTING_BTC,
        buy_threshold=buy_threshold,
        sell_threshold=sell_threshold,
        buy_amount=buy_amount,
        sell_amount=sell_amount,
        min_training_observations=BACKTEST_MIN_TRAINING_OBSERVATIONS,
    )
    return run_backtest(price_data, config)


def _currency(value: float | None) -> str:
    return "N/A" if value is None else f"${value:,.2f}"


def _percent(value: float) -> str:
    return f"{value:.2%}"


def _signal_message(signal: str) -> None:
    if signal == "BUY":
        st.success("CURRENT SIGNAL: BUY")
    elif signal == "SELL":
        st.error("CURRENT SIGNAL: SELL")
    else:
        st.info("CURRENT SIGNAL: HOLD")


def main() -> None:
    st.title("BTC Compounding Machine")
    st.caption("Buy weakness. Sell strength. Sell less than you buy.")

    with st.sidebar:
        st.header("Compounding Settings")
        buy_threshold = st.number_input(
            "BUY threshold (sigma)", value=DEFAULT_BUY_THRESHOLD, min_value=-5.0,
            max_value=4.9, step=0.1, format="%.2f",
        )
        sell_threshold = st.number_input(
            "SELL threshold (sigma)", value=DEFAULT_SELL_THRESHOLD, min_value=-4.9,
            max_value=5.0, step=0.1, format="%.2f",
        )
        buy_amount = st.number_input(
            "BUY amount (USD)", value=DEFAULT_BUY_AMOUNT, min_value=1.0,
            max_value=1_000_000_000.0, step=100.0, format="%.2f",
        )
        sell_amount = st.number_input(
            "SELL amount (USD)", value=DEFAULT_SELL_AMOUNT, min_value=1.0,
            max_value=1_000_000_000.0, step=100.0, format="%.2f",
        )
        st.divider()
        st.caption(
            f"Historical backtest: {BACKTEST_START_DATE}, "
            f"${BACKTEST_STARTING_CASH:,.0f} cash, {BACKTEST_STARTING_BTC:g} BTC."
        )
        st.caption("Portfolio amounts shown below are synthetic backtest values.")

    if buy_threshold >= sell_threshold:
        st.error("The BUY threshold must be strictly lower than the SELL threshold.")
        return

    try:
        with st.spinner("Loading validated BTC history..."):
            price_data = cached_price_data()
        current_state = build_current_dashboard_state(
            price_data, buy_threshold, sell_threshold
        )
    except (DataUnavailableError, DataValidationError, ValueError):
        LOGGER.exception("Unable to calculate the dashboard")
        st.error("Unable to calculate the dashboard. Check the server logs for details.")
        return

    metric_columns = st.columns(4)
    metric_columns[0].metric("BTC PRICE", _currency(current_state.current_price))
    metric_columns[1].metric("LOG TREND", _currency(current_state.current_trend_price))
    metric_columns[2].metric("CURRENT Z-SCORE", f"{current_state.current_z_score:+.2f} sigma")
    metric_columns[3].metric("CURRENT SIGNAL", current_state.current_signal)
    _signal_message(current_state.current_signal)
    st.caption(
        "Current valuation uses the complete available history. The historical "
        "backtest below uses its separate prior-close-only expanding model."
    )

    st.subheader("Selected Threshold Prices")
    threshold_columns = st.columns(2)
    threshold_columns[0].metric(
        f"BUY LEVEL ({buy_threshold:+.2f} sigma)",
        _currency(current_state.buy_threshold_price),
        f"Distance: {current_state.distance_to_buy:+.2f} sigma",
    )
    threshold_columns[1].metric(
        f"SELL LEVEL ({sell_threshold:+.2f} sigma)",
        _currency(current_state.sell_threshold_price),
        f"Distance: {current_state.distance_to_sell:+.2f} sigma",
    )

    st.subheader("BTC Price vs Log Trend")
    trend_figure = create_btc_log_trend_figure(
        current_state.trend.data,
        signal_events=current_state.signal_events,
        residual_sigma=current_state.trend.residual_standard_deviation,
        buy_threshold=buy_threshold,
        sell_threshold=sell_threshold,
    )
    st.pyplot(trend_figure, width="stretch")
    plt.close(trend_figure)

    try:
        with st.spinner("Running no-look-ahead historical backtest..."):
            backtest = cached_backtest(
                price_data, buy_threshold, sell_threshold, buy_amount, sell_amount
            )
    except ValueError:
        LOGGER.exception("Unable to run the backtest")
        st.error("Unable to run the backtest. Check the server logs for details.")
        return

    summary = backtest.summary
    st.subheader("Portfolio and Backtest Summary")
    portfolio_columns = st.columns(4)
    portfolio_columns[0].metric("ENDING BTC", f"{summary['ending_btc_holdings']:.6f} BTC")
    portfolio_columns[1].metric("ENDING CASH", _currency(summary["ending_cash"]))
    portfolio_columns[2].metric("ENDING VALUE", _currency(summary["ending_portfolio_value"]))
    portfolio_columns[3].metric("TOTAL RETURN", _percent(summary["total_return"]))

    comparison_columns = st.columns(3)
    comparison_columns[0].metric("MAX DRAWDOWN", _percent(summary["maximum_drawdown"]))
    comparison_columns[1].metric("BUY & HOLD VALUE", _currency(summary["benchmark_ending_value"]))
    comparison_columns[2].metric("BUY & HOLD RETURN", _percent(summary["benchmark_total_return"]))
    st.caption(
        f"Executed events: {summary['total_buy_transactions']} BUY, "
        f"{summary['total_sell_transactions']} SELL. Skipped exact-dollar events: "
        f"{summary['skipped_events']}."
    )

    st.subheader("Compounding Machine vs Buy and Hold")
    performance_figure = create_backtest_performance_figure(backtest.daily_values)
    st.pyplot(performance_figure, width="stretch")
    plt.close(performance_figure)

    st.subheader("Transaction History")
    if backtest.simulation.ledger.empty:
        st.info("No historical events could be funded with the selected backtest capital.")
    else:
        st.dataframe(backtest.simulation.ledger, width="stretch", hide_index=True)

    with st.expander("Backtest assumptions and limitations"):
        st.markdown(
            "- Trend coefficients and sigma use only closes before each signal date.\n"
            "- Close-derived signals execute at the next available daily open.\n"
            "- No fees, spread, slippage, taxes, liquidity limits, or exchange outages are modeled.\n"
            "- Historical performance does not guarantee future results."
        )


if __name__ == "__main__":
    main()
