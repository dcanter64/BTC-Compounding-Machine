"""Historically actionable expanding-window backtest calculations."""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np
import pandas as pd

from src.portfolio import PortfolioSimulation, simulate_event_ledger
from src.signals import build_signal_history, find_signal_events, validate_thresholds


class BacktestError(ValueError):
    """Raised when a backtest cannot be calculated safely or fairly."""


@dataclass(frozen=True)
class BacktestConfig:
    """All user-configurable inputs for one transparent historical replay."""

    starting_date: str | pd.Timestamp
    starting_cash: float
    starting_btc: float
    buy_threshold: float
    sell_threshold: float
    buy_amount: float
    sell_amount: float
    min_training_observations: int = 730


@dataclass(frozen=True)
class BacktestResult:
    """Model, signals, ledger, daily valuations, and summary from one replay."""

    expanding_trend_data: pd.DataFrame
    signal_history: pd.DataFrame
    signal_events: pd.DataFrame
    execution_events: pd.DataFrame
    unexecuted_signal_events: pd.DataFrame
    simulation: PortfolioSimulation
    daily_values: pd.DataFrame
    summary: dict[str, float | int | str | None]


def _prepare_price_data(price_data: pd.DataFrame) -> pd.DataFrame:
    required_columns = {"date", "close"}
    missing = required_columns.difference(price_data.columns)
    if missing:
        raise BacktestError(f"Price data is missing columns: {', '.join(sorted(missing))}.")

    prepared = price_data.copy()
    prepared["date"] = pd.to_datetime(prepared["date"], errors="coerce")
    prepared["close"] = pd.to_numeric(prepared["close"], errors="coerce")
    if prepared[["date", "close"]].isna().any().any():
        raise BacktestError("Price data contains invalid dates or close prices.")
    if (prepared["close"] <= 0).any():
        raise BacktestError("Expanding log trend requires strictly positive close prices.")
    prepared = prepared.sort_values("date").reset_index(drop=True)
    if prepared["date"].duplicated().any():
        raise BacktestError("Price data contains duplicate dates.")
    return prepared


def _validate_backtest_config(config: BacktestConfig, price_data: pd.DataFrame) -> pd.Timestamp:
    try:
        starting_date = pd.Timestamp(config.starting_date).normalize()
    except (TypeError, ValueError) as exc:
        raise BacktestError("Starting date is invalid.") from exc
    if starting_date < price_data["date"].min() or starting_date > price_data["date"].max():
        raise BacktestError("Starting date must fall within the supplied price history.")
    validate_thresholds(config.buy_threshold, config.sell_threshold)
    for value, name in (
        (config.starting_cash, "Starting cash"),
        (config.starting_btc, "Starting BTC"),
    ):
        try:
            numeric_value = float(value)
        except (TypeError, ValueError) as exc:
            raise BacktestError(f"{name} must be numeric.") from exc
        if not math.isfinite(numeric_value) or numeric_value < 0:
            raise BacktestError(f"{name} must be finite and non-negative.")
    if not isinstance(config.min_training_observations, int) or config.min_training_observations < 3:
        raise BacktestError("Minimum training observations must be an integer of at least three.")
    return starting_date


