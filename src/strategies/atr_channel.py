import pandas as pd
def atr_channel_signal(df: pd.DataFrame, length:int=14, mult:float=2.0):
    ema = df['close'].ewm(span=length, adjust=False).mean()
    tr = (pd.concat([(df['high']-df['low']),(df['high']-df['close'].shift()).abs(),(df['low']-df['close'].shift()).abs()],axis=1).max(axis=1))
    atr = tr.ewm(span=length, adjust=False).mean()
    upper = ema + mult*atr; lower = ema - mult*atr
    return ((df['close']>upper).astype(int) - (df['close']<lower).astype(int)).rename('signal')
