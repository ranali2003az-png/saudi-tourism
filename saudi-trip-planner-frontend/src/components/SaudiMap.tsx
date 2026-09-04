const CITIES = [
  { name: "Tabuk", x: 120, y: 90 },
  { name: "Madinah", x: 150, y: 220 },
  { name: "AlUla", x: 110, y: 175 },
  { name: "Jeddah", x: 150, y: 320 },
  { name: "Makkah", x: 175, y: 305 },
  { name: "Riyadh", x: 330, y: 300 },
  { name: "Dammam", x: 430, y: 260 },
  { name: "Abha", x: 210, y: 430 },
];

export default function SaudiMap() {
  return (
    <svg
      viewBox="0 0 520 520"
      className="w-full h-auto"
      role="img"
      aria-label="Stylized map of Saudi Arabia with major tourist cities"
    >
      {/* Stylized (not geodetically precise) outline -- a decorative
          silhouette, not a data map. */}
      <path
        d="M 95 60
           L 260 40
           L 340 95
           L 470 150
           L 460 230
           L 500 300
           L 440 370
           L 380 470
           L 260 500
           L 200 460
           L 150 480
           L 90 400
           L 120 330
           L 70 260
           L 100 200
           L 60 140
           Z"
        fill="#0B6E4F"
        fillOpacity="0.08"
        stroke="#0B6E4F"
        strokeWidth="2.5"
        strokeLinejoin="round"
      />

      {CITIES.map((c) => (
        <g key={c.name}>
          <circle cx={c.x} cy={c.y} r="14" fill="#0B6E4F" fillOpacity="0.12" />
          <circle cx={c.x} cy={c.y} r="5.5" fill="#0B6E4F" />
          <text
            x={c.x + 12}
            y={c.y + 4}
            className="fill-ink-900 font-body"
            fontSize="14"
            fontWeight="500"
          >
            {c.name}
          </text>
        </g>
      ))}
    </svg>
  );
}
