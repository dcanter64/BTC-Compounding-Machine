"""Tests for fixed-dollar, spot-only portfolio accounting."""

from __future__ import annotations

import math

import pandas as pd
import pytest

from config import DEFAULT_BUY_AMOUNT, DEFAULT_SELL_AMOUNT
from src.portfolio import PortfolioError, portfolio_summary, simulate_event_ledger
from src.signals import BUY, SELL


def events(rows: list[tuple[str, float, str]]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": [date for date, _, _ in rows],
            "close": [price for _, price, _ in rows],
            "trend_price": [50_000.0] * len(rows),
            "z_score": [-1.6 if signal == BUY else 2.1 for _, _, signal in rows],
            "signal": [signal for _, _, signal in rows],
        }
    )


def test_buy_sell_ledger_and_portfolio_totals_are_accurate() -> None:
    simulation = simulate_event_ledger(
        events([("2024-01-01", 50_000.0, BUY), ("2024-02-01", 100_000.0, SELL)]),
        starting_cash=2_000.0,
        starting_btc=0.0,
        buy_amount=DEFAULT_BUY_AMOUNT,
        sell_amount=DEFAULT_SELL_AMOUNT,
    )
    summary = portfolio_summary(simulation.state, current_btc_price=100_000.0)

    assert len(simulation.ledger) == 2
    assert simulation.skipped_events.empty
    assert simulation.ledger.loc[0, "btc_quantity"] == pytest.approx(0.02)
    assert simulation.ledger.loc[0, "cash_after"] == pytest.approx(1_000.0)
    assert simulation.ledger.loc[1, "btc_quantity"] == pytest.approx(0.005)
    assert simulation.ledger.loc[1, "cash_after"] == pytest.approx(1_500.0)
    assert summary["btc_quantity"] == pytest.approx(0.015)
    assert summary["total_amount_purchased"] == pytest.approx(1_000.0)
    assert summary["total_amount_sold"] == pytest.approx(500.0)
    assert summary["total_portfolio_value"] == pytest.approx(3_000.0)
    assert summary["average_buy_price"] == pytest.approx(50_000.0)
    assert summary["average_sell_price"] == pytest.approx(100_000.0)


def test_unaffordable_buy_is_skipped_without_spending_available_cash() -> None:
    simulation = simulate_event_ledger(
        events([("2024-01-01", 50_000.0, BUY)]),
        starting_cash=999.99,
        starting_btc=0.0,
        buy_amount=DEFAULT_BUY_AMOUNT,
        sell_amount=DEFAULT_SELL_AMOUNT,
    )

    assert simulation.ledger.empty
    assert simulation.state.cash == pytest.approx(999.99)
    assert simulation.state.btc_quantity == 0
    assert simulation.skipped_events.loc[0, "reason"] == "Insufficient cash for exact BUY amount."


def test_unaffordable_sell_is_skipped_without_negative_bitcoin_holdings() -> None:
    simulation = simulate_event_ledger(
        events([("2024-01-01", 100_000.0, SELL)]),
        starting_cash=0.0,
        starting_btc=0.001,
        buy_amount=DEFAULT_BUY_AMOUNT,
        sell_amount=DEFAULT_SELL_AMOUNT,
    )

    assert simulation.ledger.empty
    assert simulation.state.cash == 0
    assert simulation.state.btc_quantity == pytest.approx(0.001)
    assert simulation.skipped_events.loc[0, "reason"] == "Insufficient BTC for exact SELL amount."


@pytest.mark.parametrize("amount", [0.0, -1.0, math.inf])
def test_transaction_amounts_must_be_positive_and_finite(amount: float) -> None:
    with pytest.raises(PortfolioError):
        simulate_event_ledger(
            events([("2024-01-01", 50_000.0, BUY)]),
            starting_cash=1_000.0,
            starting_btc=0.0,
            buy_amount=amount,
            sell_amount=DEFAULT_SELL_AMOUNT,
        )
