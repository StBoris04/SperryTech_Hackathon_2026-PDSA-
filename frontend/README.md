# GridLock frontend

React + Tailwind CSS + Leaflet (OpenStreetMap tiles, no API key) interface over
`GET /projects` and `GET /opportunities`:

- Map of both utilities' projects in distinct colors. Approximate locations are
  dashed and translucent; projects without coordinates stay in the list only.
- Ranked opportunities exactly as the API orders them. Selecting one draws the
  pair on the map and shows distance, timeline status, uncertainty, the reason,
  and both projects.
- Project list with search and utility/map filters. Selecting a project shows
  its dates at source precision, location method, notes, and source evidence,
  plus a 25-mile radius on the map.
- The UI does not compute distances, rankings, or savings; those come from the
  API and are never invented.

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
