import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTrip } from "../lib/TripContext";
import { generateTrip, ApiError } from "../lib/api";
import Header from "../components/Header";
import type { TransportMode } from "../lib/types";

const CITIES = ["Riyadh","Abha", "Dammam", "Tabuk"];
const INTEREST_OPTIONS = ["Culture & Heritage", "Food", "Nature", "Adventure", "Shopping", "Relaxation"];
const TRANSPORT_OPTIONS: { value: TransportMode; label: string }[] = [
  { value: "walking", label: " Walking" },
  { value: "public_transit", label: " Public transit" },
  { value: "driving", label: " Driving / taxi" },
];

export default function Plan() {
  const navigate = useNavigate();
  const { prefs, setPrefs, setResult } = useTrip();

  const [city, setCity] = useState(prefs?.city ?? CITIES[0]);
  const [budget, setBudget] = useState(prefs?.budget ?? 1000);
  const [days, setDays] = useState(prefs?.days ?? 3);
  const [interests, setInterests] = useState<string[]>(prefs?.interests ?? []);
  const [transport, setTransport] = useState<TransportMode>(prefs?.transport ?? "driving");
  const [requireAccessibility, setRequireAccessibility] = useState(prefs?.requireAccessibility ?? false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function toggleInterest(name: string) {
    setInterests((cur) => (cur.includes(name) ? cur.filter((i) => i !== name) : [...cur, name]));
  }

  async function handleGenerate() {
    setError(null);
    setLoading(true);
    const newPrefs = { city, budget, days, interests, transport, requireAccessibility };
    setPrefs(newPrefs);
    try {
      const result = await generateTrip(newPrefs);
      setResult(result);
      navigate("/results");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Couldn't reach the trip planner backend. Is it running?");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-sand-100">
      <Header />

      <main className="max-w-content mx-auto px-6 py-12 md:py-16 grid md:grid-cols-[1fr_360px] gap-10">
        <div>
          <h1 className="font-display text-3xl text-ink-900 mb-8">Trip preferences</h1>

          <div className="space-y-8">
            <div>
              <label className="block font-body font-medium text-ink-900 mb-2"> Destination</label>
              <select
                value={city}
                onChange={(e) => setCity(e.target.value)}
                className="w-full border border-ink-900/15 rounded-lg px-4 py-3 bg-white font-body"
              >
                {CITIES.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-2 gap-6">
              <div>
                <label className="block font-body font-medium text-ink-900 mb-2"> Budget (SAR)</label>
                <input
                  type="number"
                  min={0}
                  value={budget}
                  onChange={(e) => setBudget(Number(e.target.value))}
                  className="w-full border border-ink-900/15 rounded-lg px-4 py-3 bg-white font-body"
                />
              </div>
              <div>
                <label className="block font-body font-medium text-ink-900 mb-2">📅 Days</label>
                <input
                  type="number"
                  min={1}
                  max={14}
                  value={days}
                  onChange={(e) => setDays(Number(e.target.value))}
                  className="w-full border border-ink-900/15 rounded-lg px-4 py-3 bg-white font-body"
                />
              </div>
            </div>

            <div>
              <label className="block font-body font-medium text-ink-900 mb-2"> Interests</label>
              <div className="flex flex-wrap gap-2">
                {INTEREST_OPTIONS.map((opt) => {
                  const active = interests.includes(opt);
                  return (
                    <button
                      key={opt}
                      type="button"
                      onClick={() => toggleInterest(opt)}
                      className={`px-4 py-2 rounded-full text-sm font-body border transition-colors ${
                        active
                          ? "bg-palm-600 border-palm-600 text-sand-50"
                          : "bg-white border-ink-900/15 text-ink-700 hover:border-palm-600"
                      }`}
                    >
                      {opt}
                    </button>
                  );
                })}
              </div>
            </div>

            <div>
              <label className="block font-body font-medium text-ink-900 mb-2"> Transport</label>
              <div className="flex gap-2">
                {TRANSPORT_OPTIONS.map((opt) => (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => setTransport(opt.value)}
                    className={`px-4 py-2 rounded-full text-sm font-body border transition-colors ${
                      transport === opt.value
                        ? "bg-palm-600 border-palm-600 text-sand-50"
                        : "bg-white border-ink-900/15 text-ink-700 hover:border-palm-600"
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block font-body font-medium text-ink-900 mb-2"> Accessibility</label>
              <label className="flex items-start gap-3 border border-ink-900/15 rounded-lg px-4 py-3 bg-white font-body cursor-pointer">
                <input
                  type="checkbox"
                  checked={requireAccessibility}
                  onChange={(e) => setRequireAccessibility(e.target.checked)}
                  className="mt-0.5 h-4 w-4 accent-palm-600"
                />
                <span className="text-sm text-ink-700">
                  Only recommend wheelchair-accessible places — better suited for travelers with mobility needs,
                  seniors, or young children
                </span>
              </label>
            </div>
          </div>

          {error && (
            <p className="mt-6 text-rock-600 font-body text-sm">{error}</p>
          )}

          <button
            onClick={handleGenerate}
            disabled={loading}
            className="mt-10 bg-palm-600 hover:bg-palm-700 disabled:opacity-60 text-sand-50 font-body font-medium px-7 py-3.5 rounded-full transition-colors"
          >
            {loading ? "Generating…" : "🤖 Generate Trip"}
          </button>
        </div>

        <aside className="bg-palm-50 rounded-2xl p-6 h-fit">
          <p className="font-display text-lg text-ink-900 mb-3">Trip brief</p>
          <dl className="space-y-2 font-body text-sm text-ink-700">
            <div className="flex justify-between"><dt>Destination</dt><dd className="font-medium text-ink-900">{city}</dd></div>
            <div className="flex justify-between"><dt>Budget</dt><dd className="font-medium text-ink-900">{budget} SAR</dd></div>
            <div className="flex justify-between"><dt>Days</dt><dd className="font-medium text-ink-900">{days}</dd></div>
            <div className="flex justify-between"><dt>Interests</dt><dd className="font-medium text-ink-900 text-right">{interests.length ? interests.join(", ") : "Any"}</dd></div>
            <div className="flex justify-between"><dt>Accessibility</dt><dd className="font-medium text-ink-900">{requireAccessibility ? "Required" : "Not required"}</dd></div>
          </dl>
        </aside>
      </main>
    </div>
  );
}
