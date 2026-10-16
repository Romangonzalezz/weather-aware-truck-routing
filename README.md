# Weather-aware truck routing

A React + Django app that helps a truck driver pick the safest of up to three routes. It samples the
forecast along each route at the time the truck will actually be there, classifies the risk with the
assignment's wind, rain, snow and load rules, recommends a route, and draws a 0-48 hour weather heatmap
along the trip corridor.

Live demo: _add the Vercel URL here_

## Run it locally

Needs Python 3.12+ and Node 20+. No API keys: routing, geocoding, weather and map tiles are all keyless.

```
# backend (http://localhost:8000)
cd backend
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements-dev.txt    # Linux/macOS: .venv/bin/python
.venv/Scripts/python manage.py runserver 8000

# frontend (http://localhost:5173), in another terminal
npm --prefix frontend install
npm --prefix frontend run dev
```

The frontend talks to `http://localhost:8000` in dev. Set `VITE_API_URL` (see `frontend/.env.example`) to
point it somewhere else. The backend allows `http://localhost:5173` through CORS; override with
`CORS_ALLOWED_ORIGINS` (comma separated).

## How it works

```
React + MapLibre  --POST /api/plan-------->  Django (DRF)
                  --POST /api/corridor--->     routing/planner.py    plan: routes -> checkpoints -> weather -> risk -> rank
                  --GET  /api/geocode---->     routing/corridor.py   heatmap grid and hourly scores
                                               routing/clients/      Photon, Valhalla/OSRM, Open-Meteo
```

1. `/api/plan` geocodes both places (Photon), asks Valhalla for truck routes with the load weight and two
   alternatives, and fills any gap from OSRM.
2. Each route gets a checkpoint every 10, 25 or 50 miles plus one at the destination. The ETA of each
   checkpoint is interpolated from the router's per-maneuver times, not from an average speed.
3. Open-Meteo hourly forecasts are read for all checkpoints in batched requests. Each checkpoint uses the
   forecast hour nearest to its ETA.
4. Every checkpoint gets a risk level, each route is summarized, and the routes are ranked.
5. `/api/corridor` takes the plan's route geometries and returns a severity score for every hour for each
   cell of a grid around the routes. The frontend fetches it once per plan and keeps all hours in memory.

## Decisions and assumptions

- **Providers.** Valhalla (public OSM server) for truck routing, OSRM as a filler when Valhalla returns fewer
  than three routes or rejects a trip (over 1,500 km), Photon for geocoding and autocomplete, Open-Meteo for
  weather. OSRM uses car routing and has no maneuver times, so its ETAs are interpolated linearly over the route.
  Routes within 2% of the same length are treated as one road, so some trips have fewer than three routes.
- **Risk boundaries** follow the assignment table exactly: wind 25 is Moderate, 35 High, 45 Severe, 55 No Travel;
  rain 0.10, 0.25, 0.50, 1.00 in/hr (above 1.00 is No Travel); snow 0.5, 1.0, 2.0, 3.0 in/hr (above 3.0 is
  No Travel). Rain is `rain` plus `showers`. A checkpoint's level is the worst of wind, rain and snow.
- **Load rules** apply to wind only, as the spec words them: 55 mph or more is No Travel for any load; 45-54 mph
  with more than 30,000 lb is No Travel; 35-44 mph with more than 40,000 lb is Severe.
- **Miles per checkpoint.** A checkpoint stands for the stretch since the previous one, so Severe and High
  miles are the sum of those stretches.
- **Recommendation order** is the assignment's: fewest Severe miles, then fewest High miles, then lowest
  mileage-weighted average risk, then shortest time. No Travel miles are ranked before Severe because
  No Travel is worse than Severe; the spec does not list it, so this is an assumption. The reason shown in the
  UI compares the best route with the worst on the first criterion that separates them.
