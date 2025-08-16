import sys, os; sys.path.append(os.path.dirname(__file__))
import streamlit as st, yaml, pandas as pd, numpy as np
from configs.brand import APP_NAME, TAGLINE, LOGO_PATH
from src.data.loader import load_or_fetch, fetch_last_price
from src.strategies.all import ALL as STRATS, TREND, MR
from src.research.ensemble import softmax, blend
from src.research.backtest import backtest, metrics
from src.research.confidence import compute_confidence
from src.risk.levels import levels_from_signal, position_size
from src.portfolio.db import list_positions, open_position, close_position, list_ledger
from src.journal.db import add_trade, list_trades, update_trade_result

st.set_page_config(page_title=APP_NAME, page_icon=LOGO_PATH, layout='centered')

# Sidebar settings
cfg = yaml.safe_load(open('configs/default.yml'))
st.sidebar.image(LOGO_PATH, width=64)
st.sidebar.markdown(f"### {APP_NAME}\n{TAGLINE}")

exchange = st.sidebar.selectbox('Exchange', ['okx','bybit','kraken','coinbase','kucoin','binance'], index=0)
tf = st.sidebar.selectbox('Timeframe', cfg['app']['timeframes'], index=1)
mode = st.sidebar.selectbox('Mode de risque', list(cfg['risk_modes'].keys())+['Custom'], index=1)
capital = st.sidebar.number_input('Capital (USD)', min_value=100.0, value=1000.0, step=100.0)

if mode!='Custom':
    rm = cfg['risk_modes'][mode]
    risk_pct = float(rm['risk_pct']); max_gross = float(rm['max_gross_pct']); min_rr = float(rm['min_rr']); max_pos = int(rm['max_positions'])
else:
    risk_pct = st.sidebar.slider('Risk % par trade', 0.1, 5.0, float(cfg['risk']['risk_pct_custom']), 0.1)
    max_gross = st.sidebar.slider('Max gross exposure %', 10.0, 200.0, 80.0, 1.0)
    min_rr = st.sidebar.slider('R/R minimal', 1.0, 3.0, 1.5, 0.1)
    max_pos = st.sidebar.slider('Max positions', 1, 10, 3, 1)

symbols = st.sidebar.multiselect('Paires', cfg['app']['symbols'], default=cfg['app']['symbols'][:8])

st.title('Top Picks — One Tap')
st.caption('Un seul bouton : je calcule la recherche, le budget et je sors les meilleurs trades.')

# Helper: compute current equity/exposure from portfolio DB + last prices
def compute_portfolio_state():
    pos = list_positions()
    if pos.empty:
        exposure = 0.0; unreal = 0.0
    else:
        values = []
        unreal = 0.0
        for _,r in pos.iterrows():
            price = fetch_last_price(exchange, r['symbol'])
            value = price * r['qty']
            # unrealized PnL (approx): (price-entry)*qty * dir
            dir = 1 if r['side']=='LONG' else -1
            unreal += (price - r['entry']) * r['qty'] * dir
            values.append(abs(value))
        exposure = float(np.sum(values))
    ledger = list_ledger(limit=10000)
    realized = float(ledger['pnl'].sum()) if not ledger.empty else 0.0
    equity = capital + realized + unreal
    return {'equity': equity, 'exposure': exposure, 'unreal': unreal, 'realized': realized, 'positions': pos}

state = compute_portfolio_state()
available_to_allocate = max(0.0, (state['equity'] * (max_gross/100.0)) - state['exposure'])

st.markdown(f"**Équity actuelle (approx)** : ${state['equity']:.2f}  ·  **Exposition** : ${state['exposure']:.2f}  ·  **Budget dispo** : ${available_to_allocate:.2f}")

