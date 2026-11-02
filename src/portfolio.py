"""Spot-Bitcoin portfolio accounting for Phase 3."""

from __future__ import annotations

from dataclasses import dataclass, replace
import math

import pandas as pd

from src.signals import BUY, SELL

LEDGER_COLUMNS = (
    "date",
    "signal_date",
    "action",
    "btc_price",
    "trend_price",
    "z_score",
    "dollar_amount",
    "btc_quantity",
    "cash_after",
    "btc_holdings_after",
    "total_portfolio_value",
)
SKIPPED_EVENT_COLUMNS = (
    "date",
    "signal_date",
    "action",
    "btc_price",
    "trend_price",
    "z_score",
    "dollar_amount",
    "btc_quantity",
    "reason",
)


class PortfolioError(ValueError):
    """Raised when portfolio state, signals, or transaction amounts are invalid."""


@dataclass(frozen=True)
class PortfolioState:
    """Cash, Bitcoin, and cumulative accounting after zero or more transactions."""

    cash: float
    btc_quantity: float
    total_amount_purchased: float = 0.0
    total_amount_sold: float = 0.0
    total_btc_purchased: float = 0.0
    total_btc_sold: float = 0.0
    buy_transactions: int = 0
    sell_transactions: int = 0


@dataclass(frozen=True)
class PortfolioSimulation:
    """Final portfolio state plus executed and skipped transaction records."""

    state: PortfolioState
    ledger: pd.DataFrame
    skipped_events: pd.DataFrame


def _non_negative_finite(value: float, name: str) -> float:
    try:
        numeric_value = float(value)
    except (TypeError, ValueError) as exc:
        raise PortfolioError(f"{name} must be numeric.") from exc
    if not math.isfinite(numeric_value) or numeric_value < 0:
        raise PortfolioError(f"{name} must be finite and non-negative.")
    return numeric_value


def _positive_finite(value: float, name: str) -> float:
    numeric_value = _non_negative_finite(value, name)
    if numeric_value == 0:
        raise PortfolioError(f"{name} must be greater than zero.")
    return numeric_value


def create_portfolio_state(starting_cash: float, starting_btc: float) -> PortfolioState:
    """Create an initial fully funded spot portfolio state."""
    return PortfolioState(
        cash=_non_negative_finite(starting_cash, "Starting cash"),
        btc_quantity=_non_negative_finite(starting_btc, "Starting BTC"),
    )


def _validated_events(signal_events: pd.DataFrame) -> pd.DataFrame:
    required_columns = {"date", "close", "trend_price", "z_score", "signal"}
    missing = required_columns.difference(signal_events.columns)
    if missing:
        raise PortfolioError(
            f"Signal events are missing columns: {', '.join(sorted(missing))}."
        )

    events = signal_events.copy()
    events["date"] = pd.to_datetime(events["date"], errors="coerce")
    for column in ("close", "trend_price", "z_score"):
        events[column] = pd.to_numeric(events[column], errors="coerce")
    if events[["date", "close", "trend_price", "z_score"]].isna().any().any():
        raise PortfolioError("Signal events contain invalid dates or numeric values.")
    if (events[["close", "trend_price"]] <= 0).any().any():
        raise PortfolioError("Signal event prices must be greater than zero.")
    if not events["signal"].isin((BUY, SELL)).all():
        raise PortfolioError("Portfolio processing accepts BUY and SELL events only.")
    if events["date"].duplicated().any():
        raise PortfolioError("Signal events must not contain duplicate dates.")
    return events.sort_values("date").reset_index(drop=True)


def _event_record(event: pd.Series, action: str, dollar_amount: float, btc_quantity: float) -> dict[str, object]:
    signal_date = event["signal_date"] if "signal_date" in event.index else event["date"]
    return {
        "date": event["date"],
        "signal_date": signal_date,
        "action": action,
        "btc_price": float(event["close"]),
        "trend_price": float(event["trend_price"]),
        "z_score": float(event["z_score"]),
        "dollar_amount": dollar_amount,
        "btc_quantity": btc_quantity,
    }


