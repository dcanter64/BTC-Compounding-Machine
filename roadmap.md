# BTC Compounding Machine — Development Roadmap

## Project Goal

Build a simple, transparent Bitcoin compounding system inspired by Raoul Pal's description of the GMI Compounding Machine.

The core philosophy is:

> Buy weakness. Sell strength. Sell less than you buy. Hold the rest.

The purpose of the application is to reduce investment decisions to a very small number of rules.

The user chooses:

- How oversold Bitcoin must become before buying.
- How overbought Bitcoin must become before selling.
- How much money to deploy on each BUY signal.
- How much Bitcoin value to sell on each SELL signal.

The system then calculates Bitcoin's position relative to a long-term logarithmic trend and produces one of three states:

    BUY
    SELL
    HOLD

The goal is not frequent trading.

Most of the time, the system should say:

    HOLD

This project is inspired by the general framework described publicly by Raoul Pal. It is not intended to reproduce or reverse-engineer any proprietary GMI methodology.

Our implementation must remain transparent so every calculation can be inspected and understood.

---

## Implementation Status

Last reviewed: 2026-09-22

- **Phase 1 - Complete.** Daily BTC-USD retrieval, strict validation, local caching, log-price regression, residual sigma/z-scores, price-space sigma bands, and the baseline chart are implemented and tested.
- **Phase 2 - Complete.** Configurable BUY/SELL/HOLD states, entry-only threshold-crossing events, the signal-event CSV, and chart markers are implemented and tested.
- **Phase 3 - Complete.** A spot-only, exact-dollar ledger engine, skipped-event audit, and portfolio summary are implemented and tested. It is not a historical backtest.
- **Phase 4 - Complete.** The backtest uses prior-close-only expanding regressions, next-day-open execution, the existing Phase 2 signals and Phase 3 ledger, equivalent-capital buy-and-hold, daily valuation, total return, maximum drawdown, CSV/JSON reports, and a comparison chart.
- **Phase 5 - Complete.** The Streamlit dashboard shows current valuation and signal state, editable strategy settings, threshold prices/distances, marked trend and backtest charts, transaction history, and portfolio/benchmark summaries. It was launched and smoke-tested locally.

Phase 3 uses synthetic example defaults of $1,000.00 cash and 0 BTC. They must not be treated as historical starting balances; users should supply balances that were actually available at the start of their replay period without committing private portfolio information.

---

# Core Philosophy

The application should embody a very simple idea:

    Bitcoin becomes unusually cheap relative to long-term trend -> BUY

    Bitcoin becomes unusually expensive relative to long-term trend -> SELL

    Otherwise -> HOLD

The user determines what "cheap" and "expensive" mean by selecting standard-deviation thresholds.

Initial example:

    BUY at -1.5σ

    SELL at +2.0σ

The user also selects transaction amounts.

Example:

    BUY $1,000

    SELL $500

Because the SELL amount is smaller than the BUY amount, the strategy is designed to gradually accumulate Bitcoin while occasionally harvesting gains during periods of extreme strength.

The application should make this process mechanical rather than emotional.

---

# Development Rule

Do not build the entire application at once.

Work through this roadmap one phase at a time.

For every phase:

1. Implement only that phase.
2. Run the relevant tests.
3. Verify the calculations.
4. Update documentation if necessary.
5. Summarize what was completed.
6. Stop.
7. Wait for explicit instructions before beginning the next phase.

Do not automatically continue into another phase.

---

# Proposed Project Structure

    btc_compounding_machine/
    │
    ├── README.md
    ├── roadmap.md
    ├── requirements.txt
    ├── config.py
    │
    ├── data/
    │   └── cache/
    │
    ├── src/
    │   ├── data_loader.py
    │   ├── trend_model.py
    │   ├── signals.py
    │   ├── portfolio.py
    │   ├── backtest.py
    │   ├── dashboard.py
    │   └── charts.py
    │
    ├── app.py
    ├── start_dashboard.bat
    │
    ├── tests/
    │   ├── test_trend_model.py
    │   ├── test_signals.py
    │   ├── test_portfolio.py
    │   ├── test_backtest.py
    │   └── test_dashboard.py
    │
    └── output/

Keep the project simple and modular.

Do not introduce unnecessary frameworks or abstractions.

