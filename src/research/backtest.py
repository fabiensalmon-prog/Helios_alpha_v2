import numpy as np, pandas as pd
def backtest(df: pd.DataFrame, signal: pd.Series, fee_bps: float = 2.0, slippage_bps: float = 1.0):
    ret = df['close'].pct_change().fillna(0.0)
    pos = signal.shift().fillna(0.0).clip(-1,1)
    cost = (pos.diff().abs().fillna(0.0))*((fee_bps+slippage_bps)/10000.0)
    pnl = pos*ret - cost
    equity = (1+pnl).cumprod()
    return {'pnl': pnl, 'equity': equity}

def metrics(bt):
    pnl = bt['pnl']; eq = bt['equity']
    s = pnl.std(); sharpe = float(pnl.mean()/s*np.sqrt(365*24)) if s>0 else 0.0
    dd = float((eq/eq.cummax()-1).min())
    hit = float((pnl>0).mean())
    return {'sharpe': sharpe, 'maxdd': dd, 'hit': hit}
