"""Sophia Railway bootstrap — monitoring only, with all trading disabled.

This is intentionally not the legacy SQLite trading engine. Production paper-order
execution must wait for a managed PostgreSQL implementation and tests.
"""
from datetime import datetime, timezone
from contextlib import asynccontextmanager
import os

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

ENGINE_MODE = os.environ.get("SOPHIA_ENGINE_MODE", "MONITOR_ONLY")
if ENGINE_MODE != "MONITOR_ONLY":
    raise RuntimeError("This bootstrap accepts MONITOR_ONLY only; no trading engine installed")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # No trading tasks or polling loops are started here.
    yield

app = FastAPI(title="Sophia Cloud Monitoring Bootstrap", version="0.1.0", lifespan=lifespan,
              docs_url=None, redoc_url=None, openapi_url=None)

@app.get("/health")
def health():
    return {
        "status": "ok", "engine_mode": "MONITOR_ONLY", "paper_orders_enabled": False,
        "real_orders_enabled": False, "stop_manager_enabled": False,
        "database_connected": False,
        "utc": datetime.now(timezone.utc).isoformat(),
    }

@app.get("/api/engine/status")
def engine_status():
    return {
        "name": "Sophia Trading Engine", "state": "PREPARING",
        "paper_orders_enabled": False, "real_orders_enabled": False,
        "note": "Python API deployed separately; Postgres adapter and safety validation are not yet installed.",
        "safety_gates": {"four_percent_equity_risk": "NOT_ENABLED", "seven_gateways": "NOT_ENABLED",
                         "cooldown": "NOT_ENABLED", "durable_stops": "NOT_ENABLED",
                         "reconciliation": "NOT_ENABLED"},
    }

@app.post("/api/orders")
def create_order():
    # Fail closed regardless of request content or auth headers.
    raise HTTPException(status_code=503, detail="Paper-order execution is disabled")

@app.post("/api/positions/{position_id}/stop")
def change_stop(position_id: str):
    raise HTTPException(status_code=503, detail="Stop management is disabled")

@app.get("/")
def root():
    return {"service": "Sophia Trading Engine", "mode": "MONITOR_ONLY",
            "message": "API status available at /health; no trading endpoints enabled."}
