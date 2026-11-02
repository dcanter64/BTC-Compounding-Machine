"""Run the Phase 4 expanding-window BTC Compounding Machine backtest."""

from __future__ import annotations

import argparse
import json

from config import (
    BACKTEST_CHART_PATH,
    BACKTEST_DAILY_VALUES_PATH,
    BACKTEST_EXECUTION_EVENTS_PATH,
    BACKTEST_LEDGER_PATH,
    BACKTEST_MIN_TRAINING_OBSERVATIONS,
    BACKTEST_SIGNAL_EVENTS_PATH,
    BACKTEST_SKIPPED_EVENTS_PATH,
    BACKTEST_START_DATE,
    BACKTEST_STARTING_BTC,
    BACKTEST_STARTING_CASH,
    BACKTEST_SUMMARY_PATH,
    BACKTEST_UNEXECUTED_SIGNALS_PATH,
    DEFAULT_BUY_AMOUNT,
    DEFAULT_BUY_THRESHOLD,
    DEFAULT_SELL_AMOUNT,
    DEFAULT_SELL_THRESHOLD,
)
from src.backtest import BacktestConfig, run_backtest
from src.charts import plot_backtest_performance
from src.data_loader import load_btc_data


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a no-look-ahead BTC Compounding Machine historical backtest."
    )
    parser.add_argument("--starting-date", default=BACKTEST_START_DATE)
    parser.add_argument("--starting-cash", type=float, default=BACKTEST_STARTING_CASH)
    parser.add_argument("--starting-btc", type=float, default=BACKTEST_STARTING_BTC)
    parser.add_argument("--buy-threshold", type=float, default=DEFAULT_BUY_THRESHOLD)
    parser.add_argument("--sell-threshold", type=float, default=DEFAULT_SELL_THRESHOLD)
    parser.add_argument("--buy-amount", type=float, default=DEFAULT_BUY_AMOUNT)
    parser.add_argument("--sell-amount", type=float, default=DEFAULT_SELL_AMOUNT)
    parser.add_argument(
        "--min-training-observations",
        type=int,
        default=BACKTEST_MIN_TRAINING_OBSERVATIONS,
    )
    return parser.parse_args()


def _currency(value: float | None) -> str:
    return "N/A" if value is None else f"${value:,.2f}"


def _percentage(value: float) -> str:
    return f"{value:.2%}"


def main() -> None:
    arguments = parse_arguments()
    config = BacktestConfig(
        starting_date=arguments.starting_date,
        starting_cash=arguments.starting_cash,
        starting_btc=arguments.starting_btc,
        buy_threshold=arguments.buy_threshold,
        sell_threshold=arguments.sell_threshold,
        buy_amount=arguments.buy_amount,
        sell_amount=arguments.sell_amount,
        min_training_observations=arguments.min_training_observations,
    )
    result = run_backtest(load_btc_data(), config)
    BACKTEST_LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    result.simulation.ledger.to_csv(BACKTEST_LEDGER_PATH, index=False)
    result.simulation.skipped_events.to_csv(BACKTEST_SKIPPED_EVENTS_PATH, index=False)
    result.signal_events.to_csv(BACKTEST_SIGNAL_EVENTS_PATH, index=False)
    result.execution_events.to_csv(BACKTEST_EXECUTION_EVENTS_PATH, index=False)
    result.unexecuted_signal_events.to_csv(BACKTEST_UNEXECUTED_SIGNALS_PATH, index=False)
    result.daily_values.to_csv(BACKTEST_DAILY_VALUES_PATH, index=False)
    with BACKTEST_SUMMARY_PATH.open("w", encoding="utf-8") as summary_file:
        json.dump(result.summary, summary_file, indent=2)
    chart_path = plot_backtest_performance(result.daily_values, BACKTEST_CHART_PATH)
    summary = result.summary

    print("Phase 4 historical backtest - expanding model uses only prior daily closes.")
    print(f"Configured start date: {arguments.starting_date}")
    print(f"Actionable period: {summary['starting_date']} to {summary['ending_date']}")
    print(f"Starting cash: {_currency(arguments.starting_cash)}")
    print(f"Starting BTC: {arguments.starting_btc:.8f}")
    print(f"Ending portfolio value: {_currency(summary['ending_portfolio_value'])}")
    print(f"Ending BTC holdings: {summary['ending_btc_holdings']:.8f}")
    print(f"Ending cash: {_currency(summary['ending_cash'])}")
    print(f"BUY transactions: {summary['total_buy_transactions']}")
    print(f"SELL transactions: {summary['total_sell_transactions']}")
    print(f"Dollars spent buying: {_currency(summary['dollars_spent_buying'])}")
    print(f"Dollars received selling: {_currency(summary['dollars_received_selling'])}")
    print(f"Average BUY price: {_currency(summary['average_buy_price'])}")
    print(f"Average SELL price: {_currency(summary['average_sell_price'])}")
    print(f"Compounding Machine total return: {_percentage(summary['total_return'])}")
    print(f"Compounding Machine maximum drawdown: {_percentage(summary['maximum_drawdown'])}")
    print(f"Buy-and-hold ending value: {_currency(summary['benchmark_ending_value'])}")
    print(f"Buy-and-hold total return: {_percentage(summary['benchmark_total_return'])}")
    print(f"Buy-and-hold maximum drawdown: {_percentage(summary['benchmark_maximum_drawdown'])}")
    print(f"Skipped events: {summary['skipped_events']}")
    print(f"Signals without a following open: {summary['unexecuted_signals']}")
    print(f"Performance chart: {chart_path}")
    print(f"Summary: {BACKTEST_SUMMARY_PATH}")


if __name__ == "__main__":
    main()