### Current implementation through Phase 5

    README.md
    roadmap.md
    requirements.txt
    pytest.ini
    config.py
    run_phase1.py
    run_phase2.py
    run_phase3.py
    run_phase4.py
    app.py
    start_dashboard.bat
    data/cache/                     # ignored local BTC data cache
    output/                         # ignored charts and CSV reports
    src/data_loader.py
    src/trend_model.py
    src/signals.py
    src/portfolio.py
    src/backtest.py
    src/dashboard.py
    src/charts.py
    tests/test_data_loader.py
    tests/test_trend_model.py
    tests/test_signals.py
    tests/test_portfolio.py
    tests/test_backtest.py
    tests/test_dashboard.py
    tests/test_charts.py

---

# Initial Default Settings

Use the following values as starting defaults:

    Asset: Bitcoin
    Ticker: BTC-USD
    Frequency: Daily

    BUY threshold: -1.5σ
    SELL threshold: +2.0σ

    BUY amount: $1,000
    SELL amount: $500

These values are defaults only.

The user must eventually be able to change:

    BUY threshold
    SELL threshold
    BUY amount
    SELL amount

The system should immediately recalculate when these values change.

---

# Mathematical Foundation

The initial model should use a long-term logarithmic Bitcoin price trend.

Conceptually:

    ln(price_t) = a + b*t + error_t

Where:

    price_t = Bitcoin price at time t
    a = regression intercept
    b = long-term trend coefficient
    t = time
    error_t = distance from trend in log space

For every date calculate:

    actual_log_price
    predicted_log_price
    trend_price
    residual
    residual_standard_deviation
    z_score

The residual is:

    residual = actual_log_price - predicted_log_price

The z-score is:

    z_score = residual / residual_standard_deviation

The z-score expresses how far Bitcoin is from its modeled long-term trend.

Example interpretation:

    -2.0σ = Bitcoin is far below trend
    -1.5σ = potential accumulation level
     0.0σ = approximately at trend
    +1.0σ = above trend
    +2.0σ = potential trimming level

The initial decision rule is:

    if z_score <= buy_threshold:
        BUY

    elif z_score >= sell_threshold:
        SELL

    else:
        HOLD

All calculations must remain visible and understandable.

Do not hide the trend calculation inside an opaque model.

---

# PHASE 1 — Bitcoin Data and Log Trend

## Objective

Build the mathematical foundation of the Compounding Machine.

Do not implement trading or portfolio logic yet.

## Historical Bitcoin Data

Retrieve daily Bitcoin price history from a reliable source.

Preferred fields:

    date
    open
    high
    low
    close
    volume

Cache historical data locally where appropriate.

Check for:

    missing values
    duplicate dates
    zero prices
    negative prices
    malformed dates
    stale data

The program should fail clearly if usable Bitcoin data cannot be obtained.

Do not silently substitute corrupted data.

---

## Time Variable

Create a numerical time variable for the regression.

For example:

    days_since_start

Document exactly how it is calculated.

---

## Log Price

Calculate:

    log_price = ln(close)

---

## Log Trend Regression

Fit the baseline model:

    log_price ~ time

Calculate:

    intercept
    slope
    predicted_log_price
    trend_price
    residual

Convert the predicted log price back into dollar terms correctly.

---

## Standard Deviation

Calculate the standard deviation of the residuals.

Then calculate:

    z_score = residual / sigma

---

## Price Bands

Calculate the corresponding Bitcoin price for:

    +2σ
    +1σ
     0σ trend
    -1σ
    -1.5σ
    -2σ

The calculations must respect the fact that the regression is performed in logarithmic space.

Do not simply add dollar amounts to the trend line.

---

## Baseline Chart

Produce a chart titled:

    BTC Price vs Log Trend

Display:

    BTC price
    Log trend
    +1σ band
    -1σ band
    +2σ band
    -2σ band

The Bitcoin price axis should use a logarithmic scale if appropriate.

The chart should capture the basic visual idea of Raoul Pal's example without copying proprietary branding.

---

## Phase 1 Tests

Verify:

- BTC data loads correctly.
- Log-price calculations are correct.
- Trend values are positive.
- Residual calculations are correct.
- Positive residuals create positive z-scores.
- Negative residuals create negative z-scores.
- Sigma bands convert correctly from log space to price space.
- The chart renders without errors.

---

## Phase 1 Completion

When Phase 1 is complete:

