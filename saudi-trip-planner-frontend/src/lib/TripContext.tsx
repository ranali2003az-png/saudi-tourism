import React, { createContext, useContext, useState } from "react";
import type { TripPreferences, TripResult } from "./types";

interface TripState {
  prefs: TripPreferences | null;
  setPrefs: (p: TripPreferences) => void;
  result: TripResult | null;
  setResult: (r: TripResult | null) => void;
}

const TripContext = createContext<TripState | null>(null);

export function TripProvider({ children }: { children: React.ReactNode }) {
  const [prefs, setPrefs] = useState<TripPreferences | null>(null);
  const [result, setResult] = useState<TripResult | null>(null);
  return (
    <TripContext.Provider value={{ prefs, setPrefs, result, setResult }}>
      {children}
    </TripContext.Provider>
  );
}

export function useTrip() {
  const ctx = useContext(TripContext);
  if (!ctx) throw new Error("useTrip must be used inside TripProvider");
  return ctx;
}
