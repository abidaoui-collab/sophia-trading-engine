# Sophia Trading Engine — Railway bootstrap

This is a **safe monitoring-only Python FastAPI** service intended as the first
Railway deployment. It deliberately does **not** implement the trading strategy,
order execution, background stop manager, SQLite persistence, or PostgreSQL
adapter. The original Sophia V10.6.4 should **not** be deployed unchanged:
its SQLite file path and API development token are unsuitable for an always-on
cloud trading engine, and a disconnected browser would not protect positions.

## Deploy to Railway

1. Create a **private GitHub repository**, e.g. `sophia-trading-engine`.
2. Upload these repository-root files (extract the ZIP first).
3. Tell ChatGPT your repo name in `owner/name` format. We have already created a
   private Railway project `Sophia Trading Engine`, with an empty service staged.
4. We can attach the repo and configure an always-running Railway service.
5. Set `SOPHIA_ENGINE_MODE=MONITOR_ONLY` (this app refuses every other value).
6. Health endpoint is `GET /health`; order routes return HTTP 503 by design.

## Next engineering work

- Port existing Sophia V10.6.4 to PostgreSQL in the dedicated Supabase schema,
  preserving immutable original history and Trade #17's invalid-fill audit.
- Add account authentication, server-side order validation, fresh quotes, duplicate
  request protection, immutable/tightening-only stops, robust state recovery,
  per-position locking, idempotent worker ticks and crash resilience.
- Add exact indicator parity tests and separate Classic vs Speedy momentum exits.
- Keep all trade endpoints disabled until integration tests pass.

No Binance trading API keys or database administrative credentials should be
committed to GitHub or embedded in Vercel browser source. Use Railway sealed
variables for secrets when the PostgreSQL adapter is implemented.
