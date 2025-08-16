import pandas as pd
def macd_signal(df: pd.DataFrame, fast:int=12, slow:int=26, signal:int=9):
    ema_f = df['close'].ewm(span=fast, adjust=False).mean()
    ema_s = df['close'].ewm(span=slow, adjust=False).mean()
    macd = ema_f - ema_s
    macd_sig = macd.ewm(span=signal, adjust=False).mean()
    return ((macd>macd_sig).astype(int) - (macd<macd_sig).astype(int)).rename('signal')
