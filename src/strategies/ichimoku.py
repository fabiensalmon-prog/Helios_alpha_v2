import pandas as pd
def ichimoku_signal(df: pd.DataFrame, conv:int=9, base:int=26, spanb:int=52):
    high9 = df['high'].rolling(conv).max(); low9 = df['low'].rolling(conv).min()
    tenkan = (high9 + low9) / 2
    high26 = df['high'].rolling(base).max(); low26 = df['low'].rolling(base).min()
    kijun = (high26 + low26) / 2
    spanA = ((tenkan + kijun) / 2).shift(base)
    high52 = df['high'].rolling(spanb).max(); low52 = df['low'].rolling(spanb).min()
    spanB = ((high52 + low52) / 2).shift(base)
    cross = (tenkan > kijun).astype(int) - (tenkan < kijun).astype(int)
    cloud_up = (df['close'] > spanA) & (df['close'] > spanB)
    cloud_down = (df['close'] < spanA) & (df['close'] < spanB)
    sig = cross.where(cloud_up, 0).where(~cloud_down, -1)
    return sig.fillna(0).rename('signal')
