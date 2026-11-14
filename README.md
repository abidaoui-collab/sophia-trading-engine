# Sophia Railway — DB connectivity probe (monitor-only)

This package is an incremental update to the existing GitHub starter. Replace the repository's files with the extracted files, commit to `main`, and Railway will redeploy.

## Railway Variables

Already set: `SOPHIA_ENGINE_MODE=MONITOR_ONLY`, `SOPHIA_PAPER_ORDERS_ENABLED=false`, `SOPHIA_REAL_ORDERS_ENABLED=false`, `SOPHIA_SUPABASE_URL`.

To check the existing Supabase database, set **one secret variable in Railway's dashboard**, `SOPHIA_DATABASE_URL`, to the PostgreSQL connection string from the **Sophia Cloud** Supabase project's **Connect** panel. Use the **Session pooler** connection string for Railway, and replace the password placeholder with the project's actual database password. The secret should be entered **directly into Railway Variables**, not shared in chat, placed in GitHub, or included in a screenshot.

The probe enforces a read-only transaction setting and performs only `SELECT count(*) FROM sophia.orders`. It does not place paper trades or modify the database. The database credential itself may still have broad privileges: use a dedicated least-privilege DB role before enabling order functionality.

## Checks

- `/health`: confirms FastAPI is running (does **not** verify database).
- `/api/engine/status`: returns `database.state=CONNECTED_READ_ONLY` and `historical_orders=20` when connected.
- `POST /api/orders` and `POST /api/positions/{id}/stop`: always return HTTP 503.

The API is publicly accessible at the generated Railway domain; never expose secrets in responses. No live or paper execution is included.
