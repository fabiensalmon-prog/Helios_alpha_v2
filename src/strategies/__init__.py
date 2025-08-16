# src/strategies/__init__.py
# Expose un dict ALL = { "Nom stratégie": fonction_signal(df) }
# Gère plusieurs noms de fichiers/fonctions (macd.py vs macd_momentum.py, etc.)

from importlib import import_module

def _pick(mod_name: str, *fn_candidates: str):
    """importe .mod_name et renvoie la 1re fonction existante parmi fn_candidates"""
    m = import_module(f".{mod_name}", __name__)
    for fn in fn_candidates:
        if hasattr(m, fn):
            return getattr(m, fn)
    raise AttributeError(f"Aucune fonction trouvée dans {mod_name}: {fn_candidates}")

ALL = {}

# --- Trend/Breakout ---
try:
    ALL["EMA Trend"] = _pick("ema_trend", "ema_trend_signal", "signal")
except Exception:
    pass

try:
    ALL["MACD Momentum"] = _pick("macd", "macd_momentum_signal", "macd_signal", "signal")
except Exception:
    pass

try:
    ALL["Donchian Breakout"] = _pick("donchian", "donchian_breakout_signal", "signal")
except Exception:
    pass

try:
    ALL["SuperTrend"] = _pick("supertrend", "supertrend_signal", "signal")
except Exception:
    pass

try:
    ALL["ATR Channel"] = _pick("atr_channel", "atr_channel_signal", "signal")
except Exception:
    pass

# --- Mean Reversion / autres (si présents chez toi) ---
try:
    ALL["Bollinger MR"] = _pick("boll_mr", "boll_mr_signal", "signal")
except Exception:
    pass

try:
    ALL["Ichimoku"] = _pick("ichimoku", "ichimoku_signal", "signal")
except Exception:
    pass

# (si tu ajoutes plus tard rsi_reversion.py, kama_trend.py, etc. remets 2 blocs try comme ci-dessus)

# Groupes pour le gating éventuel (si ton code les utilise)
TREND_STRATS = ["EMA Trend","MACD Momentum","Donchian Breakout","SuperTrend","ATR Channel"]
MR_STRATS    = ["Bollinger MR"]
