import type { TripPreferences, TripResult, Place, ItineraryDay, PlaceCategory } from "./types";

// Point this at your FastAPI backend. Set VITE_API_BASE in a .env file
// (see .env.example) -- defaults to localhost for local development.
const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

function normalizeCategory(raw: string | undefined): PlaceCategory {
  const v = (raw || "").toLowerCase();
  if (v.startsWith("restaurant")) return "restaurants";
  if (v.startsWith("cafe")) return "cafes";
  return "attractions";
}

function normalizePlace(raw: any): Place {
  return {
    name: raw.name ?? raw.place ?? "Unnamed place",
    category: normalizeCategory(raw.category ?? raw.place_type),
    latitude: raw.latitude ?? raw.lat,
    longitude: raw.longitude ?? raw.lon ?? raw.lng,
    estimated_cost: raw.estimated_cost ?? raw.cost,
    rating: raw.rating ?? raw.popularity_score,
    address: raw.address,
  };
}

function normalizeItinerary(raw: any[]): ItineraryDay[] {
  // Handles either an already-grouped [{day, stops:[...]}] shape, or a
  // flat list of stops with a `day` field on each (like the Streamlit
  // app's generate_itinerary() output) -- group the flat shape here.
  if (raw.length > 0 && Array.isArray(raw[0]?.stops)) {
    return raw.map((d) => ({
      day: d.day,
      stops: d.stops.map((s: any) => ({
        place: s.place ?? s.name,
        category: normalizeCategory(s.category ?? s.place_type),
        latitude: s.latitude ?? s.lat,
        longitude: s.longitude ?? s.lon,
        estimated_cost: s.estimated_cost,
        visit_duration_hours: s.visit_duration_hours,
        travel_time_hours: s.travel_time_hours,
        travel_distance_km: s.travel_distance_km,
      })),
    }));
  }

  const byDay = new Map<number, ItineraryDay>();
  for (const row of raw) {
    const day = row.day ?? 1;
    if (!byDay.has(day)) byDay.set(day, { day, stops: [] });
    byDay.get(day)!.stops.push({
      place: row.place ?? row.name,
      category: normalizeCategory(row.category ?? row.place_type),
      latitude: row.latitude ?? row.lat,
      longitude: row.longitude ?? row.lon,
      estimated_cost: row.estimated_cost,
      visit_duration_hours: row.visit_duration_hours,
      travel_time_hours: row.travel_time_hours,
      travel_distance_km: row.travel_distance_km,
    });
  }
  return [...byDay.values()].sort((a, b) => a.day - b.day);
}

export class ApiError extends Error {}

/**
 * Calls the FastAPI backend to generate a trip.
 *
 * ADJUST ME: this assumes a single POST /plan-trip endpoint that returns
 * { places: [...], itinerary: [...] }. If your FastAPI backend instead
 * exposes separate endpoints (e.g. POST /recommendations and
 * POST /itinerary, matching the ML engine's recommend_places() /
 * generate_itinerary() functions), split this into two fetch calls --
 * the normalize* helpers above already accept either shape.
 */
export async function generateTrip(prefs: TripPreferences, excludedPlaces: string[] = []): Promise<TripResult> {
  const res = await fetch(`${API_BASE}/plan-trip`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      city: prefs.city,
      budget: prefs.budget,
      days: prefs.days,
      interests: prefs.interests,
      transport_mode: prefs.transport,
      require_accessibility: prefs.requireAccessibility,
      excluded_places: excludedPlaces,
    }),
  });

  if (!res.ok) {
    throw new ApiError(`Backend returned ${res.status}. Check VITE_API_BASE and the /plan-trip route.`);
  }

  const data = await res.json();
  const rawPlaces = data.places ?? data.recommendations ?? [];
  const rawItinerary = data.itinerary ?? [];

  return {
    places: rawPlaces.map(normalizePlace),
    itinerary: normalizeItinerary(rawItinerary),
  };
}

/**
 * Sends a message to the grounded chat assistant (POST /assistant). The
 * backend recomputes recommendations/itinerary for the given prefs and
 * excludedPlaces so the assistant's answer is always based on the trip
 * as it currently stands, not stale data.
 */
export async function askAssistant(
  message: string,
  prefs: TripPreferences,
  excludedPlaces: string[] = []
): Promise<{ reply: string; excludedPlace?: string | null }> {
  const res = await fetch(`${API_BASE}/assistant`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      city: prefs.city,
      budget: prefs.budget,
      days: prefs.days,
      interests: prefs.interests,
      transport_mode: prefs.transport,
      require_accessibility: prefs.requireAccessibility,
      excluded_places: excludedPlaces,
    }),
  });

  if (!res.ok) {
    throw new ApiError(`Backend returned ${res.status}. Check VITE_API_BASE and the /assistant route.`);
  }

  const data = await res.json();
  return { reply: data.reply ?? "Sorry, I couldn't come up with an answer for that.", excludedPlace: data.excluded_place };
}
