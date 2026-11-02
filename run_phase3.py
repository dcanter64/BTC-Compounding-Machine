"""Run the Phase 3 spot-Bitcoin ledger replay for explicit starting balances."""

from __future__ import annotations

import argparse

from config import (
    DEFAULT_BUY_AMOUNT,
    DEFAULT_BUY_THRESHOLD,
    DEFAULT_SELL_AMOUNT,
    DEFAULT_SELL_THRESHOLD,
    EXAMPLE_BTC_HOLDINGS,
    EXAMPLE_CASH_BALANCE,
    PORTFOLIO_LEDGER_PATH,
    SKIPPED_EVENTS_PATH,
)
from src.data_loader import load_btc_data
from src.portfolio import portfolio_summary, simulate_event_ledger
from src.signals import build_signal_history, find_signal_events
from src.trend_model import fit_log_trend


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Replay Phase 2 entry events through the Phase 3 spot-BTC ledger."
    )
    parser.add_argument(
        "--starting-cash",
        type=float,
        default=EXAMPLE_CASH_BALANCE,
        help="Cash available at the beginning of this ledger replay (default: synthetic $1,000.00).",
    )
    parser.add_argument(
        "--starting-btc",
        type=float,
        default=EXAMPLE_BTC_HOLDINGS,
        help="BTC held at the beginning of this ledger replay (default: synthetic 0 BTC).",
    )
    return parser.parse_args()


def _format_currency(value: float | None) -> str:
    return "N/A" if value is None else f"${value:,.2f}"


def main() -> None:
    arguments = parse_arguments()
    price_data = load_btc_data()
    trend = fit_log_trend(price_data)
    signal_history = build_signal_history(
        trend.data, DEFAULT_BUY_THRESHOLD, DEFAULT_SELL_THRESHOLD
    )
    signal_events = find_signal_events(
        signal_history, DEFAULT_BUY_THRESHOLD, DEFAULT_SELL_THRESHOLD
    )
    simulation = simulate_event_ledger(
        signal_events,
        starting_cash=arguments.starting_cash,
        starting_btc=arguments.starting_btc,
        buy_amount=DEFAULT_BUY_AMOUNT,
        sell_amount=DEFAULT_SELL_AMOUNT,
    )
    latest = signal_history.iloc[-1]
    summary = portfolio_summary(simulation.state, float(latest["close"]))

    PORTFOLIO_LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    simulation.ledger.to_csv(PORTFOLIO_LEDGER_PATH, index=False)
    simulation.skipped_events.to_csv(SKIPPED_EVENTS_PATH, index=False)

    print("Development ledger replay only; this is not a Phase 4 historical backtest.")
    print(f"Latest price date: {latest['date'].date()}")
    print(f"Starting cash: ${arguments.starting_cash:,.2f}")
    print(f"Starting BTC: {arguments.starting_btc:.8f}")
    print(f"Executed BUY transactions: {summary['buy_transactions']}")
    print(f"Executed SELL transactions: {summary['sell_transactions']}")
    print(f"Skipped events: {len(simulation.skipped_events)}")
    print(f"BTC holdings: {summary['btc_quantity']:.8f}")
    print(f"Cash: {_format_currency(summary['cash'])}")
    print(f"BTC market value: {_format_currency(summary['btc_market_value'])}")
    print(f"Total portfolio value: {_format_currency(summary['total_portfolio_value'])}")
    print(f"Dollars used for BUY transactions: {_format_currency(summary['total_amount_purchased'])}")
    print(f"Dollars received from SELL transactions: {_format_currency(summary['total_amount_sold'])}")
    print(f"Average BUY price: {_format_currency(summary['average_buy_price'])}")
    print(f"Average SELL price: {_format_currency(summary['average_sell_price'])}")
    print(f"Ledger: {PORTFOLIO_LEDGER_PATH}")
    print(f"Skipped event audit: {SKIPPED_EVENTS_PATH}")


if __name__ == "__main__":
    main()