1. Run all Phase 1 tests.
2. Show the resulting BTC log-trend chart.
3. Report the current BTC z-score.
4. Explain the exact regression methodology used.
5. Report any assumptions or limitations.
6. Stop.

Do not begin Phase 2 automatically.

---

# PHASE 2 — BUY, SELL, and HOLD Signals

## Objective

Turn the log-trend model into a very simple decision engine.

The user should be able to specify:

    BUY threshold
    SELL threshold

Default:

    BUY = -1.5σ
    SELL = +2.0σ

---

## Signal Logic

The current state should be calculated as:

    z_score <= BUY threshold
        -> BUY

    z_score >= SELL threshold
        -> SELL

    otherwise
        -> HOLD

The application should prominently display the current state.

Examples:

    CURRENT SIGNAL: BUY

    CURRENT SIGNAL: SELL

    CURRENT SIGNAL: HOLD

---

## Threshold Crossing Events

Do not treat every day inside a BUY or SELL zone as a new transaction.

A BUY event occurs when Bitcoin crosses from outside the BUY zone into the BUY zone.

Example:

    yesterday = -1.42σ
    today = -1.53σ

    BUY EVENT

If Bitcoin remains at:

    -1.60σ
    -1.72σ
    -1.68σ

those should not automatically become additional BUY events.

Bitcoin must first leave the BUY zone and subsequently enter it again before generating another threshold-crossing BUY event.

Apply equivalent logic to SELL events.

---

## Signal History

Create a signal-event table containing:

    date
    BTC price
    trend price
    z-score
    signal
    threshold crossed

---

## Chart Markers

Add signal events to the BTC Price vs Log Trend chart.

Use:

    Green marker = BUY

    Red marker = SELL

The resulting chart should make it easy to visually inspect whether BUY events occurred during weakness and SELL events occurred during strength.

---

## Phase 2 Tests

Verify:

- BUY threshold crossings are recognized.
- SELL threshold crossings are recognized.
- HOLD is returned between thresholds.
- Repeated signals are not created simply because BTC remains inside a zone.
- Leaving and re-entering a zone creates a new event.
- Markers appear on the correct dates and prices.

---

## Phase 2 Completion

When Phase 2 is complete:

1. Run the tests.
2. Display the historical chart with BUY and SELL markers.
3. Show the current z-score.
4. Show the current signal.
5. Show the configured BUY and SELL thresholds.
6. Stop.

Do not begin Phase 3 automatically.

---

# PHASE 3 — Compounding Engine

## Objective

Implement the central idea:

    Buy weakness.
    Sell strength.
    Sell less than you buy.

The user must be able to specify exact transaction amounts.

Default:

    BUY amount = $1,000

    SELL amount = $500

The BUY and SELL amounts should not be forced to match.

The strategy intentionally permits:

    BUY amount > SELL amount

This allows the portfolio to accumulate Bitcoin over time while occasionally taking some money off the table during periods of unusually strong valuation.

---

# Portfolio State

Track:

    cash
    BTC quantity
    BTC market value
    total portfolio value
    total amount purchased
    total amount sold

Also track:

    number of BUY transactions
    number of SELL transactions
    average BUY price
    average SELL price

Keep the accounting understandable.

Do not introduce unnecessary portfolio complexity.

---

# Transaction Ledger

Each executed transaction should record:

    date
    BTC price
    trend price
    z-score
    BUY or SELL
    dollar amount
    BTC quantity
    cash after transaction
    BTC holdings after transaction
    total portfolio value

Example:

    Date: 2027-03-12
    Signal: BUY
    BTC Price: $61,400
    Z-Score: -1.53σ
    Amount: $1,000
    BTC Purchased: 0.0162866

Example SELL:

    Date: 2028-08-06
    Signal: SELL
    BTC Price: $182,600
    Z-Score: +2.04σ
    Amount: $500
    BTC Sold: 0.0027382

---

# Capital Rules

The simulation must never:

- spend more cash than is available
- sell more BTC than is owned
- produce negative BTC holdings
- produce negative cash unless a future version explicitly introduces borrowing

No margin.

No leverage.

No derivatives.

This is a spot-Bitcoin accumulation and trimming model.

---

# Phase 3 Tests

Verify:

