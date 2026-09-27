# GridLock frontend (API integration check)

Minimal React + Vite page that calls `GET /health`, `GET /projects`, and
`GET /opportunities` from the browser, so API connectivity can be tested before
the map UI is built.

```bash
# Terminal 1, repository root: start the API (see docs/api.md)
python -m uvicorn main:app --host 127.0.0.1 --port 8000

# Terminal 2
cd frontend
npm install
npm run dev   # http://localhost:5173
```

The API URL defaults to `http://127.0.0.1:8000`; override it by copying
`.env.example` to `.env.local`. The dev server must stay on port 5173 because
the API only allows browser requests from origins listed in
`GRIDLOCK_CORS_ORIGINS` (default `http://localhost:5173,http://127.0.0.1:5173`).
If the page shows "Could not reach…", check that the API is running and that the
page's origin is in that list.
