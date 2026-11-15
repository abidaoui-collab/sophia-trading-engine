# Sophia Cloud v0.5 — private read-only journal API

Replace `app/main.py` in the existing GitHub repository with this file. Retain the existing Dockerfile and requirements.txt (`psycopg` must be installed). Commit to `main`; Railway redeploys.

Railway environment variables:
- `SOPHIA_ENGINE_MODE=MONITOR_ONLY`
- `SOPHIA_DATABASE_URL` (already configured)
- `SOPHIA_JOURNAL_API_TOKEN` (random secret, at least 32 characters; set privately in Railway)

Public `/health` and `/api/engine/status` remain available. `/api/journal` and `/api/account/overview` require `Authorization: Bearer <token>` and never return passwords. Missing/invalid token fails closed.

Do **not** place the token in client-side JavaScript or GitHub. A future Vercel server-side proxy must handle authentication and access controls before exposing journal data to a browser.

Order endpoints remain disabled. Trade #17's invalid fill is still included in unadjusted gross P&L.
