# =========================
# HELIOS — main.py (simple)
# =========================

# --- Patch chemin d'import pour Streamlit Cloud ---
import sys, os
ROOT = os.path.dirname(__file__)
sys.path.insert(0, ROOT)                         # repo root
sys.path.insert(0, os.path.join(ROOT, "src"))    # /src pour import direct
# -------------------------------------------------

import streamlit as st
import yaml
import pandas as pd
import numpy as np
import requests

# ---- Imports robustes (avec fallback) ----
# Data
try:
    from src.data.loader import load_or_fetch, fetch_last_price
except Exception as e:
    st.stop()

# Stratégies & recherche (chargement dynamique, plus besoin de ALL)
from importlib import import_module
import pkgutil

try:
    from src.research.ensemble import ensemble_weights, blended_signal
    try:
        from src.research.regime import kmeans_regime
        HAS_REGIME = True
    except Exception:
        HAS_REGIME = False
except Exception as e:
    st.error(f"Import recherche impossible: {e}")
    st.stop()

# 🔎 Détecte automatiquement toutes les stratégies présentes dans src/strategies
STRATS = {}
try:
    pkg = import_module("src.strategies")     # doit exister : src/strategies/
    for _, modname, ispkg in pkgutil.iter_modules(pkg.__path__):
        if ispkg or modname in ("__init__", "all"):   # ignore sous-packages et all.py
            continue
        m = import_module(f"src.strategies.{modname}")
        # Cherche une fonction de signal plausible
        candidates = (
            "signal",
            f"{modname}_signal",
            "ema_trend_signal", "macd_momentum_signal", "donchian_breakout_signal",
            "boll_mr_signal", "kama_trend_signal", "rsi_reversion_signal",
            "ichimoku_signal", "supertrend_signal", "atr_channel_signal",
        )
        fn = next((getattr(m, c) for c in candidates if hasattr(m, c)), None)
        if callable(fn):
            pretty = modname.replace("_", " ").title()
            # quelques jolis noms connus
            pretty = {
                "Ema Trend": "EMA Trend",
                "Macd": "MACD Momentum",
                "Donchian": "Donchian Breakout",
                "Boll Mr": "Bollinger MR",
                "Atr Channel": "ATR Channel",
                "Supertrend": "SuperTrend",
            }.get(pretty, pretty)
            STRATS[pretty] = fn
except Exception as e:
    st.error(f"Chargement des stratégies impossible : {e}")
    st.stop()

if not STRATS:
    st.error("Aucune stratégie détectée dans src/strategies/.")
    st.stop()

# Risque & backtest
try:
    from src.risk.levels import adaptive_levels, size_fixed_pct, size_fixed_usd, size_kelly_fraction
except Exception as e:
    st.error(f"Import risk-levels impossible: {e}")
    st.stop()

try:
    from src.backtest.engine import backtest
    from src.backtest.metrics import sharpe, max_drawdown, sortino, calmar
except Exception:
    backtest = None

# Portefeuille (avec Fallback inline si le module n’existe pas)
try:
    from src.portfolio.db import list_positions, open_position, close_position
    PORTF_OK = True
