import pandas as pd
def supertrend_signal(df: pd.DataFrame, period:int=10, mult:float=3.0):
    hl = df['high'] - df['low']
    hc = (df['high'] - df['close'].shift()).abs()
    lc = (df['low'] - df['close'].shift()).abs()
    tr = pd.concat([hl,hc,lc], axis=1).max(axis=1)
    atr = tr.ewm(span=period, adjust=False).mean()
    basic_upper = (df['high'] + df['low'])/2 + mult*atr
    basic_lower = (df['high'] + df['low'])/2 - mult*atr
    final_upper = basic_upper.copy(); final_lower = basic_lower.copy()
    for i in range(1, len(df)):
        final_upper.iloc[i] = min(basic_upper.iloc[i], final_upper.iloc[i-1]) if df['close'].iloc[i-1] > final_upper.iloc[i-1] else basic_upper.iloc[i]
        final_lower.iloc[i] = max(basic_lower.iloc[i], final_lower.iloc[i-1]) if df['close'].iloc[i-1] < final_lower.iloc[i-1] else basic_lower.iloc[i]
    up = df['close'] > final_lower; down = df['close'] < final_upper
    return (up.astype(int) - down.astype(int)).rename('signal')
