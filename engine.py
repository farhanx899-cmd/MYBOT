import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timezone

PIP = 0.0001
ESTIMATED_SPREAD = 0.00012
ESTIMATED_SLIPPAGE = 0.00002

def fetch_prices(pair="GBPUSD=X", period="365d", interval="1h"):
    raw = yf.download(pair, period=period, interval=interval,
                      auto_adjust=False, progress=False, threads=False)
    if raw is None or raw.empty:
        raise RuntimeError("No price data returned; no signal allowed.")
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    cols = ["Open", "High", "Low", "Close"]
    if any(c not in raw.columns for c in cols):
        raise RuntimeError("Required OHLC columns missing; no signal allowed.")
    df = raw[cols].copy()
    df = df[~df.index.duplicated(keep="last")].sort_index()
    df = df.apply(pd.to_numeric, errors="coerce").dropna()
    if len(df) < 250:
        raise RuntimeError("Insufficient history; no signal allowed.")
    # Drop the latest candle because it may still be forming.
    df = df.iloc[:-1].copy()
    if df.empty or (df[cols] <= 0).any().any():
        raise RuntimeError("Invalid price values; no signal allowed.")
    now = pd.Timestamp.now(tz="UTC")
    last = pd.Timestamp(df.index[-1])
    last = last.tz_localize("UTC") if last.tzinfo is None else last.tz_convert("UTC")
    max_age = 3 * 3600 if interval == "1h" else 48 * 3600
    if (now - last).total_seconds() > max_age:
        raise RuntimeError("Price data is stale; no signal allowed.")
    return df

def build_features(df, stop_atr=1.5, reward_risk=2.0):
    x = df.copy()
    c, h, l = x.Close, x.High, x.Low
    x["EMA_FAST"] = c.ewm(span=50, adjust=False).mean()
    x["EMA_SLOW"] = c.ewm(span=200, adjust=False).mean()
    delta = c.diff()
    gain, loss = delta.clip(lower=0), -delta.clip(upper=0)
    ag = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    al = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    rs = ag / al.replace(0, np.nan)
    x["RSI"] = 100 - 100 / (1 + rs)
    prev = c.shift(1)
    tr = pd.concat([h-l, (h-prev).abs(), (l-prev).abs()], axis=1).max(axis=1)
    x["ATR"] = tr.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    x["BUY"] = ((c > x.EMA_FAST) & (c.shift(1) <= x.EMA_FAST.shift(1)) &
                (x.EMA_FAST > x.EMA_SLOW) & (x.RSI > 55))
    x["SELL"] = ((c < x.EMA_FAST) & (c.shift(1) >= x.EMA_FAST.shift(1)) &
                 (x.EMA_FAST < x.EMA_SLOW) & (x.RSI < 45))
    # Basic SMC-style swing levels; heuristic only.
    x["swing_high"] = h.shift(2).rolling(5).max()
    x["swing_low"] = l.shift(2).rolling(5).min()
    # Three-candle FVG candidates. These are not entry signals by themselves.
    x["bull_fvg"] = l > h.shift(2)
    x["bear_fvg"] = h < l.shift(2)
    return x

def latest_candidate(df, pair):
    row = df.iloc[-1]
    evidence = []
    if not np.isfinite(row["ATR"]) or not np.isfinite(row["RSI"]):
        return {"side":"NO TRADE","reason":"Indicators unavailable"}, "Insufficient indicator data."
    evidence.append(f"RSI={row['RSI']:.1f}")
    evidence.append("trend bullish" if row.EMA_FAST > row.EMA_SLOW else "trend bearish" if row.EMA_FAST < row.EMA_SLOW else "trend neutral")
    evidence.append("bullish FVG candidate" if bool(row.bull_fvg) else "bearish FVG candidate" if bool(row.bear_fvg) else "no new FVG candidate")
    evidence.append("recent swing high/low levels calculated")
    side = "BUY" if bool(row.BUY) else "SELL" if bool(row.SELL) else None
    if side is None:
        return {"side":"NO TRADE","reason":"Entry rules not satisfied"}, "; ".join(evidence)
    entry = float(row.Close)
    risk = float(row.ATR) * 1.5
    stop = entry-risk if side == "BUY" else entry+risk
    target = entry+risk*2 if side == "BUY" else entry-risk*2
    return {"side":side,"entry":entry,"stop":stop,"target":target,"reason":"Baseline conditions met"}, "; ".join(evidence)

