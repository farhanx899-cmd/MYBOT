# Forex Guardian AI (starter)

An open-source, **signals-only** Forex research dashboard. It does not connect to a broker or place, modify, or close trades.

## Features
- Streamlit dashboard for desktop/laptop.
- OHLC data through `yfinance` for supported pairs.
- EMA 50/200, RSI 14, ATR 14.
- Simple swing-high/low and three-candle FVG heuristics.
- Historical illustrative trade simulation with stop/target, daily loss limit, and cooldown.
- Optional manual news-calendar CSV gate that fails closed if data is missing/stale/invalid.

## Important limitations
- This is a prototype, not a validated profitable strategy or financial advice.
- No automatic news scraping/feed is connected. Use only news/calendar data you are authorised to access.
- Spot Forex has no single consolidated volume delta/order book. Delta/CVD/heatmaps require a separate suitable data source; this starter does not fabricate them.
- ICT/SMC concepts are implemented only as simple heuristics, not a complete or authoritative ICT interpretation.
- Yahoo Finance data may be delayed, incomplete, revised, or unavailable. Do not treat it as broker execution data.
- Simulation assumptions are simplified. Spread/slippage values are examples, not live quotes. This backtest is not yet a robust research-grade event-driven simulator.
- The daily-loss and cooldown controls in the backtest are illustrative. The current signal panel is not a persistent, 24/7 risk controller.
- No live or demo order execution is implemented. Do not add broker credentials to this project.

## Run on Windows
1. Install Python 3.11 or newer from https://www.python.org/downloads/ (tick **Add Python to PATH**).
2. Extract this ZIP to a folder.
3. Open PowerShell in that folder.
4. Run:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

If PowerShell blocks activation, run the environment's Python directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Streamlit will print a local URL, usually http://localhost:8501. Open it in your browser.

## Run on macOS/Linux
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py
```

## News CSV
Copy `news_events_template.csv` to `news_events.csv` and populate it only with events from a source whose terms permit your use. Required columns:
- `time_utc`: ISO-8601 timestamp including UTC timezone, e.g. `2026-10-13T12:30:00Z`
- `currency`: currency code, e.g. USD or GBP
- `impact`: HIGH, MEDIUM, or LOW
- `title`: event title
- `updated_utc`: timestamp when you refreshed the calendar, with timezone

The filter blocks around matching high-impact events and blocks when the calendar is missing or stale. A manually maintained calendar is not a substitute for an automated, verified feed.

## Open-source repository
This package is licensed under MIT. To publish it:
1. Create a new repository on GitHub.
2. Upload these files (do not upload API keys, secrets, or account information).
3. Commit `README.md`, `LICENSE`, `requirements.txt`, `app.py`, `engine.py`, and the CSV template.
4. Add issues/tests before accepting contributions.

## Roadmap before considering any broker integration
1. Automated tests for indicators, stale data, stop/target ordering, daily loss limits, and cooldown persistence.
2. Proper event-driven backtest with bid/ask prices, spread, slippage, and conservative same-candle handling.
3. Walk-forward and out-of-sample evaluation.
4. Reliable licensed news/calendar data.
5. Separate broker adapter and demo-only integration, independently disabled by default.
6. Persistent risk state, heartbeat monitoring, alerting, and a hard manual kill switch.

Do not switch to live execution without independent review and extensive demo testing. Even stop-loss orders cannot guarantee a fixed loss during gaps or slippage.
