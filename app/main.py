"""Sophia cloud read-only database probe. All order endpoints fail closed."""
from datetime import datetime, timezone
from contextlib import asynccontextmanager
import os
from fastapi import FastAPI, HTTPException

if os.getenv('SOPHIA_ENGINE_MODE', 'MONITOR_ONLY') != 'MONITOR_ONLY':
    raise RuntimeError('This version only supports MONITOR_ONLY')

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(title='Sophia Cloud DB Probe', version='0.2.0', lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)



def db_check():
    """Read-only database probe with safe error classification."""
    dsn = os.getenv("SOPHIA_DATABASE_URL")
    if not dsn:
        return {"connected": False, "state": "NOT_CONFIGURED"}

    try:
        import psycopg

        with psycopg.connect(
            dsn,
            connect_timeout=5,
            options="-c default_transaction_read_only=on",
        ) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT count(*) FROM sophia.orders")
                count = cur.fetchone()[0]

        return {
            "connected": True,
            "state": "CONNECTED_READ_ONLY",
            "historical_orders": count,
        }

    except Exception as exc:
        import socket
        import ssl
        import psycopg

        sqlstate = getattr(exc, "sqlstate", None)

        if sqlstate == "28P01":
            category = "AUTHENTICATION_FAILED"
        elif sqlstate == "42501":
            category = "DATABASE_PERMISSION_DENIED"
        elif sqlstate == "3D000":
            category = "DATABASE_NOT_FOUND"
        elif sqlstate == "42P01":
            category = "TABLE_NOT_FOUND"
        elif isinstance(exc, (TimeoutError, socket.timeout)):
            category = "CONNECTION_TIMEOUT"
        elif isinstance(exc, ssl.SSLError):
            category = "SSL_ERROR"
        elif isinstance(exc, psycopg.ProgrammingError):
            category = "CONNECTION_CONFIGURATION_ERROR"
        elif isinstance(exc, psycopg.OperationalError):
    category = (
        "POSTGRES_SERVER_ERROR"
        if getattr(exc, "sqlstate", None)
        else "TRANSPORT_OR_HANDSHAKE_ERROR"
    )
        else:
            category = "UNKNOWN_DATABASE_ERROR"

        return {
            "connected": False,
            "state": "CONNECTION_FAILED",
            "error_category": category,
        }


@app.get('/health')
def health():
    return {'status': 'ok', 'engine_mode': 'MONITOR_ONLY', 'paper_orders_enabled': False,
            'real_orders_enabled': False, 'stop_manager_enabled': False,
            'utc': datetime.now(timezone.utc).isoformat()}

@app.get('/api/engine/status')
def status():
    return {'name': 'Sophia Trading Engine', 'state': 'MONITOR_ONLY',
            'paper_orders_enabled': False, 'real_orders_enabled': False,
            'database': db_check(),
            'safety_gates': {'four_percent_equity_risk': 'NOT_ENABLED',
                             'seven_gateways': 'NOT_ENABLED', 'cooldown': 'NOT_ENABLED',
                             'durable_stops': 'NOT_ENABLED', 'reconciliation': 'NOT_ENABLED'}}

@app.post('/api/orders')
def orders():
    raise HTTPException(status_code=503, detail='Paper orders disabled')

@app.post('/api/positions/{position_id}/stop')
def stops(position_id: str):
    raise HTTPException(status_code=503, detail='Stop management disabled')

@app.get('/')
def root():
    return {'service': 'Sophia Trading Engine', 'mode': 'MONITOR_ONLY', 'health': '/health'}
