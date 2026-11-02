"""Tests for threshold states and entry-only signal events."""

from __future__ import annotations

import pandas as pd
import pytest

from src.signals import (
    BUY,
    HOLD,
    SELL,
    SignalConfigurationError,
    build_signal_history,
    find_signal_events,
    signal_for_z_score,
    validate_thresholds,
)


@pytest.mark.parametrize(
    ("z_score", "expected"),
    [(-1.6, BUY), (-1.5, BUY), (-1.49, HOLD), (1.99, HOLD), (2.0, SELL), (2.1, SELL)],
)
def test_signal_state_uses_inclusive_thresholds(z_score: float, expected: str) -> None:
    assert signal_for_z_score(z_score, -1.5, 2.0) == expected


@pytest.mark.parametrize("buy_threshold, sell_threshold", [(2.0, 2.0), (2.1, 2.0), (float("nan"), 2.0)])
def test_thresholds_must_be_finite_and_non_overlapping(
    buy_threshold: float, sell_threshold: float
) -> None:
    with pytest.raises(SignalConfigurationError):
        validate_thresholds(buy_threshold, sell_threshold)


def sample_signal_data() -> pd.DataFrame:
    z_scores = [-1.6, -1.7, -1.4, -1.5, -1.6, 0.0, 2.0, 2.2, 1.9, 2.1, -1.5]
    dates = pd.date_range("2024-01-01", periods=len(z_scores), freq="D")
    return pd.DataFrame(
        {
            "date": dates,
            "close": [40_000 + index * 100 for index in range(len(z_scores))],
            "trend_price": [45_000] * len(z_scores),
            "z_score": z_scores,
        }
    )


def test_only_entries_into_buy_or_sell_zones_create_events() -> None:
    history = build_signal_history(sample_signal_data(), -1.5, 2.0)
    events = find_signal_events(history, -1.5, 2.0)

    assert history["signal"].tolist() == [
        BUY, BUY, HOLD, BUY, BUY, HOLD, SELL, SELL, HOLD, SELL, BUY
    ]
    assert events["date"].tolist() == [
        pd.Timestamp("2024-01-04"),
        pd.Timestamp("2024-01-07"),
        pd.Timestamp("2024-01-10"),
        pd.Timestamp("2024-01-11"),
    ]
    assert events["signal"].tolist() == [BUY, SELL, SELL, BUY]
    assert events["threshold_crossed"].tolist() == [
        "BUY <= -1.50 sigma",
        "SELL >= +2.00 sigma",
        "SELL >= +2.00 sigma",
        "BUY <= -1.50 sigma",
    ]


def test_first_row_inside_a_zone_does_not_create_an_event() -> None:
    data = sample_signal_data().iloc[:2].copy()
    history = build_signal_history(data, -1.5, 2.0)

    events = find_signal_events(history, -1.5, 2.0)

    assert events.empty
