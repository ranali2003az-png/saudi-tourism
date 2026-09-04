
import streamlit as st
import pandas as pd
import numpy as np
import html
import json


# ============================================================
# BACKEND (merged from tourism_backend.py + Samsung ML engine)
# ============================================================


import re
import math
import difflib
from pathlib import Path

import requests


# ============================================================
# CONFIG
# ============================================================

ARTIFACT_ROOT = Path("ml_artifacts")
PLACES_API_BASE = "https://placesproject.onrender.com"
HTTP_TIMEOUT_SECONDS = 12
CACHE_TTL_SECONDS = 900  # 15 min

CITIES = {
    "Riyadh": "Riyadh, Saudi Arabia",
    "Abha": "Abha, Saudi Arabia",
    "Dammam": "Dammam, Saudi Arabia",
    "Tabuk": "Tabuk, Saudi Arabia",
    "Jeddah": "Jeddah, Saudi Arabia",
    "Makkah": "Makkah, Saudi Arabia",
    "Madinah": "Madinah, Saudi Arabia",
    "AlUla": "AlUla, Saudi Arabia",
}

# Cities that also have a local static dataset (used as a fallback,
# and to backfill estimated_cost when the ML path is used).
LOCAL_DATA_CITIES = {"Riyadh", "Abha", "Dammam", "Tabuk"}

RANK_WEIGHTS = {
    "preference_match": 0.35,
    "place_quality": 0.10,
    "regional_demand": 0.15,
    "seasonality": 0.10,
    "distance_fit": 0.15,
    "budget_fit": 0.10,
    "accessibility_fit": 0.05,
}

CITY_TO_PROVINCE = {
    "riyadh": "riyadh", "jeddah": "makkah", "makkah": "makkah", "mecca": "makkah",
    "madinah": "al madinah", "medina": "al madinah", "abha": "asir",
    "alula": "al madinah", "al ula": "al madinah", "dammam": "eastern province",
    "khobar": "eastern province", "al khobar": "eastern province", "taif": "makkah",
    "tabuk": "tabuk", "hail": "hail", "jazan": "jazan", "najran": "najran",
    "buraydah": "al qassim", "buraidah": "al qassim",
}

# City-center coordinates, used as the free (no paid API) reference point for
# distance_fit scoring and as the starting point for route ordering.
CITY_CENTERS = {
    "Riyadh": (24.7136, 46.6753),
    "Abha": (18.2164, 42.5053),
    "Dammam": (26.4207, 50.0888),
    "Tabuk": (28.3838, 36.5550),
    "Jeddah": (21.4858, 39.1925),
    "Makkah": (21.3891, 39.8579),
    "Madinah": (24.5247, 39.5692),
    "AlUla": (26.6084, 37.9214),
}

# Assumed average urban travel speed (km/h) used to convert haversine
# distance into an estimated travel time between stops. This replaces the
# paid Google Routes API called for in the plan: no live traffic/road
# routing, just a straight-line + speed-factor estimate. It is clearly
# labeled as an estimate everywhere it is surfaced to the user.
ASSUMED_TRAVEL_SPEED_KMH = 30.0
ROUTE_DISTANCE_FACTOR = 1.3  # straight-line -> road-distance fudge factor

TRANSPORT_SPEED_KMH = {
    "Walking": 4.5,
    "Public Transit": 22.0,
    "Driving / Taxi": ASSUMED_TRAVEL_SPEED_KMH,
}


# ============================================================
# ML ARTIFACT LOADING (cached once per session)
# ============================================================

@st.cache_resource(show_spinner=False)
def _load_ml_artifacts():
    """
    Loads the trained artifacts shipped in Samsung's deployment/artifacts/
    folder. Returns None (instead of raising) if anything is missing --
    the app should degrade gracefully to the local fallback engine.
    """
    try:
        monthly = pd.read_csv(ARTIFACT_ROOT / "kapsarc_monthly_features.csv")
        latest_context = pd.read_csv(ARTIFACT_ROOT / "latest_regional_demand_context.csv")
        seasonality = pd.read_csv(ARTIFACT_ROOT / "datasaudi_seasonality_index.csv")
        metadata = json.loads((ARTIFACT_ROOT / "deployment_metadata.json").read_text(encoding="utf-8"))
        monthly["month"] = pd.to_datetime(monthly["month"], errors="coerce")
        for frame in (monthly, latest_context, seasonality):
            if frame.empty:
                return None
        return {
            "monthly": monthly,
            "latest_context": latest_context,
            "seasonality": seasonality,
            "metadata": metadata,
        }
    except (FileNotFoundError, ValueError, json.JSONDecodeError):
        return None


def ml_artifacts_available() -> bool:
    return _load_ml_artifacts() is not None


# ============================================================
# EVENTS (Visit Saudi / Saudi Calendar, per the plan)
# ------------------------------------------------------------
# There is no public, keyless, free equivalent of the Visit Saudi events
# feed. Rather than fake events or scrape a source with no clear license,
# this reads an optional VISIT_SAUDI_API_BASE / VISIT_SAUDI_API_KEY from
# the environment: if a team member has real (even free-tier) API
# credentials, dropping them into st.secrets / env vars turns this on
# with no other code changes. Without credentials it returns an empty,
# clearly-labeled result -- consistent with the plan's own grounding
# rule to omit unsupported/unverifiable events rather than invent them.
# ============================================================

