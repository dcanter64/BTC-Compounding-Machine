"""Daily BTC-USD retrieval, validation, and local caching."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pandas as pd

from config import BTC_TICKER, CACHE_PATH, DATA_FREQUENCY, HISTORY_START, MAX_STALE_DAYS

REQUIRED_COLUMNS = ("date", "open", "high", "low", "close", "volume")
PRICE_COLUMNS = ("open", "high", "low", "close")
Downloader = Callable[[pd.Timestamp, pd.Timestamp], pd.DataFrame]


class DataValidationError(ValueError):
    """Raised when price history is malformed or unsafe to use."""


class DataUnavailableError(RuntimeError):
    """Raised when no fresh or cached usable price history is available."""


def _normalise_column_name(column: object) -> str:
    """Return a field name from plain or yfinance MultiIndex columns."""
    if isinstance(column, tuple):
        column = column[0]
    return str(column).strip().lower().replace(" ", "_")


def normalise_price_frame(raw_data: pd.DataFrame) -> pd.DataFrame:
    """Convert a Yahoo Finance response into the project's stable schema."""
    if raw_data.empty:
        raise DataValidationError("BTC price source returned no rows.")

    frame = raw_data.reset_index().copy()
    frame.columns = [_normalise_column_name(column) for column in frame.columns]
    if "datetime" in frame.columns and "date" not in frame.columns:
        frame = frame.rename(columns={"datetime": "date"})

    missing = set(REQUIRED_COLUMNS).difference(frame.columns)
    if missing:
        raise DataValidationError(
            f"BTC data is missing required columns: {', '.join(sorted(missing))}."
        )
    return frame.loc[:, list(REQUIRED_COLUMNS)].copy()


def validate_btc_data(data: pd.DataFrame) -> pd.DataFrame:
    """Validate and return clean, date-sorted daily BTC price data.

    Every price must be present and strictly positive. Volume must be present and
    non-negative. The function fails rather than guessing how to repair data.
    """
    missing = set(REQUIRED_COLUMNS).difference(data.columns)
    if missing:
        raise DataValidationError(
            f"BTC data is missing required columns: {', '.join(sorted(missing))}."
        )

    frame = data.loc[:, list(REQUIRED_COLUMNS)].copy()
    parsed_dates = pd.to_datetime(frame["date"], errors="coerce", utc=True)
    if parsed_dates.isna().any():
        raise DataValidationError("BTC data contains malformed dates.")
    frame["date"] = parsed_dates.dt.tz_convert(None).dt.normalize()
    if frame["date"].duplicated().any():
        raise DataValidationError("BTC data contains duplicate dates.")

    numeric_columns = [*PRICE_COLUMNS, "volume"]
    for column in numeric_columns:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    if frame.loc[:, numeric_columns].isna().any().any():
        raise DataValidationError("BTC data contains missing or non-numeric values.")
    if (frame.loc[:, list(PRICE_COLUMNS)] <= 0).any().any():
        raise DataValidationError("BTC data contains zero or negative prices.")
    if (frame["volume"] < 0).any():
        raise DataValidationError("BTC data contains negative volume.")
    return frame.sort_values("date").reset_index(drop=True)


def _download_yahoo_data(start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    """Download daily BTC-USD OHLCV history from Yahoo Finance."""
    try:
        import yfinance as yf

        raw_data = yf.download(
            BTC_TICKER,
            start=start.date().isoformat(),
            end=end.date().isoformat(),
            interval=DATA_FREQUENCY,
            auto_adjust=False,
            progress=False,
            threads=False,
        )
    except Exception as exc:  # pragma: no cover - network/provider dependent
        raise DataUnavailableError(
            f"Could not retrieve {BTC_TICKER} from Yahoo Finance: {exc}"
        ) from exc
    return normalise_price_frame(raw_data)


def _read_cache(cache_path: Path) -> pd.DataFrame | None:
    if not cache_path.exists():
        return None
    try:
        return validate_btc_data(pd.read_csv(cache_path))
    except (OSError, pd.errors.ParserError, DataValidationError) as exc:
        raise DataValidationError(f"Cached BTC data at {cache_path} is invalid: {exc}") from exc


def _write_cache(data: pd.DataFrame, cache_path: Path) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = cache_path.with_suffix(".tmp")
    data.to_csv(temporary_path, index=False)
    temporary_path.replace(cache_path)


def _combine_history(cached: pd.DataFrame | None, fresh: pd.DataFrame) -> pd.DataFrame:
    frames = [fresh] if cached is None else [cached, fresh]
    combined = pd.concat(frames, ignore_index=True)
    return validate_btc_data(combined.drop_duplicates(subset="date", keep="last"))


def _as_utc_naive_day(value: pd.Timestamp | str) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)
    if timestamp.tz is not None:
        timestamp = timestamp.tz_convert("UTC").tz_localize(None)
    return timestamp.normalize()


def _check_freshness(data: pd.DataFrame, today: pd.Timestamp) -> None:
    latest_date = data["date"].max()
    oldest_acceptable_date = today - pd.DateOffset(days=MAX_STALE_DAYS)
    if latest_date < oldest_acceptable_date:
        raise DataValidationError(
            f"BTC data is stale: latest date is {latest_date.date()}, older than "
            f"{MAX_STALE_DAYS} days."
        )


def load_btc_data(
    cache_path: Path = CACHE_PATH,
    *,
    downloader: Downloader | None = None,
    today: pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Return fresh, validated BTC history and update its local cache.

    The provider refresh overlaps the previous seven days so late corrections can
    replace cached rows. If it fails, cached data is usable only when valid and
    no more than three days stale.
    """
    current_day = _as_utc_naive_day(pd.Timestamp.now(tz="UTC") if today is None else today)
    cache_path = Path(cache_path)
    cached = _read_cache(cache_path)
    download_start = pd.Timestamp(HISTORY_START)
    if cached is not None:
        download_start = cached["date"].max() - pd.DateOffset(days=7)
    download_end = current_day + pd.DateOffset(days=1)
    fetch = _download_yahoo_data if downloader is None else downloader

    try:
        fresh = validate_btc_data(fetch(download_start, download_end))
        data = _combine_history(cached, fresh)
        _write_cache(data, cache_path)
    except (DataValidationError, DataUnavailableError):
        if cached is None:
            raise
        data = cached
    except Exception as exc:
        if cached is None:
            raise DataUnavailableError(f"Could not obtain usable BTC data: {exc}") from exc
        data = cached

    _check_freshness(data, current_day)
    return data