def calculate_expanding_log_trend(
    price_data: pd.DataFrame,
    *,
    starting_date: str | pd.Timestamp,
    min_training_observations: int = 730,
) -> pd.DataFrame:
    """Calculate each daily z-score using only prices preceding that day.

    For a date *t*, regression coefficients and residual sigma are fitted from
    observations before *t*. The close on *t* only measures that day's residual,
    preventing it (or any future observation) from influencing its own signal.
    """
    prepared = _prepare_price_data(price_data)
    provisional_config = BacktestConfig(
        starting_date=starting_date,
        starting_cash=0.0,
        starting_btc=0.0,
        buy_threshold=-1.0,
        sell_threshold=1.0,
        buy_amount=1.0,
        sell_amount=1.0,
        min_training_observations=min_training_observations,
    )
    start = _validate_backtest_config(provisional_config, prepared)
    global_start = prepared["date"].iloc[0]
    days_since_start = (prepared["date"] - global_start).dt.total_seconds() / 86_400
    log_prices = np.log(prepared["close"].to_numpy(dtype=float))
    records: list[dict[str, object]] = []

    for position in range(len(prepared)):
        current_date = prepared.at[position, "date"]
        if current_date < start:
            continue
        record = prepared.iloc[position].to_dict()
        record["days_since_start"] = float(days_since_start.iloc[position])
        record["actual_log_price"] = float(log_prices[position])
        record["model_available"] = False
        record["predicted_log_price"] = np.nan
        record["trend_price"] = np.nan
        record["residual"] = np.nan
        record["residual_standard_deviation"] = np.nan
        record["z_score"] = np.nan

        if position >= min_training_observations:
            training_time = days_since_start.iloc[:position].to_numpy(dtype=float)
            training_log_prices = log_prices[:position]
            slope, intercept = np.polyfit(training_time, training_log_prices, deg=1)
            training_residuals = training_log_prices - (intercept + slope * training_time)
            sigma = float(np.std(training_residuals, ddof=0))
            if not np.isfinite(sigma) or sigma <= np.finfo(float).eps:
                raise BacktestError(
                    f"Residual sigma is not usable on {current_date.date()}."
                )
            predicted_log_price = float(intercept + slope * days_since_start.iloc[position])
            residual = float(log_prices[position] - predicted_log_price)
            record.update(
                {
                    "model_available": True,
                    "predicted_log_price": predicted_log_price,
                    "trend_price": float(np.exp(predicted_log_price)),
                    "residual": residual,
                    "residual_standard_deviation": sigma,
                    "z_score": residual / sigma,
                }
            )
        records.append(record)

    result = pd.DataFrame(records)
    if result.empty:
        raise BacktestError("No data is available on or after the requested starting date.")
    return result


def build_daily_portfolio_values(
    modeled_data: pd.DataFrame,
    ledger: pd.DataFrame,
    *,
    starting_cash: float,
    starting_btc: float,
) -> pd.DataFrame:
    """Value the post-transaction portfolio each available day without new rules."""
    required_columns = {"date", "close", "model_available"}
    missing = required_columns.difference(modeled_data.columns)
    if missing:
        raise BacktestError(f"Modeled data is missing columns: {', '.join(sorted(missing))}.")
    daily_values = modeled_data.loc[modeled_data["model_available"], ["date", "close"]].copy()
    if daily_values.empty:
        raise BacktestError("No actionable days are available after the warm-up period.")

    transaction_columns = {"date", "cash_after", "btc_holdings_after"}
    if ledger.empty:
        transactions = pd.DataFrame(
            {
                "date": pd.Series(dtype=daily_values["date"].dtype),
                "cash_after": pd.Series(dtype=float),
                "btc_holdings_after": pd.Series(dtype=float),
            }
        )
    else:
        missing_transactions = transaction_columns.difference(ledger.columns)
        if missing_transactions:
            raise BacktestError(
                f"Ledger is missing columns: {', '.join(sorted(missing_transactions))}."
            )
        transactions = ledger.loc[:, ["date", "cash_after", "btc_holdings_after"]].copy()
    daily_values = daily_values.merge(transactions, on="date", how="left")
    daily_values["cash"] = daily_values["cash_after"].ffill().fillna(float(starting_cash))
    daily_values["btc_quantity"] = (
        daily_values["btc_holdings_after"].ffill().fillna(float(starting_btc))
    )
    daily_values["btc_market_value"] = daily_values["btc_quantity"] * daily_values["close"]
    daily_values["total_portfolio_value"] = daily_values["cash"] + daily_values["btc_market_value"]
    return daily_values.drop(columns=["cash_after", "btc_holdings_after"])


