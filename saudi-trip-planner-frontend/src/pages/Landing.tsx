import { Link } from "react-router-dom";
import SaudiMap from "../components/SaudiMap";
import Header from "../components/Header";

export default function Landing() {
  return (
    <div className="min-h-screen bg-sand-100">
      <Header />

      <main className="max-w-content mx-auto px-6 py-16 md:py-24 grid md:grid-cols-2 gap-12 items-center">
        <div>
          <h1 className="font-display text-5xl md:text-6xl leading-[1.05] text-ink-900">
            Saudi Tourism
            <br />
            Planner
          </h1>
          <p className="mt-6 text-lg text-ink-700 max-w-md">
            Tell us your city, budget, and days — we'll put together a
            day-by-day trip across attractions, restaurants, and cafes.
          </p>
          <Link
            to="/plan"
            className="inline-block mt-8 bg-palm-600 hover:bg-palm-700 text-sand-50 font-body font-medium px-7 py-3.5 rounded-full transition-colors"
          >
            Plan My Trip
          </Link>
        </div>

        <div className="relative">
          <SaudiMap />
        </div>
      </main>
    </div>
  );
}
