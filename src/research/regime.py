import pandas as pd
from sklearn.cluster import KMeans

def kmeans_regime(df: pd.DataFrame, n_clusters: int = 3, lookback: int = 400) -> pd.Series:
    """Clustering de régime simple (ret, vol, trend). Retourne une série de labels."""
    X = pd.DataFrame({
        "ret": df["close"].pct_change().rolling(5).mean(),
        "vol": df["close"].pct_change().rolling(20).std(),
        "trend": df["close"].pct_change().rolling(50).mean(),
    }).dropna()
    if len(X) < 20:
        return pd.Series(["neutral"] * len(df), index=df.index)
    X = X.iloc[-lookback:]
    km = KMeans(n_clusters=n_clusters, n_init=5, random_state=42)
    labels = km.fit_predict(X)
    stats = X.copy()
    stats["cluster"] = labels
    g = stats.groupby("cluster").agg({"trend": "mean", "vol": "mean"})
    up = g["trend"].idxmax(); down = g["trend"].idxmin(); hv = g["vol"].idxmax()
    mapping = {up: "up", down: "down"}
    for c in range(n_clusters):
        if c not in mapping:
            mapping[c] = "high_vol" if c == hv else "neutral"
    names = [mapping[int(i)] for i in labels]
    ser = pd.Series(index=X.index, data=names).reindex(df.index).ffill().fillna("neutral")
    return ser