"""Sophia Cloud v0.5: private read-only journal; trading fails closed."""
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from decimal import Decimal
from urllib.parse import urlsplit
import hmac
import os
import socket
import ssl

from fastapi import FastAPI, Header, HTTPException

if os.getenv('SOPHIA_ENGINE_MODE', 'MONITOR_ONLY') != 'MONITOR_ONLY':
    raise RuntimeError('This version only supports MONITOR_ONLY')

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(title='Sophia Cloud Journal API', version='0.5.0', lifespan=lifespan,
              docs_url=None, redoc_url=None, openapi_url=None)

def connect():
    import psycopg
    dsn = os.getenv('SOPHIA_DATABASE_URL', '').strip()
    if not dsn:
        raise ValueError('MISSING_DSN')
    p = urlsplit(dsn)
    if p.scheme not in ('postgresql', 'postgres') or not p.hostname:
        raise ValueError('INVALID_DSN_FORMAT')
    return psycopg.connect(dsn, connect_timeout=7,
                           options='-c default_transaction_read_only=on')

def db_check():
    try:
        with connect() as conn, conn.cursor() as cur:
            cur.execute('select count(*) from sophia.orders')
            n = cur.fetchone()[0]
        return {'connected': True, 'state': 'CONNECTED_READ_ONLY', 'historical_orders': n}
    except Exception as exc:
        sqlstate = getattr(exc, 'sqlstate', None)
        if isinstance(exc, ValueError):
            category = str(exc) if str(exc) in ('MISSING_DSN', 'INVALID_DSN_FORMAT') else 'INVALID_DSN_FORMAT'
        elif sqlstate == '28P01':
            category = 'INVALID_PASSWORD'
        elif sqlstate == '42501':
            category = 'PERMISSION_DENIED'
        elif sqlstate == '42P01':
            category = 'TABLE_NOT_FOUND'
        elif isinstance(exc, (TimeoutError, socket.timeout)):
            category = 'TIMEOUT'
        elif isinstance(exc, ssl.SSLError):
            category = 'SSL_ERROR'
        else:
            category = 'DATABASE_ERROR'
        return {'connected': False, 'state': 'CONNECTION_FAILED', 'error_category': category}

def private_access(authorization: str | None):
    token = os.getenv('SOPHIA_JOURNAL_API_TOKEN', '')
    if not token or len(token) < 32:
        raise HTTPException(status_code=503, detail='Private API not configured')
    provided = authorization[7:] if authorization and authorization.startswith('Bearer ') else ''
    if not hmac.compare_digest(provided, token):
        raise HTTPException(status_code=401, detail='Unauthorized')

def as_number(x):
    if x is None:
        return None
    try:
        return float(Decimal(str(x)))
    except Exception:
        return None

@app.get('/health')
def health():
    return {'status': 'ok', 'engine_mode': 'MONITOR_ONLY', 'paper_orders_enabled': False,
            'real_orders_enabled': False, 'stop_manager_enabled': False,
            'utc': datetime.now(timezone.utc).isoformat()}

@app.get('/api/engine/status')
def status():
    return {'name': 'Sophia Trading Engine', 'version': '0.5.0', 'state': 'MONITOR_ONLY',
            'paper_orders_enabled': False, 'real_orders_enabled': False,
            'database': db_check(),
            'journal_api': 'AUTH_REQUIRED',
            'safety_gates': {'four_percent_equity_risk': 'NOT_ENABLED',
                             'seven_gateways': 'NOT_ENABLED', 'cooldown': 'NOT_ENABLED',
                             'durable_stops': 'NOT_ENABLED', 'reconciliation': 'NOT_ENABLED'}}

@app.get('/api/journal')
def journal(authorization: str | None = Header(default=None)):
    private_access(authorization)
    with connect() as conn, conn.cursor() as cur:
        cur.execute('SELECT id,payload FROM sophia.orders ORDER BY id DESC LIMIT 500')
        records = cur.fetchall()
        cur.execute('SELECT count(*) FROM sophia.rejected_attempts')
        rejected = cur.fetchone()[0]
    fields = ('id','side','status','created_at','filled_at','closed_at','fill_price',
              'close_price','limit_price','quantity','pnl','exit_reason','research_tag')
    trades = [{k: p.get(k) for k in fields} | {'id': row_id} for row_id,p in records]
    return {'source': 'supabase_live_read_only', 'as_of': datetime.now(timezone.utc).isoformat(),
            'count': len(trades), 'rejected_attempts': rejected, 'trades': trades,
            'audit_note': 'Trade #17 invalid simulated fill remains in original P&L'}

@app.get('/api/account/overview')
def overview(authorization: str | None = Header(default=None)):
    private_access(authorization)
    with connect() as conn, conn.cursor() as cur:
        cur.execute('SELECT payload FROM sophia.orders ORDER BY id')
        orders = [r[0] for r in cur.fetchall()]
    closed = [x for x in orders if x.get('status') == 'CLOSED']
    pnl = [as_number(x.get('pnl')) for x in closed]
    pnl = [x for x in pnl if x is not None]
    return {'source': 'historical_gross_unadjusted', 'orders': len(orders),
            'closed_trades': len(closed), 'wins': sum(x > 0 for x in pnl),
            'gross_pnl_usd': round(sum(pnl), 2),
            'win_rate_pct': round(100 * sum(x > 0 for x in pnl)/len(closed), 2) if closed else None,
            'trade_17_invalid_fill_not_reconciled': True,
            'equity': None, 'net_pnl': None}

@app.post('/api/orders')
def orders():
    raise HTTPException(status_code=503, detail='Paper orders disabled')

@app.post('/api/positions/{position_id}/stop')
def stops(position_id: str):
    raise HTTPException(status_code=503, detail='Stop management disabled')

@app.get('/')
def root():
    return {'service': 'Sophia Trading Engine', 'mode': 'MONITOR_ONLY', 'health': '/health'}
