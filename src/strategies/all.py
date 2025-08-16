from .ema_trend import ema_trend_signal
from .macd import macd_signal
from .donchian import donchian_signal
from .boll_mr import boll_mr_signal
from .atr_channel import atr_channel_signal
from .supertrend import supertrend_signal
from .ichimoku import ichimoku_signal

ALL = {
    'EMA Trend': ema_trend_signal,
    'MACD': macd_signal,
    'Donchian': donchian_signal,
    'Bollinger MR': boll_mr_signal,
    'ATR Channel': atr_channel_signal,
    'SuperTrend': supertrend_signal,
    'Ichimoku': ichimoku_signal
}
TREND = ['EMA Trend','MACD','Donchian','ATR Channel','SuperTrend','Ichimoku']
MR = ['Bollinger MR']
