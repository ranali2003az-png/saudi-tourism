import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTrip } from "../lib/TripContext";
import TripMap from "../components/TripMap";
import PlaceCard from "../components/PlaceCard";
import Header from "../components/Header";
import ChatWidget from "../components/ChatWidget";
import { generateTrip, ApiError } from "../lib/api";
import type { PlaceCategory } from "../lib/types";

const CATEGORY_TABS: { value: PlaceCategory; label: string }[] = [
  { value: "attractions", label: " Attractions" },
  { value: "restaurants", label: " Restaurants" },
  { value: "cafes", label: " Cafes" },
];

export default function Results() {
  const navigate = useNavigate();
  const { prefs, result, setResult } = useTrip();
  const [activeDay, setActiveDay] = useState(1);
  const [activeCategory, setActiveCategory] = useState<PlaceCategory>("attractions");
  const [excludedPlaces, setExcludedPlaces] = useState<string[]>([]);
  const [updating, setUpdating] = useState(false);
  const [updateError, setUpdateError] = useState<string | null>(null);

  useEffect(() => {
    if (!prefs || !result) navigate("/plan");
  }, [prefs, result, navigate]);

  if (!prefs || !result) return null;

  const day = result.itinerary.find((d) => d.day === activeDay) ?? result.itinerary[0];
  const placesForCategory = result.places.filter((p) => p.category === activeCategory);

  // Adaptive re-planning: excludes a place and asks the backend to
  // rebuild the whole trip (distances/times recompute automatically
  // since the itinerary is regenerated from scratch). Used for both
  // "remove this stop" and "swap this stop" — swapping is simply
  // removing it and letting the next-best alternative take its place.
  async function updateTrip(placeToExclude: string) {
    setUpdateError(null);
    setUpdating(true);
    const nextExcluded = [...excludedPlaces, placeToExclude];
    try {
      const newResult = await generateTrip(prefs!, nextExcluded);
      setExcludedPlaces(nextExcluded);
      setResult(newResult);
    } catch (e) {
      setUpdateError(e instanceof ApiError ? e.message : "Couldn't update the plan. Is the backend running?");
    } finally {
      setUpdating(false);
    }
  }

  return (
    <div className="min-h-screen bg-sand-100">
      <Header
        right={
          <button
            onClick={() => navigate("/plan")}
            className="text-sm font-body font-medium text-palm-700 border border-palm-600 rounded-full px-5 py-2 hover:bg-palm-50 transition-colors"
          >
            🔄 Modify plan
          </button>
        }
      />

      <main className="max-w-content mx-auto px-6 py-10">
        <h1 className="font-display text-3xl text-ink-900">
          Your {prefs.days}-day trip to {prefs.city}
        </h1>
        <p className="font-body text-ink-700 mt-1">
          Budget {prefs.budget} SAR · {prefs.interests.join(", ") || "Any interests"}
        </p>

        <div className="grid lg:grid-cols-[1fr_420px] gap-10 mt-10">
          <div>
            {/* Day tabs */}
            <div className="flex gap-2 border-b border-ink-900/10 mb-6">
              {result.itinerary.map((d) => (
                <button
                  key={d.day}
                  onClick={() => setActiveDay(d.day)}
                  className={`px-4 py-2.5 font-body text-sm font-medium border-b-2 -mb-px transition-colors ${
                    activeDay === d.day
                      ? "border-palm-600 text-palm-700"
                      : "border-transparent text-ink-700/60 hover:text-ink-900"
                  }`}
                >
                  🗓️ Day {d.day}
                </button>
              ))}
            </div>

            {updateError && <p className="text-sm text-rock-600 font-body mb-3">{updateError}</p>}

            <ol className="space-y-3">
              {day?.stops.map((stop, i) => (
                <li key={i} className="border border-ink-900/10 rounded-xl p-4 bg-white/60 flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <p className="font-body font-medium text-ink-900">
                      {i + 1}. {stop.place}
                    </p>
                    <p className="text-sm text-ink-700/70 mt-0.5">
                      {stop.visit_duration_hours ? `${stop.visit_duration_hours}h visit` : ""}
                      {stop.travel_distance_km ? ` · ${stop.travel_distance_km.toFixed(1)} km from previous` : ""}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    {typeof stop.estimated_cost === "number" && (
                      <span className="text-sm text-palm-700 font-medium whitespace-nowrap">{stop.estimated_cost} SAR</span>
                    )}
                    <button
                      onClick={() => updateTrip(stop.place)}
                      disabled={updating}
                      title="Swap for another place"
                      className="text-xs font-body text-ink-700 border border-ink-900/15 rounded-full px-2.5 py-1 hover:border-palm-600 hover:text-palm-700 disabled:opacity-50 transition-colors"
                    >
                      🔁 Swap
                    </button>
                    <button
                      onClick={() => updateTrip(stop.place)}
                      disabled={updating}
                      title="Remove this stop"
                      className="text-xs font-body text-ink-700 border border-ink-900/15 rounded-full px-2.5 py-1 hover:border-rock-600 hover:text-rock-600 disabled:opacity-50 transition-colors"
                    >
                      ✕ Remove
                    </button>
                  </div>
                </li>
              )) ?? (
                <p className="text-ink-700 font-body">No itinerary stops yet for this day.</p>
              )}
              {updating && <p className="text-sm text-ink-700/70 font-body">Updating your plan…</p>}
            </ol>

            {/* Category tabs for recommended places */}
            <div className="mt-12">
              <div className="flex gap-2 mb-4">
                {CATEGORY_TABS.map((tab) => (
                  <button
                    key={tab.value}
                    onClick={() => setActiveCategory(tab.value)}
                    className={`px-4 py-2 rounded-full text-sm font-body border transition-colors ${
                      activeCategory === tab.value
                        ? "bg-palm-600 border-palm-600 text-sand-50"
                        : "bg-white border-ink-900/15 text-ink-700 hover:border-palm-600"
                    }`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>
              <div className="grid sm:grid-cols-2 gap-3">
                {placesForCategory.length ? (
                  placesForCategory.map((p, i) => <PlaceCard key={`${p.name}-${i}`} place={p} />)
                ) : (
                  <p className="text-ink-700 font-body text-sm">No {activeCategory} found for this trip.</p>
                )}
              </div>
            </div>
          </div>

          {/* Map */}
          <div className="h-[420px] lg:h-auto lg:sticky lg:top-8">
            <TripMap city={prefs.city} places={result.places} />
          </div>
        </div>
      </main>

      <ChatWidget prefs={prefs} excludedPlaces={excludedPlaces} />
    </div>
  );
}