except Exception:
    PORTF_OK = False
    import sqlite3, datetime
    DB_FALLBACK = os.path.join(ROOT, "portfolio.db")

    def _init_db():
        conn = sqlite3.connect(DB_FALLBACK); c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS positions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            open_ts TEXT, close_ts TEXT, symbol TEXT, side TEXT,
            entry REAL, sl REAL, tp REAL, qty REAL,
            status TEXT, exit_price REAL, pnl REAL, note TEXT
        )""")
        conn.commit(); conn.close()

    def open_position(symbol, side, entry, sl, tp, qty, note=""):
        _init_db()
        conn = sqlite3.connect(DB_FALLBACK); c = conn.cursor()
        c.execute("""INSERT INTO positions (open_ts, close_ts, symbol, side, entry, sl, tp, qty, status, exit_price, pnl, note)
                     VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                  (datetime.datetime.utcnow().isoformat(), None, symbol, side.upper(),
                   float(entry), float(sl), float(tp), float(qty), "OPEN", None, None, note))
        conn.commit(); rid = c.lastrowid; conn.close(); return rid

    def close_position(pos_id, exit_price, note="CLOSE"):
        _init_db()
        conn = sqlite3.connect(DB_FALLBACK); c = conn.cursor()
        row = conn.execute('SELECT side, entry, qty FROM positions WHERE id=? AND status="OPEN"', (pos_id,)).fetchone()
        if not row:
            conn.close(); raise ValueError("position introuvable ou déjà close")
        side, entry, qty = row
        pnl = (float(exit_price) - float(entry)) * float(qty) * (1 if side.upper()=="LONG" else -1)
        conn.execute("""UPDATE positions SET close_ts=?, status=?, exit_price=?, pnl=?, note=? WHERE id=?""",
                     (datetime.datetime.utcnow().isoformat(), "CLOSED", float(exit_price), float(pnl), note, pos_id))
        conn.commit(); conn.close(); return pnl

    def list_positions(status=None, limit=500):
        _init_db()
        conn = sqlite3.connect(DB_FALLBACK)
        q = "SELECT id, open_ts, close_ts, symbol, side, entry, sl, tp, qty, status, exit_price, pnl, note FROM positions"
        params = ()
        if status in ("OPEN","CLOSED"):
            q += " WHERE status=?"; params = (status,)
        q += " ORDER BY id DESC LIMIT ?"; params = params + (int(limit),)
        rows = list(conn.execute(q, params)); conn.close()
        return pd.DataFrame(rows, columns=["id","open_ts","close_ts","symbol","side","entry","sl","tp","qty","status","exit_price","pnl","note"])

# ---------- Config ----------
def _read_yaml(path, default=None):
    try:
        with open(path, "r") as f: return yaml.safe_load(f)
    except Exception:
        return default if default is not None else {}

CFG = _read_yaml(os.path.join(ROOT, "configs", "default.yml"), {})
BRAND = _read_yaml(os.path.join(ROOT, "configs", "brand.yml"),
                   {"app_name":"HELIOS — Signals", "tagline":"One-tap signals · manual execution", "logo_path":"assets/logo.png"})

# ---------- UI ----------
st.set_page_config(page_title=BRAND.get("app_name","HELIOS"), page_icon=BRAND.get("logo_path","assets/logo.png"), layout="centered")

c1, c2 = st.columns([1,6])
with c1:
    try: st.image(BRAND.get("logo_path","assets/logo.png"), width=56)
    except Exception: st.write("☀️")
with c2:
    st.title(BRAND.get("app_name","HELIOS — Signals"))
    st.caption(BRAND.get("tagline","One-tap signals · manual execution"))

with st.sidebar:
    st.subheader("⚙️ Réglages")
    exchange = st.selectbox("Exchange", ["okx","bybit","kraken","coinbase","kucoin","binance"], index=0)
    symbols = st.multiselect("Paires suivies", (CFG.get("app",{}).get("symbols") or
                         ["BTC/USDT","ETH/USDT","BNB/USDT","SOL/USDT","XRP/USDT","ADA/USDT"]), default=None)
    if not symbols:
        symbols = ["BTC/USDT","ETH/USDT","SOL/USDT","BNB/USDT","XRP/USDT"]

    tf = st.selectbox("Timeframe", (CFG.get("app",{}).get("timeframes") or ["15m","1h","4h"]), index=1)
    mode = st.selectbox("Mode de risque", ["Conservateur","Balancé","Agressif","Custom"], index=1)
    capital = st.number_input("Capital (USD)", value=float(CFG.get("backtest",{}).get("initial_cash",1000)), step=100.0)
    # presets
    presets = {
        "Conservateur": dict(risk_pct=0.5, max_expo=40.0, min_rr=1.5, max_positions=2),
        "Balancé":     dict(risk_pct=1.0, max_expo=70.0, min_rr=1.6, max_positions=3),
        "Agressif":     dict(risk_pct=2.0, max_expo=100.0, min_rr=1.8, max_positions=5),
    }
    if mode!="Custom":
        p = presets[mode]
        risk_pct = st.slider("Risque %/trade", 0.1, 5.0, p["risk_pct"], 0.1)
        max_expo  = st.slider("Cap d’exposition (%)", 10.0, 200.0, p["max_expo"], 1.0)
        min_rr    = st.slider("R/R minimum", 1.0, 5.0, p["min_rr"], 0.1)
        max_pos   = st.slider("Nb max positions", 1, 8, p["max_positions"], 1)
    else:
        risk_pct = st.slider("Risque %/trade", 0.1, 5.0, 1.0, 0.1)
        max_expo  = st.slider("Cap d’exposition (%)", 10.0, 200.0, 80.0, 1.0)
        min_rr    = st.slider("R/R minimum", 1.0, 5.0, 1.6, 0.1)
        max_pos   = st.slider("Nb max positions", 1, 8, 3, 1)

    st.caption("TF = cadence de recalcul. Exécution 100% manuelle.")

