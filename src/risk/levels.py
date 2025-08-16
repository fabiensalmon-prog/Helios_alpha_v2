import pandas as pd, numpy as np
def atr(df: pd.DataFrame, length: int = 14):
    hl = df['high'] - df['low']; hc = (df['high'] - df['close'].shift()).abs(); lc = (df['low'] - df['close'].shift()).abs()
    tr = pd.concat([hl,hc,lc], axis=1).max(axis=1)
    return tr.ewm(span=length, adjust=False).mean()

def levels_from_signal(df: pd.DataFrame, direction: int, sl_mult: float=2.5, tp_mult: float=3.5):
    if direction == 0: return None
    a = float(atr(df,14).iloc[-1]); price = float(df['close'].iloc[-1])
    if direction>0: sl = price - sl_mult*a; tp = price + tp_mult*a
    else: sl = price + sl_mult*a; tp = price - tp_mult*a
    return {'entry': price, 'sl': sl, 'tp': tp, 'atr': a}

def position_size(account_equity: float, entry: float, sl: float, risk_pct: float):
    per_unit_loss = abs(entry - sl)
    risk_amt = account_equity * (risk_pct/100.0)
    return 0.0 if per_unit_loss<=0 else risk_amt / per_unit_loss
