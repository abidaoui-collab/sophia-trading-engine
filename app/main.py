"""Sophia monitor-only database diagnostic. All order endpoints fail closed."""
from datetime import datetime, timezone
from contextlib import asynccontextmanager
import os
import socket
import ssl
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException

if os.getenv("SOPHIA_ENGINE_MODE", "MONITOR_ONLY") != "MONITOR_ONLY":
    raise RuntimeError("This version only supports MONITOR_ONLY")

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(title="Sophia Cloud DB Probe", version="0.3.0", lifespan=lifespan,
              docs_url=None, redoc_url=None, openapi_url=None)


def db_check():
    """Probe a read-only query and expose only safe diagnostic categories."""
    dsn = os.getenv("SOPHIA_DATABASE_URL", "").strip()
    if not dsn:
        return {"connected": False, "state": "NOT_CONFIGURED", "error_category": "MISSING_DSN"}
    try:
        parsed = urlsplit(dsn)
        if parsed.scheme not in ("postgresql", "postgres") or not parsed.hostname:
            return {"connected": False, "state": "CONNECTION_FAILED", "error_category": "INVALID_DSN_FORMAT"}
    except ValueError:
        return {"connected": False, "state": "CONNECTION_FAILED", "error_category": "INVALID_DSN_FORMAT"}
    try:
        import psycopg
        with psycopg.connect(dsn, connect_timeout=7,
                             options="-c default_transaction_read_only=on") as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT count(*) FROM sophia.orders")
                count = cur.fetchone()[0]
        return {"connected": True, "state": "CONNECTED_READ_ONLY", "historical_orders": count}
    except Exception as exc:
        import psycopg
        sqlstate = getattr(exc, "sqlstate", None)
        if sqlstate == "28P01":
            category = "INVALID_PASSWORD"
        elif sqlstate == "28000":
            category = "INVALID_AUTHORIZATION"
        elif sqlstate == "42501":
            category = "PERMISSION_DENIED"
        elif sqlstate == "3D000":
            category = "DATABASE_NOT_FOUND"
        elif sqlstate == "42P01":
            category = "TABLE_NOT_FOUND"
        elif isinstance(exc, (TimeoutError, socket.timeout)):
            category = "TIMEOUT"
        elif isinstance(exc, ssl.SSLError):
            category = "SSL_ERROR"
        elif isinstance(exc, psycopg.ProgrammingError):
            category = "DSN_OR_PROGRAMMING_ERROR"
        elif isinstance(exc, psycopg.OperationalError):
            category = "POSTGRES_OPERATIONAL_ERROR"
        else:
            category = "OTHER_DATABASE_ERROR"
        return {"connected": False, "state": "CONNECTION_FAILED",
                "error_category": category, "sqlstate": sqlstate,
                "exception_type": type(exc).__name__}


@app.get("/health")
def health():
    return {"status": "ok", "engine_mode": "MONITOR_ONLY", "paper_orders_enabled": False,
            "real_orders_enabled": False, "stop_manager_enabled": False,
            "utc": datetime.now(timezone.utc).isoformat()}


@app.get("/api/engine/status")
def status():
    return {"name": "Sophia Trading Engine", "version": "0.3.0", "state": "MONITOR_ONLY",
            "paper_orders_enabled": False, "real_orders_enabled": False,
            "database": db_check(),
            "safety_gates": {"four_percent_equity_risk": "NOT_ENABLED",
                             "seven_gateways": "NOT_ENABLED", "cooldown": "NOT_ENABLED",
                             "durable_stops": "NOT_ENABLED", "reconciliation": "NOT_ENABLED"}}


@app.post("/api/orders")
def orders():
    raise HTTPException(status_code=503, detail="Paper orders disabled")


@app.post("/api/positions/{position_id}/stop")
def stops(position_id: str):
    raise HTTPException(status_code=503, detail="Stop management disabled")


@app.get("/")
def root():
    return {"service": "Sophia Trading Engine", "mode": "MONITOR_ONLY", "health": "/health"}
