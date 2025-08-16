import sqlite3, os, datetime
DB = os.path.join(os.path.dirname(__file__), 'portfolio.db')

def init():
    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS positions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts_open TEXT,
        symbol TEXT,
        side TEXT,
        entry REAL,
        sl REAL,
        tp REAL,
        qty REAL
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS ledger (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts_close TEXT,
        symbol TEXT,
        side TEXT,
        entry REAL,
        exit REAL,
        qty REAL,
        pnl REAL
    )''')
    conn.commit(); conn.close()

def open_position(symbol, side, entry, sl, tp, qty):
    init(); conn=sqlite3.connect(DB); c=conn.cursor()
    c.execute('INSERT INTO positions (ts_open,symbol,side,entry,sl,tp,qty) VALUES (?,?,?,?,?,?,?)',
              (datetime.datetime.utcnow().isoformat(), symbol, side, entry, sl, tp, qty))
    conn.commit(); conn.close()

def list_positions():
    init(); conn=sqlite3.connect(DB); c=conn.cursor()
    c.execute('SELECT id, ts_open, symbol, side, entry, sl, tp, qty FROM positions ORDER BY id DESC')
    rows=c.fetchall(); conn.close()
    import pandas as pd
    return pd.DataFrame(rows, columns=['id','ts_open','symbol','side','entry','sl','tp','qty'])

def close_position(pid, exit_price, pnl):
    conn=sqlite3.connect(DB); c=conn.cursor()
    # move to ledger
    c.execute('SELECT symbol, side, entry, qty FROM positions WHERE id=?',(pid,))
    r=c.fetchone(); 
    if not r: conn.close(); return
    symbol, side, entry, qty = r
    c.execute('INSERT INTO ledger (ts_close,symbol,side,entry,exit,qty,pnl) VALUES (?,?,?,?,?,?,?)',
              (datetime.datetime.utcnow().isoformat(), symbol, side, entry, exit_price, qty, pnl))
    c.execute('DELETE FROM positions WHERE id=?',(pid,))
    conn.commit(); conn.close()

def list_ledger(limit=500):
    init(); conn=sqlite3.connect(DB); c=conn.cursor()
    c.execute('SELECT id, ts_close, symbol, side, entry, exit, qty, pnl FROM ledger ORDER BY id DESC LIMIT ?', (limit,))
    rows=c.fetchall(); conn.close()
    import pandas as pd
    return pd.DataFrame(rows, columns=['id','ts_close','symbol','side','entry','exit','qty','pnl'])
