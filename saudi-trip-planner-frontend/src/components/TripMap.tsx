import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";
import type { Place } from "../lib/types";

// Default Leaflet marker icons reference image files that Vite doesn't
// bundle automatically -- point them at a CDN so pins render correctly.
const icon = new L.Icon({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
});

const CITY_CENTERS: Record<string, [number, number]> = {
  Riyadh: [24.7136, 46.6753],
  Jeddah: [21.4858, 39.1925],
  Makkah: [21.3891, 39.8579],
  Madinah: [24.5247, 39.5692],
  AlUla: [26.6084, 37.9214],
  Abha: [18.2164, 42.5053],
  Dammam: [26.4207, 50.0888],
  Tabuk: [28.3838, 36.5550],
};

export default function TripMap({ city, places }: { city: string; places: Place[] }) {
  const center = CITY_CENTERS[city] ?? [24.7136, 46.6753];
  const located = places.filter((p) => p.latitude && p.longitude);

  return (
    <MapContainer center={center} zoom={12} scrollWheelZoom={false} className="w-full h-full rounded-2xl">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {located.map((p, i) => (
        <Marker key={`${p.name}-${i}`} position={[p.latitude!, p.longitude!]} icon={icon}>
          <Popup>{p.name}</Popup>
        </Marker>
      ))}
    </MapContainer>
  );
}
