"""Run the complete Phase 2 signal and chart workflow."""

from config import (
    CHART_PATH,
    DEFAULT_BUY_THRESHOLD,
    DEFAULT_SELL_THRESHOLD,
    SIGNAL_EVENTS_PATH,
)
from src.charts import plot_btc_log_trend
from src.data_loader import load_btc_data
from src.signals import build_signal_history, find_signal_events
from src.trend_model import fit_log_trend


def main() -> None:
    price_data = load_btc_data()
    trend = fit_log_trend(price_data)
    signal_history = build_signal_history(
        trend.data, DEFAULT_BUY_THRESHOLD, DEFAULT_SELL_THRESHOLD
    )
    signal_events = find_signal_events(
        signal_history, DEFAULT_BUY_THRESHOLD, DEFAULT_SELL_THRESHOLD
    )
    SIGNAL_EVENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    signal_events.to_csv(SIGNAL_EVENTS_PATH, index=False)
    chart_path = plot_btc_log_trend(trend.data, CHART_PATH, signal_events)
    latest = signal_history.iloc[-1]

    print(f"Data date: {latest['date'].date()}")
    print(f"BTC close: ${latest['close']:,.2f}")
    print(f"Trend price: ${latest['trend_price']:,.2f}")
    print(f"Z-score: {latest['z_score']:+.2f} sigma")
    print(f"BUY threshold: {DEFAULT_BUY_THRESHOLD:+.2f} sigma")
    print(f"SELL threshold: {DEFAULT_SELL_THRESHOLD:+.2f} sigma")
    print(f"Current signal: {latest['signal']}")
    print(f"Historical BUY events: {(signal_events['signal'] == 'BUY').sum()}")
    print(f"Historical SELL events: {(signal_events['signal'] == 'SELL').sum()}")
    print(f"Signal event table: {SIGNAL_EVENTS_PATH}")
    print(f"Chart: {chart_path}")


if __name__ == "__main__":
    main()
