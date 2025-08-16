import numpy as np, pandas as pd
def softmax(x):
    x = np.array(x, dtype=float)
    x = x - np.nanmin(x)
    e = np.exp(x)
    return e/np.sum(e)

def blend(signals: dict, weights: dict):
    df = pd.concat(signals.values(), axis=1).fillna(0.0)
    df.columns = list(signals.keys())
    w = pd.Series(weights).reindex(df.columns).fillna(0.0)
    pos = (df*w).sum(axis=1).clip(-1,1)
    return pos.rename('signal')
