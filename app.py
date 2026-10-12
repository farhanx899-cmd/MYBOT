import streamlit as st
import pandas as pd
from datetime import datetime, timezone
from pathlib import Path
from engine import fetch_prices, build_features, latest_candidate, simulate, news_gate

st.set_page_config(page_title="Forex Guardian AI", page_icon="🛡️", layout="wide")
st.title("🛡️ Forex Guardian AI")
st.caption("Open-source starter • signals-only • no broker connection • no live orders")

with st.sidebar:
    st.header("Settings")
    pair = st.selectbox("Forex pair", ["GBPUSD=X", "EURUSD=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X"])
    period = st.selectbox("History", ["180d", "365d", "730d"], index=1)
    interval = st.selectbox("Candle timeframe", ["1h", "1d"], index=0)
    st.subheader("Risk rules (simulation only)")
    stop_atr = st.number_input("Stop distance (ATR multiplier)", 0.5, 5.0, 1.5, 0.25)
    reward_risk = st.number_input("Reward / risk target", 1.0, 5.0, 2.0, 0.25)
    daily_limit_r = st.number_input("Daily shutdown limit (R)", 0.5, 5.0, 2.0, 0.5)
    cooldown_losses = st.number_input("Losses before cooldown", 1, 5, 2, 1)
    cooldown_bars = st.number_input("Cooldown duration (bars)", 1, 72, 24, 1)
    st.caption("1R = the initial risk on one simulated trade. These settings do not protect a real account.")

st.warning("Research prototype only. It does not place, modify, or close orders. Do not use its signals as financial advice.")

if st.button("Refresh data", type="primary"):
    st.session_state["refresh_at"] = datetime.now(timezone.utc).isoformat()

try:
    with st.spinner("Loading market data…"):
        df = fetch_prices(pair, period, interval)
        df = build_features(df, stop_atr=stop_atr, reward_risk=reward_risk)
    candidate, explanation = latest_candidate(df, pair)
    a, b, c = st.columns(3)
    a.metric("Pair", pair)
    b.metric("Last completed candle", str(df.index[-1]))
    c.metric("Latest close", f"{df['Close'].iloc[-1]:.5f}")

    st.subheader("Current decision")
    if candidate["side"] == "NO TRADE":
        st.info(f"**NO TRADE** — {candidate['reason']}")
    else:
        st.success(f"**Candidate: {candidate['side']}** — not an order")
        x, y, z = st.columns(3)
        x.metric("Reference entry", f"{candidate['entry']:.5f}")
        y.metric("Illustrative stop", f"{candidate['stop']:.5f}")
        z.metric("Illustrative target", f"{candidate['target']:.5f}")
    st.write("**Evidence:**", explanation)

    st.subheader("Market structure snapshot")
    last = df.iloc[-1]
    left, right = st.columns(2)
    with left:
        st.metric("RSI (14)", "n/a" if pd.isna(last["RSI"]) else f"{last['RSI']:.1f}")
        st.metric("ATR (14)", "n/a" if pd.isna(last["ATR"]) else f"{last['ATR']:.5f}")
    with right:
        st.metric("EMA 50", f"{last['EMA_FAST']:.5f}")
        st.metric("EMA 200", f"{last['EMA_SLOW']:.5f}")
    st.line_chart(df[["Close", "EMA_FAST", "EMA_SLOW"]].tail(250))

    st.subheader("Historical simulation")
    trades = simulate(df, stop_atr=stop_atr, reward_risk=reward_risk,
                      daily_limit_r=daily_limit_r,
                      cooldown_losses=int(cooldown_losses),
                      cooldown_bars=int(cooldown_bars))
    if trades.empty:
        st.info("No completed simulated trades in this sample. That is not proof of safety or profitability.")
    else:
        wins = int((trades["net_r"] > 0).sum())
        gross_win = trades.loc[trades.net_r > 0, "net_r"].sum()
        gross_loss = -trades.loc[trades.net_r < 0, "net_r"].sum()
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Closed trades", len(trades))
        m2.metric("Win rate", f"{100*wins/len(trades):.1f}%")
        m3.metric("Net R", f"{trades.net_r.sum():.2f}")
        m4.metric("Profit factor", f"{gross_win/gross_loss:.2f}" if gross_loss > 0 else "Undefined")
        st.dataframe(trades.tail(50), use_container_width=True)
        st.download_button("Download simulated trades CSV",
                           trades.to_csv(index=False).encode("utf-8"),
                           file_name="simulated_trades.csv", mime="text/csv")

    st.subheader("News safety gate")
    events_path = Path("news_events.csv")
    if events_path.exists():
        events = pd.read_csv(events_path)
        blocked, reason = news_gate(pair, events)
        st.write("**News gate:**", "BLOCKED" if blocked else "No matching event in configured window")
        st.caption(reason)
        st.dataframe(events, use_container_width=True)
    else:
        st.warning("No news_events.csv found. Automated news is NOT connected; news status is UNKNOWN. Treat this as a research-only signal and do not trade around major releases.")
        st.write("Add events from a source you are authorised to use using the template in news_events_template.csv.")

    st.subheader("Data capability notes")
    st.write("- Spot-Forex consolidated delta/CVD and a true global liquidity heatmap are not provided by this price-only data source.")
    st.write("- ICT/SMC detections here are simple heuristics (swings and fair-value-gap candidates), not a complete interpretation of ICT concepts.")
    st.write("- News is not fetched automatically in this starter.")
except Exception as exc:
    st.error("SAFE STOP — no candidate signal generated.")
    st.code(str(exc))
    st.caption("If data is missing, stale, or invalid, this prototype refuses to generate a candidate.")
