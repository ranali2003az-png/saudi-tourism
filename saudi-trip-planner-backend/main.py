"""
FastAPI wrapper around the ML engine (ml_engine.py -- extracted from the
Streamlit app's backend logic, unchanged). Exposes one endpoint the React
frontend already expects: POST /plan-trip.

Run with:  uvicorn main:app --reload --port 8000
"""

import math
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import ml_engine as eng

app = FastAPI(title="Saudi Tourism Planner API")

# Allow the Vite dev server (and any origin, for simplicity during
# development) to call this API from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

features_df = pd.read_pickle("tourism_app_data/features_df.pkl")

TRANSPORT_MAP = {
    "walking": "Walking",
    "public_transit": "Public Transit",
    "driving": "Driving / Taxi",
}


def _candidate_pool_size(days: int) -> int:
    """How many ranked places to pull before building the itinerary.
    Sized generously (not just days*3) so the day-by-day builder has
    enough attractions/restaurants/cafes on hand to keep every day
    varied instead of running out and leaving later days empty."""
    return max(15, days * 6)


class PlanTripRequest(BaseModel):
    city: str
    budget: float = 1000
    days: int = 3
    interests: list[str] = []
    transport_mode: str = "driving"
    require_accessibility: bool = False
    excluded_places: list[str] = []


class AssistantMessageRequest(BaseModel):
    message: str
    city: str
    budget: float = 1000
    days: int = 3
    hours_per_day: float = 8.0
    interests: list[str] = []
    transport_mode: str = "driving"
    require_accessibility: bool = False
    excluded_places: list[str] = []


def _clean(value):
    """Replace NaN/inf with None so the response is valid JSON."""
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value


def _place_to_json(row) -> dict:
    return {
        "name": row.get("name"),
        "category": row.get("place_type"),
        "latitude": _clean(row.get("latitude")),
        "longitude": _clean(row.get("longitude")),
        "estimated_cost": _clean(row.get("estimated_cost")),
        "rating": _clean(row.get("popularity_score")),
        "address": row.get("address"),
    }


def _stop_to_json(row) -> dict:
    return {
        "day": int(row.get("day")),
        "place": row.get("place"),
        "category": row.get("place_type"),
        "latitude": _clean(row.get("latitude")),
        "longitude": _clean(row.get("longitude")),
        "estimated_cost": _clean(row.get("estimated_cost")),
        "visit_duration_hours": _clean(row.get("visit_duration_hours")),
        "travel_time_hours": _clean(row.get("travel_time_hours")),
        "travel_distance_km": _clean(row.get("travel_distance_km")),
    }


@app.post("/plan-trip")
def plan_trip(req: PlanTripRequest):
    if req.city not in eng.CITIES:
        raise HTTPException(400, f"Unsupported city. Choose one of: {list(eng.CITIES)}")

    recommendations = eng.recommend_places(
        city=req.city,
        interests=req.interests,
        budget=req.budget,
        features_df=features_df,
        top_n=_candidate_pool_size(req.days),
        require_accessibility=req.require_accessibility,
        excluded_places=req.excluded_places,
    )

    if recommendations is None or recommendations.empty:
        return {"places": [], "itinerary": []}

    itinerary = eng.generate_itinerary(
        recommendations=recommendations,
        budget=req.budget,
        days=req.days,
        hours_per_day=8,
        city=req.city,
        require_accessibility=req.require_accessibility,
        transport_mode=TRANSPORT_MAP.get(req.transport_mode, "Driving / Taxi"),
    )

    return {
        "places": [_place_to_json(r) for _, r in recommendations.iterrows()],
        "itinerary": [_stop_to_json(r) for _, r in itinerary.iterrows()] if not itinerary.empty else [],
    }


@app.post("/assistant")
def assistant_message(req: AssistantMessageRequest):
    """Conversational assistant grounded in the current trip's actual
    recommendations/itinerary (never outside knowledge) -- wires up the
    chat logic that already existed in ml_engine.py (process_assistant_message
    / generate_llm_response / generate_assistant_response) but wasn't
    previously reachable from the API."""
    if req.city not in eng.CITIES:
        raise HTTPException(400, f"Unsupported city. Choose one of: {list(eng.CITIES)}")

    recommendations = eng.recommend_places(
        city=req.city,
        interests=req.interests,
        budget=req.budget,
        features_df=features_df,
        top_n=_candidate_pool_size(req.days),
        require_accessibility=req.require_accessibility,
        excluded_places=req.excluded_places,
    )

    itinerary = pd.DataFrame()
    if recommendations is not None and not recommendations.empty:
        itinerary = eng.generate_itinerary(
            recommendations=recommendations,
            budget=req.budget,
            days=req.days,
            hours_per_day=req.hours_per_day,
            city=req.city,
            require_accessibility=req.require_accessibility,
            transport_mode=TRANSPORT_MAP.get(req.transport_mode, "Driving / Taxi"),
        )

    state = {
        "city": req.city,
        "budget": req.budget,
        "hours_per_day": req.hours_per_day,
        "interests": req.interests,
        "excluded_places": req.excluded_places,
    }
    result = eng.process_assistant_message(
        req.message, state, recommendations=recommendations, itinerary=itinerary
    )

    context = eng.build_grounded_context(recommendations, itinerary, req.city)
    llm_text, _llm_error = eng.generate_llm_response(req.message, context, result["state"])
    reply = llm_text or eng.generate_assistant_response(
        req.message, result, recommendations=recommendations, itinerary=itinerary
    )

    return {
        "reply": reply,
        "intent": result["intent"],
        "excluded_place": result.get("excluded_place"),
        "state": result["state"],
    }


@app.get("/health")
def health():
    return {"status": "ok", "cities": list(eng.CITIES)}
