import type { Place } from "../lib/types";

const CATEGORY_ICON: Record<string, string> = {
  attractions: "📍",
  restaurants: "🍽️",
  cafes: "☕",
};

export default function PlaceCard({ place }: { place: Place }) {
  return (
    <div className="border border-ink-900/10 rounded-xl p-4 bg-white/60">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-body font-medium text-ink-900">
            {CATEGORY_ICON[place.category]} {place.name}
          </p>
          {place.address && (
            <p className="text-sm text-ink-700/70 mt-0.5">{place.address}</p>
          )}
        </div>
        {typeof place.estimated_cost === "number" && (
          <span className="text-sm text-palm-700 font-medium whitespace-nowrap">
            {place.estimated_cost} SAR
          </span>
        )}
      </div>
    </div>
  );
}
