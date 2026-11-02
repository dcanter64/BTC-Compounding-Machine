"""Transparent BUY, SELL, and HOLD signal logic."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

BUY = "BUY"
SELL = "SELL"
HOLD = "HOLD"
SIGNALS = (BUY, SELL, HOLD)
EVENT_COLUMNS = ("date", "close", "trend_price", "z_score", "signal", "threshold_crossed")


class SignalConfigurationError(ValueError):
    """Raised when signal inputs or thresholds are invalid."""


def validate_thresholds(buy_threshold: float, sell_threshold: float) -> tuple[float, float]:
    """Return finite thresholds after enforcing a non-overlapping signal range."""
    try:
        buy = float(buy_threshold)
        sell = float(sell_threshold)
    except (TypeError, ValueError) as exc:
        raise SignalConfigurationError("BUY and SELL thresholds must be numeric.") from exc
    if not math.isfinite(buy) or not math.isfinite(sell):
        raise SignalConfigurationError("BUY and SELL thresholds must be finite.")
    if buy >= sell:
        raise SignalConfigurationError(
            "BUY threshold must be strictly lower than the SELL threshold."
        )
    return buy, sell


def signal_for_z_score(
    z_score: float, buy_threshold: float, sell_threshold: float
) -> str:
    """Return the current state for one z-score using inclusive boundaries."""
    buy, sell = validate_thresholds(buy_threshold, sell_threshold)
    try:
        z_value = float(z_score)
    except (TypeError, ValueError) as exc:
        raise SignalConfigurationError("Z-score must be numeric.") from exc
    if not math.isfinite(z_value):
        raise SignalConfigurationError("Z-score must be finite.")
    if z_value <= buy:
        return BUY
    if z_value >= sell:
        return SELL
    return HOLD


def build_signal_history(
    modeled_data: pd.DataFrame, buy_threshold: float, sell_threshold: float
) -> pd.DataFrame:
    """Add the daily BUY, SELL, or HOLD state to fitted trend-model data."""
    required_columns = {"date", "close", "trend_price", "z_score"}
    missing = required_columns.difference(modeled_data.columns)
    if missing:
        raise SignalConfigurationError(
            f"Signal data is missing columns: {', '.join(sorted(missing))}."
        )
    buy, sell = validate_thresholds(buy_threshold, sell_threshold)
    history = modeled_data.copy()
    z_scores = pd.to_numeric(history["z_score"], errors="coerce")
    if z_scores.isna().any() or not np.isfinite(z_scores).all():
        raise SignalConfigurationError("Signal data contains invalid z-scores.")

    history["signal"] = np.select(
        [z_scores <= buy, z_scores >= sell], [BUY, SELL], default=HOLD
    )
    return history


def find_signal_events(signal_history: pd.DataFrame, buy_threshold: float, sell_threshold: float) -> pd.DataFrame:
    """Return entries into BUY or SELL zones, excluding repeated in-zone days.

    The first data row cannot be an event because it has no preceding day from
    which to establish a threshold crossing.
    """
    required_columns = {"date", "close", "trend_price", "z_score", "signal"}
    missing = required_columns.difference(signal_history.columns)
    if missing:
        raise SignalConfigurationError(
            f"Signal history is missing columns: {', '.join(sorted(missing))}."
        )
    buy, sell = validate_thresholds(buy_threshold, sell_threshold)
    if not signal_history["signal"].isin(SIGNALS).all():
        raise SignalConfigurationError("Signal history contains an unrecognized state.")

    history = signal_history.copy()
    previous_state = history["signal"].shift(1)
    entered_buy_zone = (history["signal"] == BUY) & (previous_state != BUY) & previous_state.notna()
    entered_sell_zone = (history["signal"] == SELL) & (previous_state != SELL) & previous_state.notna()
    events = history.loc[entered_buy_zone | entered_sell_zone, ["date", "close", "trend_price", "z_score", "signal"]].copy()
    events["threshold_crossed"] = np.where(
        events["signal"] == BUY,
        f"BUY <= {buy:+.2f} sigma",
        f"SELL >= {sell:+.2f} sigma",
    )
    return events.loc[:, EVENT_COLUMNS].reset_index(drop=True)
