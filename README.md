# BTC Compounding Machine

A transparent Bitcoin valuation tool inspired by the simple framework: buy
weakness, sell strength, and sell less than you buy. It is not a price
prediction system and does not reproduce any proprietary methodology.

## Current scope: Phases 1–5

Phase 1 retrieves daily `BTC-USD` OHLCV data from Yahoo Finance, validates it,
caches it locally, and fits a long-term linear trend in natural-log closing
prices. It produces a **BTC Price vs Log Trend** chart with ±1σ and ±2σ price
bands. It also calculates transparent BUY, SELL, and HOLD states and marks only
entries into the configured BUY or SELL zones. Signal-driven, spot-only
portfolio accounting, a transaction ledger, an expanding-window historical
backtest, and a Streamlit dashboard are implemented. No exchange integration or
live order execution exists.

## Setup

Python 3.11 or newer is required.

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Run the signal workflow

```powershell
python run_phase2.py
```

The chart is written to `output/btc_price_vs_log_trend.png`. Daily raw data is
cached at `data/cache/btc_usd_daily.csv`; a refresh overlaps the prior seven
days so provider corrections can replace recent cached rows. A cache is used
only after strict validation and only if it is no more than three days stale.
The historical entry-only event table is written to `output/signal_events.csv`.

## Run the dashboard

```powershell
.\start_dashboard.bat
```

Double-clicking `start_dashboard.bat` in File Explorer provides the same
project-local launch path. It verifies that `.venv` exists and starts
Streamlit with that environment. To run it manually from an activated virtual
environment instead, use `python -m streamlit run app.py`.

The dashboard presents current BTC price, log trend, z-score, and BUY/SELL/HOLD
state; editable BUY/SELL thresholds and dollar amounts; current threshold
prices and distances; the marked log-trend chart; a no-look-ahead backtest;
transaction history; and portfolio/buy-and-hold summaries. Changing any of the
four strategy settings recalculates the relevant signals and backtest results.

## Run a ledger replay

The command defaults are synthetic examples: `$1,000.00` cash and `0 BTC`.
Supply balances that were actually available at the beginning of a historical
replay instead when appropriate.

```powershell
python run_phase3.py

# Optional override for a specific replay starting state
python run_phase3.py --starting-cash <dollars> --starting-btc <btc>
```

This produces `output/portfolio_ledger.csv` for executed transactions and
`output/skipped_events.csv` for unaffordable exact-dollar events. BUYs and
SELLs are never partially filled, and the engine never permits negative cash or
BTC. No exchange is contacted and no live order is placed.

## Run the historical backtest

The default backtest starts on `2017-01-01` with `$1,000.00` cash and `0 BTC`.
It uses a 730-observation warm-up period. All settings can be overridden from
the command line.

```powershell
python run_phase4.py

# Example override
python run_phase4.py --starting-date 2018-01-01 --starting-cash 2000 --starting-btc 0
```

The run writes the transaction ledger, skipped-event audit, signal and
execution-event tables, daily portfolio values, JSON summary, and a
strategy-versus-buy-and-hold chart to `output/`.

## Run tests

```powershell
python -m pytest
```

## Methodology

For each daily close, the model fits:

```text
ln(close_t) = intercept + slope × days_since_start + residual_t
```

`days_since_start` is the exact number of 24-hour days since the first usable
BTC observation. The regression uses ordinary least squares through
`numpy.polyfit`. Trend price is `exp(predicted_log_price)`. Residual sigma is
the population standard deviation (`ddof=0`) of all residuals in the fitted
dataset, and `z_score = residual / sigma`.

A sigma-band price is calculated in log space and then converted back:

```text
band_price(k) = exp(predicted_log_price + k × residual_sigma)
```

The bands are therefore multiplicative in dollar terms, rather than a fixed
dollar distance from the trend.

## Signals

The default thresholds are BUY at −1.50 sigma and SELL at +2.00 sigma. The
configuration requires the BUY threshold to be strictly lower than the SELL
threshold, preventing overlapping zones.

```text
z_score <= buy_threshold   -> BUY
z_score >= sell_threshold  -> SELL
otherwise                  -> HOLD
```

An event is created only when the daily state enters a BUY or SELL zone from a
different state. Remaining in the same zone creates no further event. The first
available historical row is never treated as an event because it has no prior
day from which to establish a crossing.

## Historical backtest methodology

For every backtest date, the log-price regression and residual sigma are fit
using only prior daily closes. The current close is then compared with that
prior-data trend to calculate its z-score. A signal known at that day’s close is
executed at the following available day’s opening price, never at the same
close. This avoids fitting a signal with future data or filling it at a price
that was only known after the signal was calculated.

The buy-and-hold benchmark converts the same initial total capital to BTC on
the first actionable date and values that quantity daily. The report includes
total return and maximum drawdown for both approaches.

The dashboard deliberately distinguishes its current valuation panel from the
historical backtest: current valuation uses the complete available history,
while historical signals use only prior closes and execute at the next daily
open.

## Portfolio accounting

For an executed BUY, the engine spends the exact configured dollar amount and
adds `buy_amount / BTC_price` to holdings. For an executed SELL, it receives the
exact configured dollar amount and removes `sell_amount / BTC_price` from
holdings. A transaction is skipped, with an audit record, when the exact amount
cannot be funded by cash or existing BTC.

The portfolio summary reports cash, BTC quantity, BTC market value, total
portfolio value, dollars purchased and sold, transaction counts, and
BTC-weighted average BUY and SELL prices.

## Limitations

- Yahoo Finance is an external source and can be unavailable, delayed, or corrected.
- The full-history fit used by the Phase 1/2 visualisation is descriptive. The
  Phase 4 backtest instead uses an expanding calculation based only on prior
  closes.
- The Phase 3 ledger replay is accounting verification, not a historical
  backtest. It has no benchmark, performance metrics, or look-ahead-bias
  mitigation; those belong to Phase 4.
- Backtests assume daily opening-price fills with no fees, spread, slippage,
  taxes, liquidity constraints, or exchange outages.
- The log trend is a mathematical model, not a law; Bitcoin can remain far
  above or below it for extended periods.
- Historical performance does not guarantee future results. This tool simplifies
  a decision process; it does not predict prices.

## Security and privacy

Do not commit wallet addresses, exchange credentials, API keys, seed phrases,
or personal portfolio balances. Local environment files, cached market data,
and generated reports are excluded by `.gitignore`. Dependency vulnerabilities
are checked automatically in GitHub Actions and should be resolved before a
release or deployment.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