# Dashboard: generate picks
if st.button('🚀 Générer les meilleurs trades (5)'):
    rows = []
    for sym in symbols:
        df = load_or_fetch(exchange, sym, tf, limit=2000)
        # Build simple robust ensemble (equal weights)
        sigs = {name: STRATS[name](df) for name in STRATS}
        w = {k: 1.0/len(sigs) for k in sigs}
        sig = blend(sigs, w)
        direction = int(sig.iloc[-1])
        lvl = levels_from_signal(df, direction, sl_mult=cfg['risk']['atr_k_sl'], tp_mult=cfg['risk']['atr_k_tp'])
        if not lvl: continue
        # R/R
        r = abs(lvl['entry']-lvl['sl']); rr = abs(lvl['tp']-lvl['entry'])/max(r,1e-9)
        if rr < min_rr or direction==0:
            continue
        # confidence from quick backtest window
        conf, m = compute_confidence(df, sigs, window=800)
        # suggested qty by risk %
        qty = position_size(state['equity'], lvl['entry'], lvl['sl'], risk_pct)
        rows.append({'symbol': sym, 'dir': 'LONG' if direction>0 else 'SHORT', 'entry': lvl['entry'], 'sl': lvl['sl'], 'tp': lvl['tp'], 'rr': rr, 'qty': qty, 'conf': conf})
    if not rows:
        st.info('Aucun trade éligible selon les filtres.')
    else:
        import pandas as pd, numpy as np
        dfp = pd.DataFrame(rows).sort_values(['conf','rr'], ascending=False).head(5).reset_index(drop=True)
        # smart allocation: weight by conf*rr, bounded by available budget
        weights = (dfp['conf']*dfp['rr']).values
        w = weights / weights.sum()
        # convert budget to position value target; then to qty by entry price
        budgets = w * available_to_allocate
        dfp['alloc_$'] = budgets
        dfp['qty_suggested'] = (budgets / dfp['entry']).clip(lower=0)
        # override by risk-based qty if smaller (safety)
        dfp['qty'] = np.minimum(dfp['qty_suggested'], dfp['qty'])
        st.dataframe(dfp[['symbol','dir','entry','sl','tp','rr','conf','qty']].round(6), use_container_width=True)
        # selection to record
        take = st.multiselect('Sélectionne les trades à prendre', dfp['symbol'].tolist(), default=dfp['symbol'].tolist())
        if st.button('📌 J’ai pris ces trades'):
            for i,row in dfp.iterrows():
                if row['symbol'] not in take: continue
                add_trade(row['symbol'], row['dir'], float(row['entry']), float(row['sl']), float(row['tp']), float(row['qty']), float(row['rr']), note='AUTO')
                open_position(row['symbol'], row['dir'], float(row['entry']), float(row['sl']), float(row['tp']), float(row['qty']))
            st.success('Trades ajoutés au portefeuille & journal.')
            st.rerun()

st.markdown('---')
st.header('📦 Portefeuille (live)')
pos = state['positions']
if pos.empty:
    st.info('Aucune position ouverte.')
else:
    # compute live P&L for each
    data=[]
    for _,r in pos.iterrows():
        price = fetch_last_price(exchange, r['symbol'])
        dir = 1 if r['side']=='LONG' else -1
        pnl = (price - r['entry']) * r['qty'] * dir
        data.append({'id': int(r['id']), 'symbol': r['symbol'], 'side': r['side'], 'entry': r['entry'], 'sl': r['sl'], 'tp': r['tp'], 'qty': r['qty'], 'last': price, 'unreal_pnl': pnl})
    dfpos = pd.DataFrame(data)
    st.dataframe(dfpos[['id','symbol','side','last','entry','sl','tp','qty','unreal_pnl']].round(6), use_container_width=True)
    pid = st.number_input('ID à clôturer (market)', min_value=1, step=1)
    if st.button('❌ Clôturer cette position'):
        row = dfpos[dfpos['id']==pid]
        if not row.empty:
            r=row.iloc[0]
            exit_price = float(r['last']); pnl = float(r['unreal_pnl'])
            close_position(int(r['id']), exit_price, pnl)
            st.success(f"Position {int(r['id'])} clôturée. PnL ≈ {pnl:.2f}")
            st.rerun()
    if st.button('🔄 Rafraîchir P&L'):
        st.rerun()

st.markdown('---')
st.header('🧾 Journal')
tr = list_trades(limit=1000)
if tr.empty:
    st.info('Journal vide.')
else:
    st.dataframe(tr[['id','ts','symbol','side','entry','sl','tp','qty','rr','result','pnl','note']].round(6), use_container_width=True)
    # auto mark WIN/LOSS based on last price vs TP/SL
    if st.button('🔍 Mettre à jour résultats (TP/SL)'):
        updates=[]
        for _,t in tr.iterrows():
            if str(t['result']).upper() in ('WIN','LOSS','CLOSE'): continue
            price = fetch_last_price(exchange, t['symbol'])
            result=''
            if t['side']=='LONG':
                if price>=t['tp']: result='WIN'
                elif price<=t['sl']: result='LOSS'
            else:
                if price<=t['tp']: result='WIN'
                elif price>=t['sl']: result='LOSS'
            if result:
                exit_price = t['tp'] if result=='WIN' else t['sl']
                pnl = (exit_price - t['entry'])*t['qty']*(1 if t['side']=='LONG' else -1)
                update_trade_result(int(t['id']), result, float(pnl))
                # also close position if exists
                poss = list_positions()
                m = poss[poss['symbol']==t['symbol']]
                if not m.empty:
                    from src.portfolio.db import close_position
                    close_position(int(m.iloc[0]['id']), float(exit_price), float(pnl))
                updates.append({'id':int(t['id']),'symbol':t['symbol'],'result':result,'pnl':pnl})
        st.write(pd.DataFrame(updates))
        st.rerun()