def schedule_next_open_executions(
    signal_events: pd.DataFrame, modeled_data: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Schedule a close-derived signal for the next available daily open.

    A daily signal is known only after its close. Executing it at the following
    open prevents the same-close fill from introducing execution look-ahead bias.
    Signals with no following observation are retained in an unexecuted audit.
    """
    required_event_columns = {"date", "close", "trend_price", "z_score", "signal"}
    missing_events = required_event_columns.difference(signal_events.columns)
    if missing_events:
        raise BacktestError(
            f"Signal events are missing columns: {', '.join(sorted(missing_events))}."
        )
    required_model_columns = {"date", "open", "model_available"}
    missing_model = required_model_columns.difference(modeled_data.columns)
    if missing_model:
        raise BacktestError(
            f"Modeled data is missing columns: {', '.join(sorted(missing_model))}."
        )

    executable_days = modeled_data.loc[modeled_data["model_available"], ["date", "open"]].copy()
    executable_days["date"] = pd.to_datetime(executable_days["date"], errors="coerce")
    executable_days["open"] = pd.to_numeric(executable_days["open"], errors="coerce")
    if executable_days.isna().any().any() or (executable_days["open"] <= 0).any():
        raise BacktestError("Execution days contain invalid opening prices.")
    executable_days = executable_days.sort_values("date").reset_index(drop=True)

    execution_records: list[dict[str, object]] = []
    unexecuted_records: list[dict[str, object]] = []
    for _, signal_event in signal_events.iterrows():
        signal_date = pd.Timestamp(signal_event["date"])
        following_days = executable_days.loc[executable_days["date"] > signal_date]
        if following_days.empty:
            unexecuted_records.append(
                {
                    **signal_event.to_dict(),
                    "reason": "No subsequent daily open is available for execution.",
                }
            )
            continue
        execution_day = following_days.iloc[0]
        execution_record = signal_event.to_dict()
        execution_record["signal_date"] = signal_date
        execution_record["signal_close"] = float(signal_event["close"])
        execution_record["date"] = execution_day["date"]
        execution_record["close"] = float(execution_day["open"])
        execution_record["execution_price_source"] = "next_day_open"
        execution_records.append(execution_record)

    execution_events = pd.DataFrame(execution_records)
    if execution_events.empty:
        execution_events = signal_events.head(0).copy()
        execution_events["signal_date"] = pd.Series(dtype="datetime64[ns]")
        execution_events["signal_close"] = pd.Series(dtype=float)
        execution_events["execution_price_source"] = pd.Series(dtype=str)
    unexecuted_events = pd.DataFrame(unexecuted_records)
    if unexecuted_events.empty:
        unexecuted_events = signal_events.head(0).copy()
        unexecuted_events["reason"] = pd.Series(dtype=str)
    return execution_events, unexecuted_events


def add_buy_and_hold_benchmark(
    daily_values: pd.DataFrame,
    *,
    starting_cash: float,
    starting_btc: float,
) -> pd.DataFrame:
    """Add a buy-and-hold benchmark with the same initial total capital."""
    if daily_values.empty:
        raise BacktestError("Cannot create a benchmark without daily portfolio values.")
    benchmark = daily_values.copy()
    initial_price = float(benchmark["close"].iloc[0])
    initial_capital = float(starting_cash) + float(starting_btc) * initial_price
    if initial_capital <= 0:
        raise BacktestError("Backtest requires positive initial portfolio capital.")
    benchmark_btc_quantity = initial_capital / initial_price
    benchmark["buy_and_hold_btc_quantity"] = benchmark_btc_quantity
    benchmark["buy_and_hold_value"] = benchmark_btc_quantity * benchmark["close"]
    return benchmark


def calculate_performance_metrics(values: pd.Series) -> dict[str, float]:
    """Return ending value, total return, and maximum drawdown for a value series."""
    series = pd.to_numeric(values, errors="coerce")
    if series.empty or series.isna().any() or (series <= 0).any():
        raise BacktestError("Performance values must be present and greater than zero.")
    initial_value = float(series.iloc[0])
    ending_value = float(series.iloc[-1])
    drawdowns = series / series.cummax() - 1.0
    return {
        "initial_value": initial_value,
        "ending_value": ending_value,
        "total_return": ending_value / initial_value - 1.0,
        "maximum_drawdown": float(drawdowns.min()),
    }


def run_backtest(price_data: pd.DataFrame, config: BacktestConfig) -> BacktestResult:
    """Run one configuration using expanding signals and the existing ledger engine."""
    prepared = _prepare_price_data(price_data)
    starting_date = _validate_backtest_config(config, prepared)
    expanding_data = calculate_expanding_log_trend(
        prepared,
        starting_date=starting_date,
        min_training_observations=config.min_training_observations,
    )
    actionable_data = expanding_data.loc[expanding_data["model_available"]].copy()
    if actionable_data.empty:
        raise BacktestError("No actionable dates are available with the selected warm-up period.")
    signal_history = build_signal_history(
        actionable_data, config.buy_threshold, config.sell_threshold
    )
    signal_events = find_signal_events(
        signal_history, config.buy_threshold, config.sell_threshold
    )
    execution_events, unexecuted_signal_events = schedule_next_open_executions(
        signal_events, expanding_data
    )
    simulation = simulate_event_ledger(
        execution_events,
        starting_cash=config.starting_cash,
        starting_btc=config.starting_btc,
        buy_amount=config.buy_amount,
        sell_amount=config.sell_amount,
    )
    daily_values = build_daily_portfolio_values(
        expanding_data,
        simulation.ledger,
        starting_cash=config.starting_cash,
        starting_btc=config.starting_btc,
    )
    daily_values = add_buy_and_hold_benchmark(
        daily_values,
        starting_cash=config.starting_cash,
        starting_btc=config.starting_btc,
    )
    strategy_metrics = calculate_performance_metrics(daily_values["total_portfolio_value"])
    benchmark_metrics = calculate_performance_metrics(daily_values["buy_and_hold_value"])
    final_state = simulation.state
    summary: dict[str, float | int | str | None] = {
        "starting_date": daily_values["date"].iloc[0].date().isoformat(),
        "ending_date": daily_values["date"].iloc[-1].date().isoformat(),
        "ending_portfolio_value": strategy_metrics["ending_value"],
        "ending_btc_holdings": final_state.btc_quantity,
        "ending_cash": final_state.cash,
        "total_buy_transactions": final_state.buy_transactions,
        "total_sell_transactions": final_state.sell_transactions,
        "dollars_spent_buying": final_state.total_amount_purchased,
        "dollars_received_selling": final_state.total_amount_sold,
        "average_buy_price": (
            final_state.total_amount_purchased / final_state.total_btc_purchased
            if final_state.total_btc_purchased > 0 else None
        ),
        "average_sell_price": (
            final_state.total_amount_sold / final_state.total_btc_sold
            if final_state.total_btc_sold > 0 else None
        ),
        "maximum_drawdown": strategy_metrics["maximum_drawdown"],
        "total_return": strategy_metrics["total_return"],
        "benchmark_ending_value": benchmark_metrics["ending_value"],
        "benchmark_maximum_drawdown": benchmark_metrics["maximum_drawdown"],
        "benchmark_total_return": benchmark_metrics["total_return"],
        "skipped_events": len(simulation.skipped_events),
        "unexecuted_signals": len(unexecuted_signal_events),
    }
    return BacktestResult(
        expanding_trend_data=expanding_data,
        signal_history=signal_history,
        signal_events=signal_events,
        execution_events=execution_events,
        unexecuted_signal_events=unexecuted_signal_events,
        simulation=simulation,
        daily_values=daily_values,
        summary=summary,
    )
