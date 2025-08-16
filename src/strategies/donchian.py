import pandas as pd
def donchian_signal(df: pd.DataFrame, lookback:int=55):
    hh = df['high'].rolling(lookback).max()
    ll = df['low'].rolling(lookback).min()
    return ((df['close']>hh.shift()).astype(int) - (df['close']<ll.shift()).astype(int)).clip(-1,1).rename('signal')
