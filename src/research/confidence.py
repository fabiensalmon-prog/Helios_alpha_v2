import numpy as np
from .backtest import backtest, metrics
from .ensemble import softmax, blend

def score_from_metrics(m):
    # combine Sharpe (0..3+), MaxDD (-1..0), Hit (0..1) -> 0..100
    sharpe = max(m['sharpe'], 0.0)
    dd_term = 1.0 + m['maxdd']  # closer to 1 is better
    hit = m['hit']
    raw = 0.6*(sharpe/3.0) + 0.25*(dd_term) + 0.15*hit
    return max(0.0, min(100.0, 100*raw))

def compute_confidence(df, signals: dict, window: int = 800):
    # equal weights ensemble for robustness
    w = {k: 1.0/len(signals) for k in signals}
    sig = blend(signals, w)
    bt = backtest(df.iloc[-window:], sig.iloc[-window:])
    m = metrics(bt)
    return score_from_metrics(m), m  # (0..100), metrics
