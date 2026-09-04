# Saudi Tourism Planner — Backend (FastAPI)

This wraps the same ML engine used in the Streamlit app (`ml_engine.py` is
an unedited extraction of its backend logic — recommend_places(),
generate_itinerary(), the Geoapify-backed places engine, opening-hours
hard constraints, etc.) behind one REST endpoint the React frontend calls.

## Run

```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Check it's alive: open `http://localhost:8000/health` — should list the
8 supported cities.

## Endpoint

```
POST /plan-trip
{
  "city": "Riyadh",
  "budget": 1000,
  "days": 3,
  "interests": ["Culture & Heritage", "Food"],
  "transport_mode": "driving",
  "require_accessibility": false
}
```

Returns `{ "places": [...], "itinerary": [...] }` — exactly the shape
`src/lib/api.ts` in the frontend project already expects, so no frontend
changes are needed.

## Notes

- Uses the same live Geoapify-backed places API as the Streamlit app,
  with the same local-dataset fallback for Riyadh/Abha/Dammam/Tabuk if
  that's unreachable or a city isn't covered.
- `streamlit` is a dependency only because `ml_engine.py` reuses its
  `@st.cache_data` / `@st.cache_resource` decorators for caching --
  it never launches a Streamlit server here.
