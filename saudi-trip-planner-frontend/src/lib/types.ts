export type TransportMode = "walking" | "public_transit" | "driving";

export interface TripPreferences {
  city: string;
  budget: number;
  days: number;
  interests: string[];
  transport: TransportMode;
  requireAccessibility: boolean;
}

export type PlaceCategory = "attractions" | "restaurants" | "cafes";

export interface Place {
  name: string;
  category: PlaceCategory;
  latitude?: number;
  longitude?: number;
  estimated_cost?: number;
  rating?: number;
  address?: string;
}

export interface ItineraryStop {
  place: string;
  category: PlaceCategory;
  latitude?: number;
  longitude?: number;
  estimated_cost?: number;
  visit_duration_hours?: number;
  travel_time_hours?: number;
  travel_distance_km?: number;
}

export interface ItineraryDay {
  day: number;
  stops: ItineraryStop[];
}

export interface TripResult {
  places: Place[];
  itinerary: ItineraryDay[];
}

export interface ChatMessage {
  role: "user" | "assistant";
  text: string;
}
