"""Run the complete Phase 1 data, trend, and chart workflow."""

from config import CHART_PATH
from src.charts import plot_btc_log_trend
from src.data_loader import load_btc_data
from src.trend_model import fit_log_trend


def main() -> None:
    price_data = load_btc_data()
    trend = fit_log_trend(price_data)
    chart_path = plot_btc_log_trend(trend.data, CHART_PATH)
    latest = trend.data.iloc[-1]

    print(f"Data date: {latest['date'].date()}")
    print(f"BTC close: ${latest['close']:,.2f}")
    print(f"Trend price: ${latest['trend_price']:,.2f}")
    print(f"Z-score: {latest['z_score']:+.2f} sigma")
    print(f"Residual sigma: {trend.residual_standard_deviation:.6f} log-price units")
    print(f"Chart: {chart_path}")


if __name__ == "__main__":
    main()
