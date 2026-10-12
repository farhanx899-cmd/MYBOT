import html
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from engine import build_features, fetch_prices, latest_candidate, news_gate, simulate

PAIRS = {
    "GBP/USD": {"yahoo": "GBPUSD=X", "tradingview": "FX:GBPUSD"},
    "EUR/USD": {"yahoo": "EURUSD=X", "tradingview": "FX:EURUSD"},
    "USD/JPY": {"yahoo": "USDJPY=X", "tradingview": "FX:USDJPY"},
    "AUD/USD": {"yahoo": "AUDUSD=X", "tradingview": "FX:AUDUSD"},
    "USD/CAD": {"yahoo": "USDCAD=X", "tradingview": "FX:USDCAD"},
}
PAIR_BY_YAHOO = {item["yahoo"]: label for label, item in PAIRS.items()}

st.set_page_config(
    page_title="Forex Guardian | Market Intelligence",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    :root {
        color-scheme: dark;
        --fg-bg: #07111f;
        --fg-panel: #0d1a2b;
        --fg-border: rgba(148, 163, 184, .16);
        --fg-muted: #8fa1b8;
        --fg-text: #e8eff8;
        --fg-green: #34d399;
        --fg-red: #fb7185;
    }
    [data-testid="stAppViewContainer"] { background: var(--fg-bg); color: var(--fg-text); }
    [data-testid="stHeader"] { background: rgba(7, 17, 31, .9); }
    [data-testid="stSidebar"] { background: #0a1524; border-right: 1px solid var(--fg-border); }
    .block-container { max-width: 1480px; padding-top: 1.35rem; padding-bottom: 3rem; }
    h1, h2, h3 { color: var(--fg-text); letter-spacing: -.025em; }
    [data-testid="stMetric"] {
        background: linear-gradient(145deg, rgba(16, 33, 56, .95), rgba(13, 26, 43, .92));
        border: 1px solid var(--fg-border); border-radius: 16px; padding: 15px 18px; min-height: 105px;
    }
    [data-testid="stMetricLabel"] { color: var(--fg-muted); }
    [data-testid="stMetricValue"] { color: var(--fg-text); font-size: 1.4rem; }
    .fg-brand { display: flex; align-items: center; gap: 14px; margin: 0 0 8px; }
    .fg-mark {
        display: grid; place-items: center; width: 46px; height: 46px; border-radius: 14px;
        color: #dbeafe; font-size: 22px; background: linear-gradient(145deg, #1d4ed8, #0f766e);
        box-shadow: 0 8px 24px rgba(29, 78, 216, .22);
    }
    .fg-title { font-size: 1.8rem; font-weight: 750; color: var(--fg-text); }
    .fg-subtitle { color: var(--fg-muted); font-size: .94rem; margin-top: 2px; }
    .fg-statusline { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; color: var(--fg-muted); font-size: .82rem; margin: 10px 0 20px; }
    .fg-pill { display: inline-flex; align-items: center; gap: 7px; padding: 5px 10px; border: 1px solid var(--fg-border); border-radius: 999px; background: rgba(16, 33, 56, .8); color: #bfdbfe; font-weight: 650; letter-spacing: .04em; }
    .fg-dot { color: var(--fg-green); font-size: 1rem; }
    .fg-card { background: linear-gradient(145deg, rgba(16, 33, 56, .92), rgba(13, 26, 43, .92)); border: 1px solid var(--fg-border); border-radius: 18px; padding: 20px 22px; margin: 0 0 14px; }
    .fg-card-kicker { color: var(--fg-muted); font-size: .78rem; font-weight: 700; letter-spacing: .11em; text-transform: uppercase; margin-bottom: 8px; }
    .fg-decision { font-size: 1.6rem; font-weight: 800; letter-spacing: -.03em; }
    .fg-buy { color: var(--fg-green); }
    .fg-sell { color: var(--fg-red); }
    .fg-wait { color: #fbbf24; }
    .fg-card-copy { color: #b9c8da; line-height: 1.55; margin-top: 8px; }
    .fg-level { display: flex; justify-content: space-between; gap: 16px; padding: 10px 0; border-bottom: 1px solid var(--fg-border); color: var(--fg-muted); }
    .fg-level:last-child { border-bottom: 0; }
    .fg-level strong { color: var(--fg-text); font-variant-numeric: tabular-nums; }
    .fg-section-note { color: var(--fg-muted); font-size: .85rem; line-height: 1.5; }
    div[data-testid="stVerticalBlockBorderWrapper"] { border-color: var(--fg-border) !important; border-radius: 18px !important; background: rgba(13, 26, 43, .42); }
    div[data-testid="stButton"] > button { border-radius: 10px; border: 1px solid var(--fg-border); font-weight: 650; }
    @media (max-width: 760px) { .block-container { padding: 1rem .8rem 2rem; } .fg-title { font-size: 1.4rem; } .fg-card { padding: 16px; } }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=60, show_spinner=False, max_entries=32)
def load_market_snapshot(pair: str, period: str, interval: str) -> pd.DataFrame:
    prices = fetch_prices(pair, period, interval)
    return build_features(prices)


def format_price(value: float, pair: str) -> str:
    decimals = 3 if "JPY" in pair else 5
    return f"{value:,.{decimals}f}"


def tradingview_chart(pair: str, interval: str) -> None:
    symbol = PAIRS[PAIR_BY_YAHOO[pair]]["tradingview"]
    chart_interval = "60" if interval == "1h" else "D"
    config = {
        "autosize": True,
        "symbol": symbol,
        "interval": chart_interval,
        "timezone": "Etc/UTC",
        "theme": "dark",
        "style": "1",
        "withdateranges": True,
        "hide_side_toolbar": False,
        "allow_symbol_change": False,
        "save_image": False,
        "calendar": False,
        "details": False,
        "hotlist": False,
        "locale": "en",
        "support_host": "https://www.tradingview.com",
    }
    widget_html = f"""
    <!doctype html>
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1"></head>
    <body style="margin:0;background:#0d1a2b">
      <div class="tradingview-widget-container" style="height:570px;width:100%">
        <div class="tradingview-widget-container__widget" style="height:100%;width:100%"></div>
        <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" async>{json.dumps(config)}</script>
      </div>
    </body></html>
    """
    components.html(widget_html, height=580, scrolling=False)


with st.sidebar:
    st.markdown("## 🛡️ Forex Guardian")
    st.caption("Market intelligence · signals only")
    st.divider()
    pair_label = st.selectbox("Market", list(PAIRS), index=0)
    pair = PAIRS[pair_label]["yahoo"]
    interval_label = st.selectbox("Analysis timeframe", ["1 hour", "1 day"], index=0)
    interval = "1h" if interval_label == "1 hour" else "1d"
    if interval == "1h":
        period = st.selectbox("Price history", ["180d", "365d", "730d"], index=1)
    else:
        period = st.selectbox("Price history", ["1y", "2y", "5y"], index=1)

    st.divider()
    st.markdown("### Refresh")
    auto_refresh = st.toggle("Auto-refresh dashboard", value=True)
    refresh_label = st.selectbox("Check interval", ["60 seconds", "2 minutes", "5 minutes"], index=0)
    refresh_seconds = {"60 seconds": 60, "2 minutes": 120, "5 minutes": 300}[refresh_label]
    if st.button("↻ Refresh market data now", use_container_width=True):
        load_market_snapshot.clear()
        st.rerun()

    st.divider()
    st.markdown("### Analysis plan")
    stop_atr = st.number_input("Stop distance (ATR)", min_value=0.5, max_value=5.0, value=1.5, step=0.25)
    reward_risk = st.number_input("Final target (R multiple)", min_value=1.0, max_value=5.0, value=2.0, step=0.25)

    st.divider()
    st.markdown("### Simulation controls")
    daily_limit_r = st.number_input("Daily simulation limit (R)", min_value=0.5, max_value=5.0, value=2.0, step=0.5)
    cooldown_losses = st.number_input("Losses before cooldown", min_value=1, max_value=5, value=2, step=1)
    cooldown_bars = st.number_input("Cooldown bars", min_value=1, max_value=72, value=24, step=1)
    st.caption("Risk levels and limits are for analysis and historical simulation only.")
    st.caption("Auto-refresh runs while this dashboard session is open and the app server is running.")


st.markdown(
    """
    <div class="fg-brand">
      <div class="fg-mark">🛡️</div>
      <div><div class="fg-title">Forex Guardian</div><div class="fg-subtitle">Market intelligence dashboard</div></div>
    </div>
    """,
    unsafe_allow_html=True,
)
status_text = "AUTO-REFRESH ON" if auto_refresh else "AUTO-REFRESH PAUSED"
st.markdown(
    f'<div class="fg-statusline"><span class="fg-pill"><span class="fg-dot">●</span>{status_text}</span>'
    f'<span>Data updates are provider-dependent; this is not an execution terminal.</span></div>',
    unsafe_allow_html=True,
)
st.warning(
    "Research only. Signals, entries, stop-losses, and targets are illustrative analysis, "
    "not financial advice or orders. This app has no broker connection and cannot trade."
)


@st.fragment(run_every=refresh_seconds if auto_refresh else None)
def render_dashboard() -> None:
    checked_at = datetime.now(timezone.utc)
    try:
        with st.spinner("Refreshing market snapshot…"):
            df = load_market_snapshot(pair, period, interval)
        candidate, evidence = latest_candidate(df, pair, stop_atr=stop_atr, reward_risk=reward_risk)
        last = df.iloc[-1]
        last_candle = pd.Timestamp(df.index[-1])
        if last_candle.tzinfo is None:
            last_candle = last_candle.tz_localize("UTC")
        else:
            last_candle = last_candle.tz_convert("UTC")
        age_minutes = max(0, int((checked_at - last_candle.to_pydatetime()).total_seconds() // 60))

        news_path = Path(__file__).resolve().parent / "news_events.csv"
        if news_path.exists():
            try:
                events = pd.read_csv(news_path)
                news_blocked, news_reason = news_gate(pair, events)
            except (OSError, pd.errors.ParserError, UnicodeError):
                news_blocked, news_reason = True, "News calendar could not be read; risk gate is blocked."
        else:
            news_blocked, news_reason = news_gate(pair, pd.DataFrame())

        st.markdown(
            f'<div class="fg-section-note">Market: <strong>{html.escape(pair_label)}</strong>'
            f' &nbsp;·&nbsp; Checked {checked_at.strftime("%H:%M:%S UTC")}'
            f' &nbsp;·&nbsp; Last completed candle {last_candle.strftime("%d %b %Y, %H:%M UTC")}</div>',
            unsafe_allow_html=True,
        )
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Latest close · Yahoo Finance", format_price(float(last["Close"]), pair))
        m2.metric("Feed age", f"{age_minutes} min")
        m3.metric("RSI · 14", "—" if pd.isna(last["RSI"]) else f"{float(last['RSI']):.1f}")
        trend = "Bullish" if last["EMA_FAST"] > last["EMA_SLOW"] else "Bearish" if last["EMA_FAST"] < last["EMA_SLOW"] else "Neutral"
        m4.metric("EMA trend", trend)

        st.markdown("### Market overview")
        left, right = st.columns([1.55, 1], gap="large")
        with left:
            with st.container(border=True):
                st.markdown("#### TradingView chart")
                tradingview_chart(pair, interval)
                tv_symbol = PAIRS[pair_label]["tradingview"]
                st.markdown(
                    f'<div class="fg-section-note">Interactive chart by TradingView · analysis candles come from Yahoo Finance · '
                    f'<a href="https://www.tradingview.com/chart/?symbol={html.escape(tv_symbol, quote=True)}" '
                    f'target="_blank" rel="noopener noreferrer">Open full chart ↗</a></div>',
                    unsafe_allow_html=True,
                )

        with right:
            technical_side = candidate["side"]
            if technical_side == "NO TRADE":
                final_side = "NO TRADE"
                decision_reason = candidate["reason"]
            elif news_blocked:
                final_side = "NO TRADE"
                decision_reason = f"Technical setup is gated: {news_reason}"
            else:
                final_side = technical_side
                decision_reason = candidate["reason"]

            if final_side == "BUY":
                decision_class, decision_label = "fg-buy", "BUY SETUP"
            elif final_side == "SELL":
                decision_class, decision_label = "fg-sell", "SELL SETUP"
            else:
                decision_class, decision_label = "fg-wait", "NO TRADE"
            st.markdown(
                f'<div class="fg-card"><div class="fg-card-kicker">Decision · rule-based</div>'
                f'<div class="fg-decision {decision_class}">{decision_label}</div>'
                f'<div class="fg-card-copy">{html.escape(str(decision_reason))}</div></div>',
                unsafe_allow_html=True,
            )

            if technical_side != "NO TRADE":
                pip_size = 0.01 if "JPY" in pair else 0.0001
                risk_pips = abs(candidate["entry"] - candidate["stop"]) / pip_size
                levels = [
                    ("Reference entry", candidate["entry"]),
                    ("Stop loss", candidate["stop"]),
                    ("Take profit · TP1 (1R)", candidate["tp1"]),
                    (f"Take profit · TP2 ({reward_risk:g}R)", candidate["target"]),
                ]
                level_html = "".join(
                    f'<div class="fg-level"><span>{html.escape(label)}</span>'
                    f'<strong>{format_price(float(value), pair)}</strong></div>'
                    for label, value in levels
                )
                st.markdown(
                    f'<div class="fg-card"><div class="fg-card-kicker">Illustrative trade plan</div>{level_html}'
                    f'<div class="fg-card-copy">Initial risk distance: {risk_pips:.1f} pips · stop: {stop_atr:g} ATR. '
                    f'TP1 is 1R; TP2 follows the selected reward/risk setting. These are reference levels only.</div></div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<div class="fg-card"><div class="fg-card-kicker">Trade plan</div>'
                    '<div class="fg-card-copy">No entry, stop, or target is issued until the rule set forms a candidate setup.</div></div>',
                    unsafe_allow_html=True,
                )

            if news_blocked:
                st.warning("News safety gate: BLOCKED · " + news_reason)
            else:
                st.success("News safety gate: clear for the configured ±30-minute window.")

        st.markdown("### Analysis")
        a, b = st.columns([1, 1], gap="large")
        with a:
            with st.container(border=True):
                st.markdown("#### Signal evidence")
                st.write(evidence)
                if technical_side != "NO TRADE" and news_blocked:
                    st.caption("A technical candidate exists, but the final decision remains NO TRADE while the news gate is blocked.")
                st.markdown("#### Indicator snapshot")
                i1, i2, i3 = st.columns(3)
                i1.metric("EMA 50", format_price(float(last["EMA_FAST"]), pair))
                i2.metric("EMA 200", format_price(float(last["EMA_SLOW"]), pair))
                i3.metric("ATR · 14", format_price(float(last["ATR"]), pair))
                st.line_chart(df[["Close", "EMA_FAST", "EMA_SLOW"]].tail(250), height=260)

        with b:
            with st.container(border=True):
                st.markdown("#### News safety gate")
                if news_blocked:
                    st.warning(news_reason)
                    st.caption("The dashboard will not promote a technical candidate to BUY or SELL when the calendar is missing, stale, invalid, or inside a configured high-impact event window.")
                else:
                    st.success(news_reason)
                st.caption("The calendar is a manually maintained CSV. No news feed is connected, and a clear window is not a guarantee of safety.")

        st.markdown("### Historical simulation")
        trades = simulate(
            df,
            stop_atr=stop_atr,
            reward_risk=reward_risk,
            daily_limit_r=daily_limit_r,
            cooldown_losses=int(cooldown_losses),
            cooldown_bars=int(cooldown_bars),
        )
        if trades.empty:
            st.info("No completed simulated trades in this sample. That is not proof of safety or profitability.")
        else:
            wins = int((trades["net_r"] > 0).sum())
            gross_win = float(trades.loc[trades.net_r > 0, "net_r"].sum())
            gross_loss = float(-trades.loc[trades.net_r < 0, "net_r"].sum())
            s1, s2, s3, s4 = st.columns(4)
            s1.metric("Closed trades", f"{len(trades):,}")
            s2.metric("Win rate", f"{100 * wins / len(trades):.1f}%")
            s3.metric("Net result", f"{trades.net_r.sum():.2f}R")
            s4.metric("Profit factor", f"{gross_win / gross_loss:.2f}" if gross_loss > 0 else "—")
            st.dataframe(trades.tail(50), use_container_width=True, hide_index=True)
            st.download_button(
                "Download simulation CSV",
                trades.to_csv(index=False).encode("utf-8"),
                file_name="forex_guardian_simulation.csv",
                mime="text/csv",
            )

        st.markdown("---")
        st.caption(
            f"Checked {checked_at.strftime('%Y-%m-%d %H:%M:%S UTC')} · refresh cadence {refresh_seconds}s · "
            "source updates are subject to provider delays. An open browser session does not keep a stopped server online."
        )
    except Exception as exc:
        st.error("Market data is unavailable or stale. No candidate signal was generated.")
        st.caption(f"Reason: {type(exc).__name__}. Refresh later or verify the configured data source.")
        st.caption("The dashboard fails closed rather than displaying a stale trade plan.")


render_dashboard()