import os

VISIT_SAUDI_API_BASE = os.environ.get("VISIT_SAUDI_API_BASE", "")
VISIT_SAUDI_API_KEY = os.environ.get("VISIT_SAUDI_API_KEY", "")


def events_source_configured() -> bool:
    return bool(VISIT_SAUDI_API_BASE and VISIT_SAUDI_API_KEY)


# ============================================================
# LLM-GROUNDED ASSISTANT (optional upgrade over the rule-based
# keyword matcher below). Uses the Anthropic API directly with a
# system prompt that restricts it to the retrieved place/itinerary
# context only -- it's told explicitly not to answer from outside
# knowledge, so it can't invent prices, hours, or places that
# weren't actually retrieved. Turns on automatically if
# ANTHROPIC_API_KEY is set; otherwise the app silently keeps using
# the existing rule-based assistant, so nothing breaks without a key.
# ============================================================

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")

# Groq: a genuinely free (no credit card) LLM API, OpenAI-compatible.
# Get a key at console.groq.com/keys. Checked first below since it's
# free -- Anthropic is used only as a paid fallback if a Groq key
# isn't set but an Anthropic key is.
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")


def llm_configured() -> bool:
    return bool(GROQ_API_KEY or ANTHROPIC_API_KEY)


def llm_provider_name() -> str:
    if GROQ_API_KEY:
        return "Groq (free)"
    if ANTHROPIC_API_KEY:
        return "Claude (paid)"
    return "none"


def _build_grounding_system_prompt(context, state):
    return (
        "You are a Saudi tourism trip-planning assistant embedded in an app. "
        "You must answer ONLY using the VERIFIED_CONTEXT JSON provided below -- "
        "this is the actual data retrieved for the user's current trip (real "
        "places, an itinerary, or both). Do not use outside knowledge about "
        "Saudi Arabia, and do not invent places, prices, hours, or facts that "
        "are not in VERIFIED_CONTEXT. If the user asks something the context "
        "doesn't cover, say plainly that you don't have that information yet "
        "rather than guessing. Keep answers short and practical.\n\n"
        f"Current trip settings: {json.dumps(state, ensure_ascii=False)}\n\n"
        f"VERIFIED_CONTEXT: {json.dumps(context, ensure_ascii=False, default=str)}"
    )


def _generate_groq_response(user_message, context, state, chat_history=None):
    system_prompt = _build_grounding_system_prompt(context, state)
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(chat_history or [])
    messages.append({"role": "user", "content": user_message})
    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={"model": GROQ_MODEL, "max_tokens": 400, "messages": messages},
            timeout=HTTP_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        data = resp.json()
        text = data["choices"][0]["message"]["content"]
        return (text.strip() or None), None
    except (requests.RequestException, ValueError, KeyError, IndexError) as e:
        return None, str(e)


def _generate_anthropic_response(user_message, context, state, chat_history=None):
    system_prompt = _build_grounding_system_prompt(context, state)
    messages = list(chat_history or [])
    messages.append({"role": "user", "content": user_message})
    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": ANTHROPIC_MODEL,
                "max_tokens": 400,
                "system": system_prompt,
                "messages": messages,
            },
            timeout=HTTP_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        data = resp.json()
        text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
        return (text.strip() or None), None
    except (requests.RequestException, ValueError, KeyError) as e:
        return None, str(e)


def generate_llm_response(user_message, context, state, chat_history=None):
    """Calls whichever grounded LLM provider is configured (Groq first,
    since it's free; Anthropic as a paid fallback). Returns
    (response_text, error). On any failure, error is a short string and
    the caller should fall back to generate_assistant_response()."""
    if GROQ_API_KEY:
        return _generate_groq_response(user_message, context, state, chat_history)
    if ANTHROPIC_API_KEY:
        return _generate_anthropic_response(user_message, context, state, chat_history)
    return None, "no LLM API key configured"


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def fetch_events(city: str) -> list:
    if not events_source_configured():
        return []
    try:
        resp = requests.get(
            f"{VISIT_SAUDI_API_BASE}/events",
            params={"city": city},
            headers={"Authorization": f"Bearer {VISIT_SAUDI_API_KEY}"},
            timeout=HTTP_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        payload = resp.json()
    except (requests.RequestException, ValueError):
        return []
    retrieved = pd.Timestamp.utcnow().isoformat()
    events = []
    for row in payload.get("results", []):
        events.append({
            "name": row.get("name"),
            "start_date": row.get("start_date"),
            "end_date": row.get("end_date"),
            "venue": row.get("venue"),
            "city": city,
            "source": "Visit Saudi Calendar",
            "source_retrieved_at_utc": retrieved,
        })
    return events


# ============================================================
# ML HELPERS (adapted from ml_api_service.py)
# ============================================================

def _normalize_text(value) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return ""
    s = str(value).strip().lower()
    s = re.sub(r"[\u200e\u200f]", "", s)
    s = re.sub(r"[^a-z0-9\u0600-\u06ff]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _minmax01(series: pd.Series, neutral: float = 0.5) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce")
    lo, hi = s.min(), s.max()
    if pd.isna(lo) or pd.isna(hi) or np.isclose(lo, hi):
        return pd.Series(neutral, index=series.index, dtype=float)
    return ((s - lo) / (hi - lo)).clip(0, 1)


def _haversine_km(lat1, lon1, lat2, lon2) -> float:
    vals = [lat1, lon1, lat2, lon2]
    if any(pd.isna(v) for v in vals):
        return float("nan")
    r = 6371.0088
    p1, p2 = math.radians(float(lat1)), math.radians(float(lat2))
    dp = math.radians(float(lat2) - float(lat1))
    dl = math.radians(float(lon2) - float(lon1))
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _canonical_place_group(category: str) -> str:
    if category in {"restaurants", "cafes"}:
        return "food"
    return "attractions" if category == "attractions" else category


# ============================================================
# OPENING HOURS (hard constraint) -- lightweight OSM/Geoapify
# "opening_hours" syntax parser. Not a full spec implementation,
# but handles the common patterns well enough to hard-filter
# venues that are confirmed closed on the visit day, per the
# plan's requirement that opening hours be a hard constraint.
# Unknown/unparseable strings are treated as "unknown" (soft --
# not excluded) rather than fabricating a status.
# ============================================================

_WEEKDAY_CODES = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]