- BUY transactions use the correct dollar amount.
- SELL transactions use the correct dollar amount.
- BTC quantity calculations are accurate.
- Cash accounting is accurate.
- BTC accounting is accurate.
- The system cannot sell BTC it does not own.
- The system cannot spend unavailable cash.
- Portfolio value is accurate after every transaction.

---

# Phase 3 Completion

When Phase 3 is complete:

1. Run all tests.
2. Display the transaction ledger.
3. Show total BTC accumulated.
4. Show total dollars used for BUY transactions.
5. Show total dollars received from SELL transactions.
6. Show current portfolio value.
7. Stop.

Do not begin Phase 4 automatically.

---

# PHASE 4 — Historical Backtest

## Objective

Determine how the Compounding Machine would have behaved historically.

The purpose is not to discover a perfect historical strategy.

The purpose is to understand:

    how frequently signals occur
    when they occur
    how much BTC accumulates
    how much BTC is trimmed
    how portfolio value changes

---

# Backtest Inputs

Allow configuration of:

    starting date
    starting cash
    starting BTC
    BUY threshold
    SELL threshold
    BUY amount
    SELL amount

Use exactly the same signal logic implemented in Phase 2.

Do not create separate backtest-only rules.

---

# Buy-and-Hold Benchmark

Include a simple Bitcoin buy-and-hold comparison.

The benchmark exists to provide context.

Compare:

    Compounding Machine
    Bitcoin Buy and Hold

Use equivalent starting capital assumptions whenever possible.

---

# Backtest Results

Report:

    ending portfolio value
    ending BTC holdings
    ending cash
    total BUY transactions
    total SELL transactions
    dollars spent buying
    dollars received selling
    average BUY price
    average SELL price
    maximum drawdown
    total return

Also show a chart comparing portfolio value over time.

Do not automatically optimize the thresholds based on historical performance.

The user should choose the thresholds.

---

# Avoid Look-Ahead Bias

Historical calculations must not use information that would have been unavailable at the time a signal occurred.

This requirement is critical.

If the trend calculation used for a historical date depends on future price observations, clearly identify that issue before treating the backtest as realistic.

The backtest must distinguish between:

    retrospective visualization

and:

    historically actionable signals

If necessary, use an expanding calculation so each historical signal uses only information available up to that date.

Correctness is more important than producing attractive historical results.

---

# Phase 4 Completion

When Phase 4 is complete:

1. Run all tests.
2. Display the historical transactions.
3. Display portfolio performance.
4. Display the buy-and-hold benchmark.
5. Report any look-ahead limitations.
6. Stop.

Do not begin Phase 5 automatically.

---

# PHASE 5 — Streamlit Compounding Machine Dashboard

## Objective

Create the actual user-facing application.

The interface should remain simple.

This is not intended to become a large market-analysis dashboard.

Its purpose is to answer:

    Is Bitcoin cheap enough to buy?

    Is Bitcoin expensive enough to sell?

    Or should I simply hold?

---

# Main Display

At the top of the dashboard prominently show:

    BTC PRICE

    LOG TREND

    CURRENT Z-SCORE

    CURRENT SIGNAL

Example:

    BTC PRICE
    $78,450

    LOG TREND
    $94,200

    CURRENT DEVIATION
    -0.83σ

    SIGNAL
    HOLD

The signal should be extremely easy to see.

---

# User Controls

Allow the user to change:

    BUY threshold
    SELL threshold
    BUY amount
    SELL amount

Example:

    BUY threshold: -1.50σ

    SELL threshold: +2.00σ

    BUY amount: $1,000

    SELL amount: $500

Changing these inputs should immediately update the relevant calculations and historical signals.

---

# Threshold Prices

Show the approximate Bitcoin prices corresponding to the selected thresholds for the current date.

Example:

    BUY LEVEL

    -1.50σ

    BTC price approximately:
    $XX,XXX

And:

    SELL LEVEL

    +2.00σ

    BTC price approximately:
    $XXX,XXX

This allows the user to understand not only the z-score but the approximate dollar price associated with the next signal level.

---

# Primary Chart

Display:

    BTC price
    Log trend
    +1σ
    -1σ
    +2σ
    -2σ
    BUY markers
    SELL markers

Also display the user's selected BUY and SELL thresholds when they differ from the standard bands.

The chart should remain visually clean.

Do not add unrelated indicators.

---

# Current Position Panel

Display:

    Current BTC price
    Current trend price
    Current z-score
    Current signal