- **Heatmap score** is a continuous 0-4 value per cell (0 for no weather, 1 where Moderate begins, 4 where No
  Travel begins, linear in between), the maximum over wind, rain and snow, with the load rules applied as
  floors. Continuous values make the heatmap smooth instead of banded.
- **Corridor masking.** Cells are only kept within 50 km of a route, on a grid capped at 300 cells (never finer
  than 0.1 degrees, about the forecast model's resolution). A full bounding box would waste most requests on
  weather nobody drives through.
- **Payload thinning.** Distances, checkpoints and ETAs are computed on the router's full geometry; only then is
  each route simplified with Douglas-Peucker (75 m tolerance, grown until it has at most 1,500 points) for
  drawing. A plan response drops from about 600 KB to well under 100 KB.
- **Heatmap performance.** The corridor GeoJSON is set once. Every hour's score is a property on the cell
  (`s0` to `s48`), and the slider only swaps the heatmap-weight expression, so there is no refetch, no data
  reload and no layer re-creation per step.
- **Times** are shown in the browser's local time zone. The API uses UTC.
- **Validation.** Load is 0-80,000 lb (US legal gross weight). The forecast covers 16 days, so a departure whose
  last checkpoint would fall beyond that is rejected with a clear message.

## API

| Endpoint | Purpose |
| --- | --- |
| `POST /api/plan` | `{origin, destination, departure, load_lb, interval_miles}` returns routes with summaries, thinned geometry and checkpoints. A place is a string or `{lat, lon, name?}`. |
| `POST /api/corridor` | `{routes: [[[lon, lat], ...]], departure, load_lb, hours}` returns `{times, spacing_deg, cells: [{lat, lon, score: [...]}]}` |
| `GET /api/geocode?q=` | Up to 5 place suggestions |

Errors are `{"error": "..."}` with status 400 for bad input and 502 when an upstream service fails.
Upstream calls retry once on a timeout or 5xx and responses are cached for 10 minutes.

## Tests

```
cd backend && .venv/Scripts/python -m pytest -q     # risk rules, sampling, scoring, API; no network
npm --prefix frontend test                          # formatting, form validation, GeoJSON and heatmap expressions
npm --prefix frontend run build
```

Backend tests run against recorded Valhalla, OSRM, Photon and Open-Meteo responses, so they never touch the
network.

## Deploy: Vercel (frontend and API in one project)

One Vercel project serves both, using Vercel Services (`vercel.json`). The `web` service builds the Vite
app in `frontend/`; the `api` service runs the Django app in `backend/` as a Python function, detected from
`manage.py` and `WSGI_APPLICATION`. Requests under `/api/` go to `api` with their full path, everything else to
`web`, which falls back to `index.html`. The browser calls relative `/api/...`, so everything is one origin and
production needs no CORS.

1. Push the repo to GitHub and import it in Vercel with the root directory at the repository root. Vercel reads
   the services from `vercel.json`; no build settings are needed in the dashboard.
2. Add the environment variables (Project Settings, Environment Variables):
   - `DJANGO_SECRET_KEY`: any long random string
   - `DEBUG`: `false`
   - `ALLOWED_HOSTS`: `.vercel.app` (add your own domain if you use one)
3. Deploy. `VITE_API_URL` is not needed in production; it is only a development override.

The function's `maxDuration` is 60 seconds; a cold plan takes roughly 5 to 15 seconds.

## Known limitations

- Routing, geocoding and weather use free public services with rate limits and variable latency. A burst of
  requests can return a 502; retrying a minute later works. The Valhalla public server also refuses trips over
  1,500 km, which then fall back to OSRM car routing.
- The forecast window is 16 days; the heatmap shows the 49 hours from the departure hour.
- The cache lives in each warm function instance's memory, so on Vercel it helps repeat requests only while an
  instance stays warm.
- Weather is the nearest forecast hour at a point, not an interpolation in time or space.
- Only the selected route's checkpoints are drawn, to keep the map readable; the other routes still show their
  line and summary.