def _execute_buy(
    state: PortfolioState, event: pd.Series, buy_amount: float
) -> tuple[PortfolioState, dict[str, object] | None, dict[str, object] | None]:
    price = float(event["close"])
    btc_quantity = buy_amount / price
    base_record = _event_record(event, BUY, buy_amount, btc_quantity)
    if state.cash < buy_amount:
        return state, None, {**base_record, "reason": "Insufficient cash for exact BUY amount."}

    updated_state = replace(
        state,
        cash=state.cash - buy_amount,
        btc_quantity=state.btc_quantity + btc_quantity,
        total_amount_purchased=state.total_amount_purchased + buy_amount,
        total_btc_purchased=state.total_btc_purchased + btc_quantity,
        buy_transactions=state.buy_transactions + 1,
    )
    return updated_state, {
        **base_record,
        "cash_after": updated_state.cash,
        "btc_holdings_after": updated_state.btc_quantity,
        "total_portfolio_value": updated_state.cash + updated_state.btc_quantity * price,
    }, None


def _execute_sell(
    state: PortfolioState, event: pd.Series, sell_amount: float
) -> tuple[PortfolioState, dict[str, object] | None, dict[str, object] | None]:
    price = float(event["close"])
    btc_quantity = sell_amount / price
    base_record = _event_record(event, SELL, sell_amount, btc_quantity)
    if state.btc_quantity < btc_quantity:
        return state, None, {**base_record, "reason": "Insufficient BTC for exact SELL amount."}

    updated_btc = state.btc_quantity - btc_quantity
    updated_state = replace(
        state,
        cash=state.cash + sell_amount,
        btc_quantity=max(0.0, updated_btc),
        total_amount_sold=state.total_amount_sold + sell_amount,
        total_btc_sold=state.total_btc_sold + btc_quantity,
        sell_transactions=state.sell_transactions + 1,
    )
    return updated_state, {
        **base_record,
        "cash_after": updated_state.cash,
        "btc_holdings_after": updated_state.btc_quantity,
        "total_portfolio_value": updated_state.cash + updated_state.btc_quantity * price,
    }, None


def simulate_event_ledger(
    signal_events: pd.DataFrame,
    *,
    starting_cash: float,
    starting_btc: float,
    buy_amount: float,
    sell_amount: float,
) -> PortfolioSimulation:
    """Execute fixed-dollar BUY/SELL events without borrowing, leverage, or partial fills."""
    events = _validated_events(signal_events)
    buy_amount = _positive_finite(buy_amount, "BUY amount")
    sell_amount = _positive_finite(sell_amount, "SELL amount")
    state = create_portfolio_state(starting_cash, starting_btc)
    ledger_records: list[dict[str, object]] = []
    skipped_records: list[dict[str, object]] = []

    for _, event in events.iterrows():
        if event["signal"] == BUY:
            state, transaction, skipped = _execute_buy(state, event, buy_amount)
        else:
            state, transaction, skipped = _execute_sell(state, event, sell_amount)
        if transaction is not None:
            ledger_records.append(transaction)
        if skipped is not None:
            skipped_records.append(skipped)

    ledger = pd.DataFrame(ledger_records, columns=LEDGER_COLUMNS)
    skipped_events = pd.DataFrame(skipped_records, columns=SKIPPED_EVENT_COLUMNS)
    return PortfolioSimulation(state=state, ledger=ledger, skipped_events=skipped_events)


def portfolio_summary(state: PortfolioState, current_btc_price: float) -> dict[str, float | int | None]:
    """Return current portfolio value and transparent aggregate transaction metrics."""
    current_price = _positive_finite(current_btc_price, "Current BTC price")
    average_buy_price = (
        state.total_amount_purchased / state.total_btc_purchased
        if state.total_btc_purchased > 0
        else None
    )
    average_sell_price = (
        state.total_amount_sold / state.total_btc_sold
        if state.total_btc_sold > 0
        else None
    )
    btc_market_value = state.btc_quantity * current_price
    return {
        "cash": state.cash,
        "btc_quantity": state.btc_quantity,
        "btc_market_value": btc_market_value,
        "total_portfolio_value": state.cash + btc_market_value,
        "total_amount_purchased": state.total_amount_purchased,
        "total_amount_sold": state.total_amount_sold,
        "buy_transactions": state.buy_transactions,
        "sell_transactions": state.sell_transactions,
        "average_buy_price": average_buy_price,
        "average_sell_price": average_sell_price,
    }