def simulate(df, stop_atr=1.5, reward_risk=2.0, daily_limit_r=2.0,
             cooldown_losses=2, cooldown_bars=24):
    trades, daily = [], {}
    consecutive, cooldown_until, pos = 0, -1, None
    for i in range(205, len(df)-1):
        row, ts = df.iloc[i], df.index[i]
        day = pd.Timestamp(ts).date()
        if pos is not None:
            stop_hit = row.Low <= pos["stop"] if pos["side"]=="BUY" else row.High >= pos["stop"]
            target_hit = row.High >= pos["target"] if pos["side"]=="BUY" else row.Low <= pos["target"]
            reason = None
            if stop_hit: exit_price, reason = pos["stop"], "STOP"
            elif target_hit: exit_price, reason = pos["target"], "TARGET"
            if reason:
                direction = 1 if pos["side"]=="BUY" else -1
                net_r = direction*(float(exit_price)-pos["entry"])/pos["risk"]
                net_r -= (ESTIMATED_SPREAD+ESTIMATED_SLIPPAGE)/pos["risk"]
                daily[day] = daily.get(day,0.0)+net_r
                trades.append({"entry_time":pos["time"],"exit_time":ts,"side":pos["side"],
                               "exit_reason":reason,"net_r":net_r})
                consecutive = consecutive+1 if net_r < 0 else 0
                if consecutive >= cooldown_losses:
                    cooldown_until = i+cooldown_bars
                    consecutive = 0
                pos = None
        if pos is not None or i < cooldown_until or daily.get(day,0.0) <= -daily_limit_r:
            continue
        side = "BUY" if bool(row.BUY) else "SELL" if bool(row.SELL) else None
        if side is None or not np.isfinite(row.ATR): continue
        entry = float(df.iloc[i+1].Open)
        risk = float(row.ATR)*stop_atr
        if risk <= 0 or not np.isfinite(risk): continue
        stop = entry-risk if side=="BUY" else entry+risk
        target = entry+risk*reward_risk if side=="BUY" else entry-risk*reward_risk
        pos = {"side":side,"entry":entry,"risk":risk,"stop":stop,"target":target,"time":df.index[i+1]}
    return pd.DataFrame(trades)

def news_gate(pair, events):
    currencies = {"GBPUSD=X":{"GBP","USD"},"EURUSD=X":{"EUR","USD"},
                  "USDJPY=X":{"USD","JPY"},"AUDUSD=X":{"AUD","USD"},
                  "USDCAD=X":{"USD","CAD"}}.get(pair)
    if not currencies:
        return True, "Pair not supported by news filter; blocked."
    required = {"time_utc","currency","impact","title","updated_utc"}
    if events.empty or not required.issubset(events.columns):
        return True, "Calendar missing required columns; blocked."
    now = pd.Timestamp.now(tz="UTC")
    updated = pd.to_datetime(events["updated_utc"].iloc[0], utc=True, errors="coerce")
    if pd.isna(updated) or (now-updated).total_seconds() < 0 or (now-updated).total_seconds() > 24*3600:
        return True, "Calendar is stale or has invalid timestamp; blocked."
    for _, e in events.iterrows():
        if str(e["impact"]).upper() != "HIGH" or str(e["currency"]).upper() not in currencies:
            continue
        t = pd.to_datetime(e["time_utc"], utc=True, errors="coerce")
        if pd.isna(t): return True, "Invalid event timestamp; blocked."
        minutes = (t-now).total_seconds()/60
        if -30 <= minutes <= 30:
            return True, f"High-impact event window: {e['title']}"
    return False, "No matching high-impact event in configured ±30-minute window."