tabs = st.tabs(["🏠 Top Picks", "📈 Portefeuille", "🧾 Journal", "🧪 Backtest 3Y"])

# --------- Helpers ----------
def rr_from_levels(entry, sl, tp):
    R = abs(entry - sl)
    return float(abs(tp - entry) / (R if R>0 else 1e-9))

def confidence_from_backtest(df, sig):
    if backtest is None or len(df) < 100:
        return 50.0
    bt = backtest(df, sig, initial_cash=1.0, fee_bps=2.0, slippage_bps=1.0)
    s = max(0.0, min(3.0, sharpe(bt["pnl"])))
    dd = abs(max_drawdown(bt["equity"]))
    score = (s/3.0)*70.0 + (1.0 - min(dd,0.4)/0.4)*30.0
    return round(100.0*score/100.0, 1)

def size_qty(account_equity, entry, sl, risk_pct):
    return size_fixed_pct(account_equity, entry, sl, risk_pct)

# --------- TAB 1: TOP PICKS ----------
with tabs[0]:
    st.subheader("Top Picks (1 clic)")
    if st.button("🚀 Générer les meilleurs trades (max 5)"):
        rows = []
        for sym in symbols:
            df = load_or_fetch(exchange, sym, tf, limit=2500)
            # Regime gating (si dispo)
            sigs = {name: fn(df) for name, fn in STRATS.items()}
            if HAS_REGIME:
                reg = kmeans_regime(df)
                reg_now = str(reg.iloc[-1])
            else:
                reg_now = "neutral"
            w = ensemble_weights(df, sigs, window=int((CFG.get("app",{}).get("ensemble_window") or 300)))
            sig = blended_signal(sigs, w)
            d = int(sig.iloc[-1])
            if d == 0:
                continue
            lvl = adaptive_levels(df, d,
                atr_mult_sl=float(CFG.get("risk",{}).get("atr_k_sl", 2.5)),
                atr_mult_tp=float(CFG.get("risk",{}).get("atr_k_tp", 3.5))
            )
            if not lvl:
                continue
            rr = rr_from_levels(lvl["entry"], lvl["sl"], lvl["tp"])
            if rr < min_rr:
                continue
            qty = size_qty(capital, lvl["entry"], lvl["sl"], risk_pct)
            conf = confidence_from_backtest(df, sig)
            rows.append({
                "symbol": sym,
                "dir": "LONG" if d>0 else "SHORT",
                "entry": lvl["entry"], "sl": lvl["sl"], "tp": lvl["tp"],
                "rr": rr, "qty": qty, "confiance": conf, "regime": reg_now
            })
        if not rows:
            st.warning("Aucun signal suffisamment solide pour l’instant.")
        else:
            df_rows = pd.DataFrame(rows).sort_values(["confiance","rr"], ascending=False).head(5)
            st.dataframe(df_rows[["symbol","dir","entry","sl","tp","qty","rr","confiance","regime"]].round(6),
                         use_container_width=True)
            # Enregistrer tout d’un coup
            if st.button("📌 J’ai pris ces trades"):
                n=0
                for _, r in df_rows.iterrows():
                    open_position(r["symbol"], r["dir"], float(r["entry"]), float(r["sl"]),
                                  float(r["tp"]), float(r["qty"]), note="TOPPICK")
                    n+=1
                st.success(f"{n} trade(s) ajouté(s) au portefeuille.")
                st.rerun()

