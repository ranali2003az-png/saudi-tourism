# Saudi Tourism Planner — Frontend

React 18 + TypeScript + Tailwind CSS + Vite. Three pages matching the flow:

```
Home → Preferences (destination, budget, days, interests, transport)
     → Generate Trip → Results (day tabs, attractions/restaurants/cafes, map)
     → Modify (back to Preferences, pre-filled)
```

## 1. Install

```bash
npm install
```

## 2. Point it at your FastAPI backend

```bash
cp .env.example .env
# edit .env: VITE_API_BASE=http://localhost:8000  (or your deployed URL)
```

## 3. Run

```bash
npm run dev
```

Opens at `http://localhost:5173`.

## Wiring this to your actual FastAPI + ML + Geoapify backend

Everything backend-related lives in **one file**: `src/lib/api.ts`.

It currently expects a single `POST /plan-trip` endpoint that takes:
```json
{ "city": "Riyadh", "budget": 1000, "days": 3, "interests": ["Food"], "transport_mode": "driving" }
```
and returns:
```json
{ "places": [ ... ], "itinerary": [ ... ] }
```

**If your FastAPI backend instead exposes separate endpoints** (e.g. one for
`recommend_places()` and one for `generate_itinerary()`), open
`src/lib/api.ts` and split `generateTrip()` into two `fetch` calls — the
`normalizePlace()` / `normalizeItinerary()` helpers already accept a few
common field-name variations (`name`/`place`, `latitude`/`lat`,
`place_type`/`category`, a flat itinerary list or one already grouped by
day), so you likely won't need to touch the pages or components at all.

## Map

The Results page map uses **Leaflet with free OpenStreetMap tiles** — no
API key needed. It plots whatever `latitude`/`longitude` your backend
returns per place.

## Notes

- The landing-page Saudi map (`src/components/SaudiMap.tsx`) is a
  **stylized decorative silhouette**, not real geodata — it's fine for the
  hero, but don't use it for anything needing accurate boundaries.
- Tailwind tokens (colors/fonts) are in `tailwind.config.js` if you want to
  adjust the palette.
