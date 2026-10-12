# Forex Guardian AI

A signals-only Forex research dashboard with an interactive TradingView chart, automatic refresh for open sessions, rule-based analysis, and illustrative stop-loss and take-profit levels. It does not connect to a broker or place, modify, or close trades.

## What the dashboard includes

- Five supported pairs: GBP/USD, EUR/USD, USD/JPY, AUD/USD, and USD/CAD.
- One-hour and daily analysis views with selectable history.
- TradingView Advanced Chart widget, with pair and timeframe controls.
- Rule-based BUY, SELL, or NO TRADE decisions with EMA trend, RSI, ATR, and evidence.
- Adjustable ATR stop distance, TP1 at 1R, and TP2 at the selected reward/risk multiple.
- Illustrative historical simulation with estimated trading costs, daily loss limits, and a cooldown after losses.
- A manual high-impact-news gate that blocks signals when its calendar is unavailable, stale, invalid, or inside the event window.
- Manual refresh and automatic refresh at a selectable interval while the dashboard session is open.

## Run locally

Use Python 3.10 or newer. From the repository directory, install the dependencies and start the dashboard:

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open the local address printed by Streamlit. On Windows, these same commands work in PowerShell when Python and pip are on PATH.

## Refresh and availability

Automatic refresh reruns the dashboard for an active browser session. It does not keep a stopped computer, server, browser, or hosting service running. Continuous availability requires an independently operated host with monitoring and access controls. Do not publish this dashboard publicly without authentication. No hosting credentials, deployment, or public service are included in this repository change.

Price data for analysis is fetched through Yahoo Finance and cached briefly. The TradingView chart is an embedded third-party widget with its own market-data coverage and timing, so its candles or quotes may differ from the signal calculations.

## News calendar

Place the manually maintained news calendar at `news_events.csv` in the project directory, using the columns and timestamp format expected by the app. Keep the calendar current. If the file is missing or cannot be validated, the dashboard blocks a trade signal instead of assuming there is no event risk. This is not an automatic news feed.

## How to interpret signals

The rules use EMA 50/200 trend, RSI, ATR, and a moving-average crossover condition. Swing levels and fair-value-gap labels are descriptive heuristics, not standalone confirmations. A displayed stop or target is an estimate based on recent volatility and user-selected settings; it is not an order submitted to a broker. A BUY or SELL label is not a prediction or a recommendation.

The historical simulation is illustrative and simplified. It does not establish future performance, and its estimated costs, fills, slippage, and available market data may not match a live account. Spot Forex has no single consolidated order book or volume delta; the app does not fabricate CVD, heatmap, or order-flow data.

## Safety and scope

This project is a prototype for research and education, not financial advice. It has no broker integration or live-trading capability. Never put API keys, broker credentials, or access tokens in source files or commit them to GitHub.
