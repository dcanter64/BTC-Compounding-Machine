"""Project-wide defaults for the BTC Compounding Machine."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

BTC_TICKER = "BTC-USD"
DATA_FREQUENCY = "1d"
HISTORY_START = "2014-09-17"
MAX_STALE_DAYS = 3
CACHE_PATH = PROJECT_ROOT / "data" / "cache" / "btc_usd_daily.csv"
CHART_PATH = PROJECT_ROOT / "output" / "btc_price_vs_log_trend.png"
SIGNAL_EVENTS_PATH = PROJECT_ROOT / "output" / "signal_events.csv"
PORTFOLIO_LEDGER_PATH = PROJECT_ROOT / "output" / "portfolio_ledger.csv"
SKIPPED_EVENTS_PATH = PROJECT_ROOT / "output" / "skipped_events.csv"
BACKTEST_LEDGER_PATH = PROJECT_ROOT / "output" / "backtest_ledger.csv"
BACKTEST_SKIPPED_EVENTS_PATH = PROJECT_ROOT / "output" / "backtest_skipped_events.csv"
BACKTEST_DAILY_VALUES_PATH = PROJECT_ROOT / "output" / "backtest_daily_values.csv"
BACKTEST_SUMMARY_PATH = PROJECT_ROOT / "output" / "backtest_summary.json"
BACKTEST_CHART_PATH = PROJECT_ROOT / "output" / "backtest_performance.png"
BACKTEST_SIGNAL_EVENTS_PATH = PROJECT_ROOT / "output" / "backtest_signal_events.csv"
BACKTEST_EXECUTION_EVENTS_PATH = PROJECT_ROOT / "output" / "backtest_execution_events.csv"
BACKTEST_UNEXECUTED_SIGNALS_PATH = PROJECT_ROOT / "output" / "backtest_unexecuted_signals.csv"

DEFAULT_BUY_THRESHOLD = -1.5
DEFAULT_SELL_THRESHOLD = 2.0
DEFAULT_BUY_AMOUNT = 1_000.0
DEFAULT_SELL_AMOUNT = 500.0

# Synthetic examples only. Users should provide their own replay balances on
# the command line and must not commit private portfolio information here.
EXAMPLE_CASH_BALANCE = 1_000.0
EXAMPLE_BTC_HOLDINGS = 0.0

BACKTEST_START_DATE = "2017-01-01"
BACKTEST_STARTING_CASH = 1_000.0
BACKTEST_STARTING_BTC = 0.0
BACKTEST_MIN_TRAINING_OBSERVATIONS = 730