# --------- TAB 2: PORTEFEUILLE ----------
with tabs[1]:
    st.subheader("Positions ouvertes")
    open_df = list_positions(status="OPEN", limit=500)
    if open_df.empty:
        st.info("Aucune position ouverte.")
    else:
        # PnL latent live
        latest_prices = {sym: fetch_last_price(exchange, sym) for sym in open_df["symbol"].unique()}
        def _latent(row):
            last = latest_prices.get(row["symbol"], row["entry"])
            sign = 1 if row["side"]=="LONG" else -1
            return (last - row["entry"]) * row["qty"] * sign
        open_df["last"] = open_df["symbol"].map(latest_prices)
        open_df["PnL_latent"] = open_df.apply(_latent, axis=1)
        st.dataframe(open_df[["id","symbol","side","entry","sl","tp","qty","last","PnL_latent"]].round(6),
                     use_container_width=True)

        # Auto-close si TP/SL touché
        if st.button("🔍 Mettre à jour (TP/SL)"):
            closed = 0
            for _, r in open_df.iterrows():
                px = latest_prices.get(r["symbol"], r["entry"])
                if r["side"]=="LONG" and (px>=r["tp"] or px<=r["sl"]):
                    pnl = close_position(int(r["id"]), px, note="AUTO_TP_SL")
                    st.success(f"Position {int(r['id'])} clôturée. PnL ≈ {pnl:.2f}")
                    closed += 1
                if r["side"]=="SHORT" and (px<=r["tp"] or px>=r["sl"]):
                    pnl = close_position(int(r["id"]), px, note="AUTO_TP_SL")
                    st.success(f"Position {int(r['id'])} clôturée. PnL ≈ {pnl:.2f}")
                    closed += 1
            if closed: st.rerun()

        # Clôture manuelle
        st.markdown("---")
        st.write("Clôturer manuellement :")
        for _, r in open_df.iterrows():
            cols = st.columns([3,1,1])
            with cols[0]:
                st.write(f"{r['symbol']} · {r['side']} — entry {r['entry']:.6f} qty {r['qty']:.4f}")
            with cols[1]:
                mkt = latest_prices.get(r["symbol"], r["entry"])
                st.write(f"⚡ {mkt:.6f}")
            with cols[2]:
                if st.button(f"Clôturer #{int(r['id'])}", key=f"close_{int(r['id'])}"):
                    pnl = close_position(int(r["id"]), mkt, note="MANUAL")
                    st.success(f"Position {int(r['id'])} clôturée. PnL ≈ {pnl:.2f}")
                    st.rerun()

# --------- TAB 3: JOURNAL ----------
with tabs[2]:
    st.subheader("Historique (clôturées)")
    closed_df = list_positions(status="CLOSED", limit=1000)
    if closed_df.empty:
        st.info("Aucun trade clôturé.")
    else:
        st.dataframe(closed_df[["id","open_ts","close_ts","symbol","side","entry","exit_price","qty","pnl","note"]],
                     use_container_width=True)
        st.metric("P&L réalisé (total)", f"{closed_df['pnl'].sum():.2f} USD")

# --------- TAB 4: BACKTEST ----------
with tabs[3]:
    st.subheader("Backtest rapide 3 ans (journalier)")
    if backtest is None:
        st.warning("Module de backtest non disponible dans ce build.")
    else:
        sym = st.selectbox("Symbole", symbols)
        if st.button("▶️ Lancer backtest"):
            df = load_or_fetch(exchange, sym, "1d", limit=1500)
            sigs = {k: fn(df) for k, fn in STRATS.items()}
            w = ensemble_weights(df, sigs, window=300)
            sig = blended_signal(sigs, w)
            bt = backtest(df, sig, initial_cash=1.0, fee_bps=2.0, slippage_bps=1.0)
            st.line_chart(pd.Series(bt["equity"], name="Equity (norm.)"))
            st.write({
                "Sharpe": round(sharpe(bt["pnl"]), 2),
                "Sortino": round(sortino(bt["pnl"]), 2),
                "MaxDD": round(max_drawdown(bt["equity"]), 3),
                "Calmar": round(calmar(bt["equity"]), 2)
            })
