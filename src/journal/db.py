import sqlite3, os, datetime
DB = os.path.join(os.path.dirname(__file__), 'journal.db')
def init_db():
    conn=sqlite3.connect(DB); c=conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT,
        symbol TEXT,
        side TEXT,
        entry REAL,
        sl REAL,
        tp REAL,
        qty REAL,
        rr REAL,
        result TEXT,
        pnl REAL,
        note TEXT
    )'''); conn.commit(); conn.close()
def add_trade(symbol, side, entry, sl, tp, qty, rr, note=''):
    init_db(); conn=sqlite3.connect(DB); c=conn.cursor()
    c.execute('INSERT INTO trades (ts,symbol,side,entry,sl,tp,qty,rr,result,pnl,note) VALUES (?,?,?,?,?,?,?,?,?,?,?)',
              (datetime.datetime.utcnow().isoformat(), symbol, side, entry, sl, tp, qty, rr, '', None, note)); conn.commit(); conn.close()
def update_trade_result(trade_id, result, pnl):
    conn=sqlite3.connect(DB); c=conn.cursor()
    c.execute('UPDATE trades SET result=?, pnl=? WHERE id=?', (result, pnl, trade_id)); conn.commit(); conn.close()
def list_trades(limit=500):
    init_db(); conn=sqlite3.connect(DB); c=conn.cursor()
    c.execute('SELECT id, ts, symbol, side, entry, sl, tp, qty, rr, result, pnl, note FROM trades ORDER BY id DESC LIMIT ?', (limit,))
    rows=c.fetchall(); conn.close()
    import pandas as pd
    return pd.DataFrame(rows, columns=['id','ts','symbol','side','entry','sl','tp','qty','rr','result','pnl','note'])
