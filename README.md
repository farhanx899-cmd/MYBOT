# Forex Guardian AI

A signals-only Forex research dashboard with a TradingView chart, active-session refresh, transparent rule-based analysis, and illustrative stop-loss and take-profit levels. It does not connect to a broker or place, modify, or close trades.

## Dashboard features

- Five supported pairs: GBP/USD, EUR/USD, USD/JPY, AUD/USD, and USD/CAD.
- One-hour and daily analysis timeframes with selectable price history.
- TradingView Advanced Chart widget with matching pair and timeframe selectors.
- Rule-based BUY, SELL, or NO TRADE decision, with EMA trend, RSI, ATR, and supporting evidence.
- Adjustable ATR stop distance, TP1 at 1R, and TP2 at the selected reward/risk multiple.
- Historical illustrative simulation with estimated costs, daily loss limit, and cooldown controls.
- Manual high-impact-news calendar gate that blocks signals when the calendar is missing, stale, invalid, or inside the event window.
- Manual refresh plus automatic refresh every 60 seconds, 2 minutes, or 5 minutes while the dashboard session is open.

## Run on Windows

Install Python 3.11 or newer, then open PowerShell in the repository folder and run:

~~~powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
~~~

If PowerShell blocks environment activation, run the environment's Python directly:

~~~powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
~~~

## Run on macOS or Linux

~~~bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
~~~

Streamlit prints the local address to open in your browser (usually http://localhost:8501).

## Refresh, data, and availability

Auto-refresh reruns the dashboard for an active browser session while the app server is running. It does not keep a stopped computer, server, browser, or hosting service online. Continuous availability needs an independently operated host, monitoring, and access controls. Do not publish the dashboard publicly without authentication. This change does not deploy or configure hosting.

Technical analysis candles are fetched from Yahoo Finance and cached briefly. The TradingView widget uses its own market data, coverage, and timing, so chart values can differ from the signal calculations. Yahoo Finance data can be delayed, incomplete, revised, or unavailable and is not broker execution data.

## News calendar CSV

Copy news_events_template.csv to news_events.csv in the project folder. Populate it only with event data from a source whose terms permit your use, and update it regularly. Required columns:

- time_utc: ISO-8601 event timestamp with a UTC timezone, such as 2026-10-13T12:30:00Z.
- currency: currency code such as USD or GBP.
- impact: HIGH, MEDIUM, or LOW.
- title: event title.
- updated_utc: timezone-aware timestamp for the calendar's last refresh.

The gate blocks around matching high-impact events and blocks if the calendar is missing or stale. No automatic news scraping or feed is connected; a manually maintained calendar is not a verified feed.

## Signal and simulation limitations

Signals use EMA 50/200 trend, RSI 14, ATR 14, and a moving-average crossover condition. Swing levels and three-candle fair-value-gap labels are simple heuristics, not a complete or authoritative ICT/SMC interpretation. A BUY or SELL label is not a prediction or recommendation. Stop and target values are reference levels based on recent volatility and selected settings; they are not broker orders.

This is a prototype for research and education, not financial advice or a validated profitable strategy. The historical simulation is simplified and not a research-grade event-driven backtest. Estimated spreads, slippage, fills, and available market data may not match real trading. Daily-loss and cooldown controls only apply inside the illustrative simulation; they are not a persistent, 24/7 risk controller. Spot Forex has no single consolidated volume delta, order book, or global liquidity heatmap, and this app does not fabricate CVD, heatmap, or order-flow data.

No live or demo execution is implemented. Never commit API keys, broker credentials, or access tokens. Do not add live execution without independent review, extensive demo testing, persistent risk controls, and a hard manual kill switch. Stop-loss orders cannot guarantee a fixed loss during gaps or slippage.

## Open-source and development notes

The repository is licensed under MIT. Do not include API keys, secrets, or account information in published files. Before expanding the trading scope, prioritize automated checks for indicators, stale data, stop/target ordering, and risk limits; a conservative event-driven backtest; out-of-sample evaluation; and a licensed, reliable news source. Any future broker adapter should be isolated and disabled by default, with persistent risk state, monitoring, alerts, and a manual kill switch.


## Private Streamlit deployment

The dashboard fails closed until Google OpenID Connect (OIDC) sign-in and an email allowlist are configured. It requires a verified Google email that exactly matches an address on the allowlist. The example at [.streamlit/secrets.toml.example](.streamlit/secrets.toml.example) contains placeholders only. Never commit the real .streamlit/secrets.toml file or paste credentials into GitHub.

1. Create a Google OAuth web client. Set its authorized redirect URI to the exact Streamlit app URL followed by /oauth2callback. Generate a long random cookie secret.
2. In Streamlit Community Cloud, create an app from repository farhanx899-cmd/MYBOT, branch codex/live-refresh-tradingview-dashboard-20261012, and entrypoint app.py. Pick the app URL before setting the OAuth redirect URI.
3. In the deploy dialog's Advanced settings, enter the completed example as Streamlit secrets. Replace every placeholder and keep only your own verified Google email in [app_access].allowed_emails. The app shows no dashboard until all settings are valid.
4. After the app is created, open its Share settings and choose “Only specific people can view this app” before sharing its URL. The in-app Google login and email allowlist remain enabled as additional access controls.
5. Community Cloud watches the selected GitHub branch and applies later commits automatically. The feature-branch app is a preview while PR #2 remains open; merging the PR is a separate GitHub action.

Community Cloud puts apps to sleep after 12 hours without traffic. A visit wakes an app, but this service does not promise continuous 24/7 uptime. The dashboard's 60-second to 5-minute refresh runs only while a browser session and app server are active. See [Community Cloud app hibernation](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app) and [private app sharing](https://docs.streamlit.io/deploy/streamlit-community-cloud/share-your-app).
