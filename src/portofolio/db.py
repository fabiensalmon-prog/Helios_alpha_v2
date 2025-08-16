import os, sqlite3, datetime
import pandas as pd

# DB path stored alongside this file
DB = os.path.join(os.path.dirname(__file__), 'portfolio.db')

def _init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS positions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        open_ts TEXT,
        close_ts TEXT,
        symbol TEXT,
        side TEXT,
        entry REAL,
        sl REAL,
        tp REAL,
        qty REAL,
        status TEXT,
        exit_price REAL,
        pnl REAL,
        note TEXT
    )''')
    conn.commit()
    conn.close()

def open_position(symbol:str, side:str, entry:float, sl:float, tp:float, qty:float, note:str=''):
    """Create/open a position. Returns row id."""
    _init_db()
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('INSERT INTO positions (open_ts, close_ts, symbol, side, entry, sl, tp, qty, status, exit_price, pnl, note) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
              (datetime.datetime.utcnow().isoformat(), None, symbol, side.upper(), float(entry), float(sl), float(tp), float(qty), 'OPEN', None, None, note))
    conn.commit()
    rowid = c.lastrowid
    conn.close()
    return rowid

def close_position(pos_id:int, exit_price:float, note:str='CLOSE'):
    """Close an open position at the given price and compute P&L."""
    _init_db()
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('SELECT symbol, side, entry, qty FROM positions WHERE id=? AND status="OPEN"', (pos_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        raise ValueError(f'Position {pos_id} not found or already closed')
    symbol, side, entry, qty = row
    side = side.upper()
    # P&L = (exit - entry) * qty for LONG, inverted for SHORT
    pnl = (float(exit_price) - float(entry)) * float(qty) * (1 if side=='LONG' else -1)
    c.execute('UPDATE positions SET close_ts=?, status=?, exit_price=?, pnl=?, note=? WHERE id=?',
              (datetime.datetime.utcnow().isoformat(), 'CLOSED', float(exit_price), float(pnl), note, pos_id))
    conn.commit()
    conn.close()
    return pnl

def list_positions(status:str=None, limit:int=500):
    """Return a DataFrame of positions. status: None | 'OPEN' | 'CLOSED'"""
    _init_db()
    conn = sqlite3.connect(DB)
    q = 'SELECT id, open_ts, close_ts, symbol, side, entry, sl, tp, qty, status, exit_price, pnl, note FROM positions'
    params = ()
    if status in ('OPEN','CLOSED'):
        q += ' WHERE status=?'; params = (status,)
    q += ' ORDER BY id DESC LIMIT ?'
    params = params + (int(limit),)
    rows = list(conn.execute(q, params))
    conn.close()
    df = pd.DataFrame(rows, columns=['id','open_ts','close_ts','symbol','side','entry','sl','tp','qty','status','exit_price','pnl','note'])
    return df