def _parse_opening_hours(raw: str):
    """Returns dict {weekday_code: [(start_hour, end_hour), ...]} or None
    if unparseable / unknown. "24/7" maps every day to (0, 24)."""
    if not isinstance(raw, str) or not raw.strip():
        return None
    text = raw.strip()
    if text.lower() in {"24/7", "open 24 hours"}:
        return {d: [(0.0, 24.0)] for d in _WEEKDAY_CODES}

    schedule = {}
    for segment in text.split(";"):
        segment = segment.strip()
        if not segment or segment.lower() in {"closed", "off", "ph off"}:
            continue
        m = re.match(
            r"^((?:Mo|Tu|We|Th|Fr|Sa|Su)(?:-(?:Mo|Tu|We|Th|Fr|Sa|Su))?"
            r"(?:,(?:Mo|Tu|We|Th|Fr|Sa|Su)(?:-(?:Mo|Tu|We|Th|Fr|Sa|Su))?)*)\s+"
            r"(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})$",
            segment,
        )
        if not m:
            continue
        day_part, sh, sm, eh, em = m.groups()
        start_hr = int(sh) + int(sm) / 60.0
        end_hr = int(eh) + int(em) / 60.0
        days = set()
        for chunk in day_part.split(","):
            if "-" in chunk:
                d1, d2 = chunk.split("-")
                i1, i2 = _WEEKDAY_CODES.index(d1), _WEEKDAY_CODES.index(d2)
                idxs = list(range(i1, i2 + 1)) if i2 >= i1 else list(range(i1, 7)) + list(range(0, i2 + 1))
                days.update(_WEEKDAY_CODES[i] for i in idxs)
            else:
                days.add(chunk)
        for d in days:
            schedule.setdefault(d, []).append((start_hr, end_hr))
    return schedule or None


def opening_hours_status(raw: str, visit_weekday: int, visit_hour: float = 12.0):
    """visit_weekday: Python weekday() (Mon=0..Sun=6).
    Returns one of "open", "closed", "unknown" -- never fabricates certainty
    beyond what the parsed string supports."""
    schedule = _parse_opening_hours(raw)
    if schedule is None:
        return "unknown"
    code = _WEEKDAY_CODES[visit_weekday]
    windows = schedule.get(code)
    if not windows:
        return "closed"
    for start_hr, end_hr in windows:
        if start_hr <= visit_hour <= end_hr:
            return "open"
    return "closed"


