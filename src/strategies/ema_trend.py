import pandas as pd
def ema_trend_signal(df: pd.DataFrame, fast:int=12, slow:int=48):
    ema_f = df['close'].ewm(span=fast, adjust=False).mean()
    ema_s = df['close'].ewm(span=slow, adjust=False).mean()
    return ((ema_f>ema_s).astype(int) - (ema_f<ema_s).astype(int)).rename('signal')