Also display:

    Distance to BUY threshold

    Distance to SELL threshold

For example:

    Current deviation: -0.83σ

    BUY threshold: -1.50σ

    Distance to BUY: 0.67σ

This should help the user understand how close Bitcoin is to a decision point.

---

# Compounding Settings Panel

Display:

    BUY amount
    SELL amount
    BUY threshold
    SELL threshold

Make the asymmetry obvious.

Example:

    Buy weakness:
    $1,000 at -1.50σ

    Sell strength:
    $500 at +2.00σ

---

# Transaction History

Show an interactive table containing:

    date
    action
    BTC price
    z-score
    dollar amount
    BTC quantity

Keep this table simple.

---

# Portfolio Summary

Display:

    BTC holdings
    Cash
    BTC market value
    Total portfolio value
    Total dollars purchased
    Total dollars sold
    Number of BUY events
    Number of SELL events

---

# Phase 5 Completion

Phase 5 is complete when:

- The Streamlit application launches reliably.
- Current BTC data loads.
- Current trend is displayed.
- Current z-score is displayed.
- BUY/SELL/HOLD is displayed.
- BUY and SELL thresholds are editable.
- BUY and SELL amounts are editable.
- Threshold prices are shown.
- Historical signals are plotted.
- Portfolio results are shown.
- Transaction history is accessible.
- Backtest results are accessible.
- All tests pass.

At completion:

1. Run the full test suite.
2. Launch the application.
3. Verify the current calculations.
4. Summarize the finished system.
5. Stop.

---

# Final Application Philosophy

The finished application should remain intentionally boring.

It should not encourage trading.

It should not produce constant signals.

It should not contain dozens of indicators.

It should not attempt to predict Bitcoin's next move.

It should answer a much simpler question:

    Relative to Bitcoin's long-term trend,
    is Bitcoin unusually cheap,
    unusually expensive,
    or somewhere in between?

The user's rules determine what happens next.

The essential workflow is:

    WEAKNESS
        |
        v
    BUY

    NORMAL RANGE
        |
        v
    HOLD

    STRENGTH
        |
        v
    SELL

And the long-term compounding principle is:

    BUY MORE THAN YOU SELL

The intended behavior is therefore:

    buy weakness
        ->
    hold through the middle
        ->
    sell some strength
        ->
    retain the core BTC position
        ->
    wait

The application should reduce decisions rather than create them.

---

# Coding Principles

Prefer:

    simple functions
    transparent calculations
    clear variable names
    modular files
    documented assumptions
    reproducible results

Avoid:

    unnecessary indicators
    complex optimization
    machine-learning predictions
    price forecasting
    giant functions
    hidden calculations
    unnecessary dependencies
    excessive configuration

The software should be understandable enough that the user can inspect exactly why it produced BUY, SELL, or HOLD.

---

# README Requirements

Maintain README.md throughout development.

The final README should explain:

    What the BTC Compounding Machine does

    How the logarithmic trend works

    What standard deviations represent

    How BUY signals are generated

    How SELL signals are generated

    Why SELL amounts can be smaller than BUY amounts

    How the compounding process works

    How to run the Streamlit application

    How to run the tests

    Important limitations

Clearly state:

    Historical performance does not guarantee future results.

    The log trend is a mathematical model, not a law.

    Bitcoin can remain above or below modeled trend for extended periods.

    The model is intended to simplify a decision process, not predict future prices.

---

# HISTORICAL INITIAL CODEX INSTRUCTION (COMPLETED)

This initial instruction has been completed. Phases 1 through 5 are complete.

Begin with PHASE 1 only.

Do not implement trading.

Do not implement portfolio accounting.

Do not implement the Streamlit dashboard.

Do not begin later phases.

For Phase 1, complete only:

    Bitcoin historical data retrieval

    data validation

    local data caching

    time variable

    log-price calculation

    baseline logarithmic regression

    trend price calculation

    residual calculation

    residual standard deviation

    z-score calculation

    sigma price bands

    BTC Price vs Log Trend chart

    Phase 1 tests

After completing Phase 1:

1. Run the tests.
2. Display the resulting chart.
3. Report the latest BTC price.
4. Report the latest trend price.
5. Report the latest z-score.
6. Explain exactly how the trend and sigma calculations work.
7. Identify any limitations in the implementation.
8. Stop.

Wait for the user to explicitly request Phase 2.
