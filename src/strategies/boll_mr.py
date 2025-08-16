import pandas as pd
def boll_mr_signal(df: pd.DataFrame, length:int=20, mult:float=2.0):
    ma = df['close'].rolling(length).mean()
    std = df['close'].rolling(length).std()
    upper = ma + mult*std; lower = ma - mult*std
    long = (df['close']<lower).astype(int); short = -(df['close']>upper).astype(int)
    return (long+short).clip(-1,1).rename('signal')