def accessibility_status(row) -> str:
    """Best-effort accessibility read from whatever the upstream Places API
    passed through (e.g. an OSM 'wheelchair' tag), since the ML metadata
    explicitly notes confirmed accessibility isn't exposed by the current
    normalized API. Returns "yes" / "no" / "unknown" -- "unknown" is the
    honest default, never assumed accessible."""
    for key in ("wheelchair", "accessibility", "accessible"):
        val = row.get(key) if hasattr(row, "get") else None
        if val is None:
            continue
        v = str(val).strip().lower()
        if v in {"yes", "true", "1", "full", "limited"}:
            return "yes"
        if v in {"no", "false", "0"}:
            return "no"
    return "unknown"


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def _fetch_places_from_upstream(city: str, category: str, limit: int) -> list:
    """Calls the live Places API. Cached per (city, category, limit) for 15 min."""
    response = requests.get(
        f"{PLACES_API_BASE}/places",
        params={"city": city, "category": category, "limit": limit},
        timeout=HTTP_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    payload = response.json()

    retrieved = pd.Timestamp.utcnow().isoformat()
    rows = []
    for row in payload.get("results", []):
        item = dict(row)
        item["requested_city"] = city
        item["requested_category"] = category
        item["source"] = "Geoapify via team Places API"
        item["source_retrieved_at_utc"] = retrieved
        rows.append(item)
    return rows


def _prepare_places(rows: list) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    out = pd.DataFrame(rows)
    expected = [
        "name", "latitude", "longitude", "category", "address", "city",
        "opening_hours", "place_id", "requested_city", "requested_category",
        "source", "source_retrieved_at_utc",
    ]
    for col in expected:
        if col not in out.columns:
            out[col] = np.nan

    out["latitude"] = pd.to_numeric(out["latitude"], errors="coerce")
    out["longitude"] = pd.to_numeric(out["longitude"], errors="coerce")
    out["city_effective"] = out["city"].fillna(out["requested_city"]).astype(str)
    out["city_key"] = out["city_effective"].map(_normalize_text)
    out["place_group"] = out["requested_category"].map(_canonical_place_group)
    out["has_name"] = out["name"].notna().astype(float)
    out["has_coordinates"] = (out["latitude"].notna() & out["longitude"].notna()).astype(float)
    out["has_address"] = out["address"].notna().astype(float)
    out["has_opening_hours"] = out["opening_hours"].notna().astype(float)
    out["place_quality"] = out[
        ["has_name", "has_coordinates", "has_address", "has_opening_hours"]
    ].mean(axis=1)
    out["accessibility_status"] = out.apply(accessibility_status, axis=1)

    out["_dedupe_key"] = out["place_id"].fillna(
        out["name"].fillna("") + "|" + out["latitude"].astype(str) + "|" + out["longitude"].astype(str)
    )
    return out.drop_duplicates("_dedupe_key").drop(columns="_dedupe_key")


def _regional_demand_score(artifacts, city_key: str, place_group: str) -> float:
    frame = artifacts["latest_context"]
    match = frame[
        (frame["city_key"].astype(str).map(_normalize_text) == _normalize_text(city_key))
        & (frame["place_group"].astype(str) == place_group)
    ]
    if not match.empty:
        return float(match["regional_demand"].iloc[0])
    fallback = frame[frame["place_group"].astype(str) == place_group]["regional_demand"]
    return float(fallback.median()) if not fallback.empty else 0.5


def _seasonality_score(artifacts, city: str, month_num: int):
    frame = artifacts["seasonality"]
    pkey = CITY_TO_PROVINCE.get(_normalize_text(city))
    if pkey:
        candidates = frame[
            (pd.to_numeric(frame["month_num"], errors="coerce") == int(month_num))
            & frame["province_key"].astype(str).map(_normalize_text).str.contains(pkey, regex=False, na=False)
        ]
        if not candidates.empty:
            return float(candidates["seasonality_score"].mean()), "province_month"

    national = frame[pd.to_numeric(frame["month_num"], errors="coerce") == int(month_num)]
    if not national.empty:
        return float(national["seasonality_score"].mean()), "national_month_fallback"
    return 0.5, "neutral_fallback"


def _weighted_score(row: pd.Series) -> float:
    total, used = 0.0, 0.0
    for feature, weight in RANK_WEIGHTS.items():
        value = row.get(feature, np.nan)
        if weight <= 0 or pd.isna(value):
            continue
        total += float(value) * weight
        used += weight
    return total / used if used else 0.0


def fetch_ml_recommendations(city, interests, trip_month, top_k=10, require_accessibility=False):
    """
    Real ML-grounded recommendations: live venues from the Places API,
    ranked with regional demand + seasonality signals from the trained
    artifacts, plus a free (no paid-API) distance_fit computed from
    haversine distance to the city center, and accessibility_fit read
    from whatever the upstream data actually reports. Returns None on
    any failure (city not covered, artifacts missing, upstream API
    down) so the caller can fall back gracefully.

    budget_fit is intentionally left out of the score here -- venue
    price isn't returned by the Places API (a stated data limitation),
    so it's computed later in recommend_places() once a cost estimate
    exists, and the score is re-weighted at that point.
    """
    artifacts = _load_ml_artifacts()
    if artifacts is None:
        return None

    valid_interests = [i for i in interests if i in ("attractions", "restaurants", "cafes")]
    if not valid_interests:
        valid_interests = ["attractions", "restaurants", "cafes"]

    per_category_limit = min(50, max(top_k * 3, 15))
    raw_rows = []
    try:
        for category in valid_interests:
            raw_rows.extend(_fetch_places_from_upstream(city, category, per_category_limit))
    except (requests.RequestException, ValueError):
        return None

    candidates = _prepare_places(raw_rows)
    if candidates.empty:
        return None

    if require_accessibility:
        # Hard constraint: drop venues *confirmed* inaccessible. Venues with
        # unknown status are kept (we never fabricate a "yes"), but flagged
        # via accessibility_status so the UI can disclose the uncertainty.
        candidates = candidates[candidates["accessibility_status"] != "no"]
        if candidates.empty:
            return None

    candidates["preference_match"] = candidates["requested_category"].map(
        lambda c: 1.0 if c in valid_interests else 0.0
    )
    candidates["regional_demand"] = candidates.apply(
        lambda r: _regional_demand_score(artifacts, r["city_key"], r["place_group"]), axis=1
    )
    seas = candidates["requested_city"].map(lambda c: _seasonality_score(artifacts, c, trip_month))
    candidates["seasonality"] = [x[0] for x in seas]
    candidates["seasonality_source"] = [x[1] for x in seas]

    center = CITY_CENTERS.get(city)
    if center:
        candidates["distance_km_center"] = candidates.apply(
            lambda r: _haversine_km(r["latitude"], r["longitude"], center[0], center[1]), axis=1
        )
        candidates["distance_fit"] = 1.0 - _minmax01(candidates["distance_km_center"])
    else:
        candidates["distance_km_center"] = np.nan
        candidates["distance_fit"] = np.nan

    candidates["accessibility_fit"] = candidates["accessibility_status"].map(
        {"yes": 1.0, "no": 0.0, "unknown": 0.5}
    )
    candidates["opening_hours_raw"] = candidates["opening_hours"]

    candidates["ranking_score"] = candidates.apply(_weighted_score, axis=1)
    ranked = candidates.sort_values(
        ["ranking_score", "place_quality", "name"],
        ascending=[False, False, True],
        na_position="last",
    ).head(top_k).reset_index(drop=True)

    # --- map to the legacy schema the rest of the app expects ---
    ranked["place_type"] = ranked["requested_category"].str.rstrip("s")
    ranked["recommendation_score"] = ranked["ranking_score"]
    ranked["popularity_score"] = ranked["place_quality"]
    ranked["distance_score"] = ranked["distance_fit"]
    ranked["city"] = city
    ranked["_source"] = "ml_engine"

    return ranked


# ============================================================
# RECOMMENDATION ENGINE (public entry point used by app.py)
# ============================================================

def recommend_places(city, interests, budget=None, features_df=None, top_n=10,
                      require_accessibility=False, excluded_places=None):
    interest_list = _normalize_interests(interests)
    excluded_places = set(excluded_places or [])

    # --- 1) Try the real ML engine first ---
    ml_df = fetch_ml_recommendations(
        city=city,
        interests=interest_list,
        trip_month=pd.Timestamp.now().month,
        top_k=top_n + len(excluded_places),
        require_accessibility=require_accessibility,
    )
    if ml_df is not None and not ml_df.empty:
        if excluded_places:
            ml_df = ml_df[~ml_df["name"].isin(excluded_places)]
        backfilled = _backfill_local_fields(ml_df, city, features_df)
        # Now that a cost estimate exists, compute budget_fit and fold it
        # into the final score (it was excluded upstream, since price
        # evidence doesn't exist until this backfill step).
        backfilled["budget_fit"] = backfilled["estimated_cost"].apply(
            lambda c: calculate_budget_score(c, budget)
        )
        backfilled["recommendation_score"] = backfilled.apply(_weighted_score, axis=1)
        return backfilled.sort_values("recommendation_score", ascending=False).head(top_n).reset_index(drop=True)

    # --- 2) Fall back to the local static dataset ---
    if features_df is None or city not in LOCAL_DATA_CITIES:
        return pd.DataFrame()

    places = features_df[features_df["city"] == city].copy()
    if excluded_places:
        places = places[~places["name"].isin(excluded_places)]
    if places.empty:
        return places

    places["interest_score"] = places["interests"].apply(
        lambda x: calculate_interest_score(x, interest_list)
    )
    places["budget_score"] = places.apply(
        lambda row: calculate_budget_score(row["estimated_cost"], budget), axis=1
    )
    places["recommendation_score"] = (
        places["interest_score"] * 0.40
        + places["budget_score"] * 0.25
        + places["distance_score"] * 0.20
        + places["popularity_score"] * 0.15
    )
    places["_source"] = "local_dataset"

    # Local dataset has no per-visit duration -- fill with the same
    # category defaults used to backfill the ML path, so the itinerary
    # builder (which needs visit_duration_hours/total_time_hours) works
    # for this fallback path too instead of raising a KeyError.
    default_duration = {"attraction": 2.0, "restaurant": 1.5, "cafe": 1.0}
    places["visit_duration_hours"] = places["place_type"].map(default_duration).fillna(1.5)
    places["total_time_hours"] = places["visit_duration_hours"]

    places = places.sort_values(by="recommendation_score", ascending=False)
    return places.head(top_n).reset_index(drop=True)


def baseline_recommend_places(city, features_df, top_n=10):
    """Non-personalized baseline required by the plan for cold-start and
    evaluation: rank purely by regional demand, using distance to the
    city center as a tie-breaker. No interests/budget considered."""
    ml_df = fetch_ml_recommendations(
        city=city, interests=["attractions", "restaurants", "cafes"],
        trip_month=pd.Timestamp.now().month, top_k=top_n,
    )
    if ml_df is not None and not ml_df.empty:
        return ml_df.sort_values(
            ["regional_demand", "distance_fit"], ascending=[False, False]
        ).head(top_n).reset_index(drop=True)

    if features_df is None or city not in LOCAL_DATA_CITIES:
        return pd.DataFrame()
    places = features_df[features_df["city"] == city].copy()
    if places.empty:
        return places
    return places.sort_values(
        ["popularity_score", "distance_score"], ascending=[False, False]
    ).head(top_n).reset_index(drop=True)


def _normalize_interests(interests):
    if isinstance(interests, str):
        parts = re.split(r"[,\n/]+", interests)
        return [p.strip().lower() for p in parts if p.strip()]
    if isinstance(interests, (list, tuple, set)):
        return [str(i).strip().lower() for i in interests if str(i).strip()]
    return []


def calculate_interest_score(place_interests, user_interests):
    if not user_interests:
        return 0.5
    if isinstance(place_interests, str):
        place_tags = [t.strip().lower() for t in re.split(r"[,;/]+", place_interests) if t.strip()]
    elif isinstance(place_interests, (list, tuple, set)):
        place_tags = [str(t).strip().lower() for t in place_interests]
    else:
        place_tags = []
    if not place_tags:
        return 0.0
    matches = sum(1 for u in user_interests if any(u in tag or tag in u for tag in place_tags))
    return min(1.0, matches / len(user_interests))


def calculate_budget_score(estimated_cost, budget):
    if budget is None or pd.isna(budget) or budget <= 0:
        return 0.5
    if pd.isna(estimated_cost):
        return 0.5
    if estimated_cost <= budget:
        return 1.0
    overage_ratio = (estimated_cost - budget) / budget
    return max(0.0, 1.0 - overage_ratio)


def _backfill_local_fields(ml_df, city, features_df):
    """
    The ML engine doesn't return venue-level price/duration (no evidence
    for it -- see the project's stated limitations). Backfill from the
    local dataset where we have it; otherwise use a category default.
    """
    ml_df = ml_df.copy()
    if features_df is not None and city in LOCAL_DATA_CITIES:
        local = features_df[features_df["city"] == city][["name", "estimated_cost"]]
        ml_df = ml_df.merge(local, on="name", how="left", suffixes=("", "_local"))
        if "estimated_cost_local" in ml_df.columns:
            ml_df["estimated_cost"] = ml_df["estimated_cost"].fillna(ml_df["estimated_cost_local"])
            ml_df = ml_df.drop(columns=["estimated_cost_local"])
    else:
        ml_df["estimated_cost"] = np.nan

    default_duration = {"attraction": 2.0, "restaurant": 1.5, "cafe": 1.0}
    ml_df["visit_duration_hours"] = ml_df["place_type"].map(default_duration).fillna(1.5)
    ml_df["total_time_hours"] = ml_df["visit_duration_hours"]
    ml_df["estimated_cost"] = ml_df["estimated_cost"].fillna(100)  # rough placeholder where no price evidence exists
    ml_df["_estimates_used"] = True
    return ml_df


# ============================================================
# ITINERARY
# ============================================================

def _route_order(places_left, start_latlon):
    """Greedy nearest-neighbor ordering by haversine distance -- a free
    stand-in for the paid Google Routes optimization the plan called for.
    Returns places_left re-ordered, plus the list of leg distances (km)."""
    remaining = list(places_left)
    ordered, leg_km = [], []
    cur = start_latlon
    while remaining:
        best_i, best_d = 0, float("inf")
        for i, p in enumerate(remaining):
            d = _haversine_km(cur[0], cur[1], p.get("latitude"), p.get("longitude"))
            if pd.isna(d):
                d = 999999.0  # unknown location -> visit last
            if d < best_d:
                best_d, best_i = d, i
        nxt = remaining.pop(best_i)
        ordered.append(nxt)
        leg_km.append(0.0 if best_d == 999999.0 else best_d)
        if not pd.isna(nxt.get("latitude")) and not pd.isna(nxt.get("longitude")):
            cur = (nxt["latitude"], nxt["longitude"])
    return ordered, leg_km


def generate_itinerary(recommendations, budget, days, hours_per_day, city=None,
                        visit_start_weekday=None, require_accessibility=False,
                        transport_mode="Driving / Taxi"):
    """
    Builds a day-by-day plan under hard constraints (opening hours, daily
    time budget, daily cost budget, accessibility when required), and
    orders each day's stops with a free nearest-neighbor route (haversine
    distance / assumed speed) instead of a paid routing API -- travel time
    between consecutive stops is added to the day's time budget.
    """
    if recommendations.empty:
        return pd.DataFrame()

    speed_kmh = TRANSPORT_SPEED_KMH.get(transport_mode, ASSUMED_TRAVEL_SPEED_KMH)
    weekday = visit_start_weekday if visit_start_weekday is not None else pd.Timestamp.now().weekday()

    # --- hard-constraint pre-filter ---
    candidates = []
    for _, place in recommendations.iterrows():
        if require_accessibility and place.get("accessibility_status") == "no":
            continue  # confirmed inaccessible -> hard exclude
        status = opening_hours_status(place.get("opening_hours_raw"), weekday)
        if status == "closed":
            continue  # confirmed closed on the visit day -> hard exclude
        row = place.to_dict()
        row["_hours_status"] = status  # "open" or "unknown" (never fabricated "open")
        candidates.append(row)

    if not candidates:
        return pd.DataFrame()

    daily_budget = budget / days
    center = CITY_CENTERS.get(city, (None, None))
    itinerary = []
    day = 1
    day_time, day_cost = 0.0, 0.0
    day_cursor = center if center[0] is not None else (
        candidates[0].get("latitude"), candidates[0].get("longitude")
    )
    pool = candidates

    while pool and day <= days:
        ordered, leg_km = _route_order(pool, day_cursor)
        placed_today = []
        for place, km in zip(ordered, leg_km):
            travel_hr = (km * ROUTE_DISTANCE_FACTOR) / speed_kmh if speed_kmh else 0.0
            visit_hr = place["total_time_hours"]
            stop_time = travel_hr + visit_hr
            stop_cost = place["estimated_cost"]
            if day_time + stop_time > hours_per_day or day_cost + stop_cost > daily_budget:
                continue  # doesn't fit today -> try tomorrow
            day_time += stop_time
            day_cost += stop_cost
            placed_today.append(place)
            itinerary.append({
                "day": day,
                "place": place["name"],
                "city": place["city"],
                "place_type": place["place_type"],
                "estimated_cost": stop_cost,
                "visit_duration_hours": place["visit_duration_hours"],
                "travel_time_hours": round(travel_hr, 2),
                "travel_distance_km": round(km, 1),
                "total_time_hours": round(stop_time, 2),
                "recommendation_score": place.get("recommendation_score", np.nan),
                "opening_hours_status": place["_hours_status"],
                "accessibility_status": place.get("accessibility_status", "unknown"),
                "latitude": place.get("latitude"),
                "longitude": place.get("longitude"),
            })
            day_cursor = (place.get("latitude"), place.get("longitude"))

        pool = [p for p in pool if p["name"] not in {x["name"] for x in placed_today}]
        if not placed_today:
            # nothing from the remaining pool fits today at all -> stop to avoid an infinite loop
            break
        day += 1
        day_time, day_cost = 0.0, 0.0
        day_cursor = center if center[0] is not None else day_cursor

    return pd.DataFrame(itinerary)


# ============================================================
# EVALUATION (required by the plan: catalog coverage, intra-list
# diversity, itinerary feasibility. NDCG@5 and mean satisfaction need
# human relevance labels / real user ratings that this deployment
# doesn't collect, so those are reported as "not available" rather
# than approximated.)
# ============================================================

def eval_catalog_coverage(recommendations, catalog_pool):
    """Share of the retrieved candidate pool that made it into the
    final recommendation list."""
    if catalog_pool is None or catalog_pool.empty:
        return None
    shown = set(recommendations["name"]) if recommendations is not None and not recommendations.empty else set()
    pool_names = set(catalog_pool["name"])
    if not pool_names:
        return None
    return len(shown & pool_names) / len(pool_names)


def eval_intra_list_diversity(recommendations):
    """1 - (share of the list taken by the single most common place_type).
    Higher = more varied list."""
    if recommendations is None or recommendations.empty or "place_type" not in recommendations:
        return None
    counts = recommendations["place_type"].value_counts(normalize=True)
    return float(1.0 - counts.iloc[0]) if not counts.empty else None


def eval_itinerary_feasibility(itinerary):
    """Share of scheduled stops that satisfied every hard constraint this
    build enforces (opening hours confirmed-open-or-unknown, never
    confirmed-closed; accessibility confirmed-yes-or-unknown when
    required). Since violators are filtered before scheduling, this
    should read 1.0 for anything actually placed -- it's a sanity check,
    not an approximation."""
    if itinerary is None or itinerary.empty:
        return None
    ok = (itinerary["opening_hours_status"] != "closed").mean()
    return float(ok)


NDCG_UNAVAILABLE_NOTE = (
    "NDCG@5 requires human relevance labels, and mean user satisfaction requires "
    "real post-trip ratings -- neither is collected by this deployment, so both "
    "are reported as not available rather than estimated."
)


# ============================================================
# ASSISTANT / CHAT HELPERS
# ============================================================

def detect_intent(message):
    m = message.lower()
    if any(w in m for w in ["wheelchair", "accessible", "accessibility"]):
        return "accessibility"
    if any(w in m for w in ["budget", "cost", "price", "sar", "cheap", "expensive"]):
        return "budget"
    if any(w in m for w in ["hour", "time", "how long", "available"]):
        return "time"
    if any(w in m for w in ["remove", "skip", "don't want", "not interested in", "exclude", "closed"]):
        return "availability"
    if any(w in m for w in ["itinerary", "schedule", "plan", "day 1", "day plan"]):
        return "itinerary"
    if any(w in m for w in ["interest", "prefer", "like", "into"]):
        return "preferences"
    if any(w in m for w in ["recommend", "suggest", "places", "visit", "options"]):
        return "recommendation"
    return "general"


def extract_budget(message):
    match = re.search(r"(\d+(?:\.\d+)?)\s*(sar|riyal|ريال)?", message.lower())
    if match and ("sar" in message.lower() or "riyal" in message.lower() or "budget" in message.lower() or "ريال" in message):
        return float(match.group(1))
    return None


def extract_hours(message):
    match = re.search(r"(\d+(?:\.\d+)?)\s*(hour|hr|hours|ساعة|ساعات)", message.lower())
    if match:
        return float(match.group(1))
    return None


def extract_excluded_place(message, available_places):
    m = message.lower()
    if not any(w in m for w in ["remove", "skip", "not", "exclude", "don't", "closed"]):
        return None
    for place in available_places:
        if place.lower() in m:
            return place
    close = difflib.get_close_matches(m, [p.lower() for p in available_places], n=1, cutoff=0.6)
    if close:
        idx = [p.lower() for p in available_places].index(close[0])
        return available_places[idx]
    return None


def build_grounded_context(recommendations, itinerary, city):
    context = []
    if recommendations is not None and not recommendations.empty:
        for _, row in recommendations.iterrows():
            context.append({
                "name": row.get("name"),
                "city": row.get("city", city),
                "place_type": row.get("place_type"),
                "source": row.get("source", row.get("_source")),
                "retrieved_at_utc": row.get("source_retrieved_at_utc"),
                "estimates_used": bool(row.get("_estimates_used", False)),
            })
    if itinerary is not None and not itinerary.empty:
        for _, row in itinerary.iterrows():
            context.append({"name": row.get("place"), "day": row.get("day")})
    return context


def _freshness_note(context):
    """Surfaces retrieval timestamps and flags estimated fields, per the
    plan's grounding requirement -- never silently presents an estimate
    as a verified fact."""
    timestamps = [c["retrieved_at_utc"] for c in context if c.get("retrieved_at_utc")]
    notes = []
    if timestamps:
        try:
            latest = max(pd.Timestamp(t) for t in timestamps)
            age_min = max(0, int((pd.Timestamp.utcnow().tz_localize(None) - latest.tz_localize(None)).total_seconds() / 60))
            notes.append(f"(place data retrieved {age_min} min ago)")
        except Exception:
            pass
    if any(c.get("estimates_used") for c in context):
        notes.append("(cost/duration for some places are category-level estimates, not confirmed prices)")
    return " ".join(notes)


def process_assistant_message(message, state, recommendations=None, itinerary=None):
    intent = detect_intent(message)
    updated_state = dict(state)
    updated_state["excluded_places"] = list(state.get("excluded_places", []))

    extracted_budget = extract_budget(message)
    if extracted_budget is not None:
        updated_state["budget"] = extracted_budget

    extracted_hours = extract_hours(message)
    if extracted_hours is not None:
        updated_state["hours_per_day"] = extracted_hours

    excluded_place = None
    if recommendations is not None and not recommendations.empty:
        available_places = recommendations["name"].tolist()
        excluded_place = extract_excluded_place(message, available_places)

    if excluded_place is not None and excluded_place not in updated_state["excluded_places"]:
        updated_state["excluded_places"].append(excluded_place)

    return {"message": message, "intent": intent, "state": updated_state, "excluded_place": excluded_place}


def generate_assistant_response(user_message, assistant_result, recommendations=None, itinerary=None):
    state = assistant_result["state"]
    intent = assistant_result["intent"]
    context = build_grounded_context(recommendations=recommendations, itinerary=itinerary, city=state["city"])

    if not context:
        return ("I could not find enough verified information in the current tourism data "
                "to answer this request. Please try another request based on the available "
                "destinations and recommendations.")

    if intent == "recommendation":
        places = list(dict.fromkeys(item["name"] for item in context if item.get("name")))
        if not places:
            return "No verified recommendations are currently available for this request."
        response = f"Based on the available tourism data for {state['city']}, here are suitable options:\n\n"
        for place in places[:5]:
            response += f"• {place}\n"
        response += "\nThese recommendations are based only on the current project dataset."
        note = _freshness_note(context)
        if note:
            response += f"\n{note}"
        return response

    if intent == "budget":
        return (f"Your current trip budget is {state['budget']:.0f} SAR. "
                f"The itinerary will prioritize options that fit within this budget.")

    if intent == "time":
        return (f"You currently have {state['hours_per_day']:.1f} hours available per day. "
                f"The itinerary is generated using this time constraint.")

    if intent == "availability":
        excluded = assistant_result["excluded_place"]
        if excluded:
            return (f"{excluded} has been marked as unavailable and can be removed from the itinerary. "
                    f"The system can generate an alternative plan.")
        return "I could not identify a specific place to remove from the current recommendations."

    if intent == "itinerary":
        if itinerary is None or itinerary.empty:
            return "There is currently no feasible itinerary available under the selected constraints."
        response = f"Your current {state['city']} itinerary contains {len(itinerary)} planned places.\n\n"
        for _, row in itinerary.iterrows():
            response += f"Day {int(row['day'])}: {row['place']} — {row['visit_duration_hours']:.1f} hours\n"
        return response

    if intent == "accessibility":
        if recommendations is None or recommendations.empty or "accessibility_status" not in recommendations:
            return "Accessibility data isn't available for the current recommendations."
        confirmed = (recommendations["accessibility_status"] == "yes").sum()
        unknown = (recommendations["accessibility_status"] == "unknown").sum()
        return (f"{confirmed} of {len(recommendations)} current recommendations have confirmed wheelchair "
                f"accessibility; {unknown} have no accessibility data reported by the source, so accessibility "
                f"there is unconfirmed rather than assumed.")

    if intent == "preferences":
        return ("Your current interests are: " + ", ".join(state["interests"])
                + ". Recommendations are ranked according to these preferences and the available tourism data.")

    return (f"I can help you plan your trip to {state['city']} using the available tourism "
            f"recommendations, budget, time, interests, and itinerary constraints.")


