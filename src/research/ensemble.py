import numpy as np
import pandas as pd
from ..backtest.engine import compute
from ..backtest.metrics import sharpe, max_drawdown

def _score(pnl: pd.Series, equity: pd.Series) -> float:
    # score simple et robuste : Sharpe + (−|MaxDD|)
    try:
        s = float(sharpe(pnl))
    except Exception:
        s = 0.0
    try:
        dd = float(max_drawdown(equity))
    except Exception:
        dd = 0.0
    # dd est négatif (ex: -0.35). On préfère un drawdown moins profond.
    return s + (1.0 + dd)  # plus grand = mieux

def ensemble_weights(df: pd.DataFrame, signals: dict, window: int = 300) -> pd.Series:
    """Calcule des poids (softmax) pour chaque stratégie selon sa perf récente."""
    if not signals:
        return pd.Series(dtype=float)
    # aligne / tronque
    end = len(df)
    start = max(0, end - int(window))
    scores = {}
    for name, sig in signals.items():
        try:
            pnl, equity = None, None
            # compute() renvoie (ret, pos, pnl, equity)
            _, _, pnl, equity = compute(df.iloc[start:end], sig.iloc[start:end])
            scores[name] = _score(pnl, equity)
        except Exception:
            scores[name] = -1e9  # très mauvais si erreur
    keys = list(scores.keys())
    arr = np.array([scores[k] for k in keys], dtype=float)
    # softmax stable
    arr = arr - np.nanmax(arr)
    w = np.exp(arr)
    w = w / np.nansum(w) if np.nansum(w) != 0 else np.ones_like(w)/len(w)
    return pd.Series(w, index=keys)

def blended_signal(signals: dict, weights: pd.Series) -> pd.Series:
    """Combine les signaux (−1..+1) selon les poids fournis et clippe en [−1, +1]."""
    if not signals:
        return pd.Series(dtype=float, name="signal")
    df = pd.concat(signals.values(), axis=1).fillna(0.0)
    df.columns = list(signals.keys())
    w = weights.reindex(df.columns).fillna(0.0).values.reshape(1, -1)
    pos = (df.values * w).sum(axis=1)
    out = pd.Series(pos, index=df.index, name="signal").clip(-1, 1)
    return out