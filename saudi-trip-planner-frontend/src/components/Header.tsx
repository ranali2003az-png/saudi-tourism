import type { ReactNode } from "react";

/**
 * Small inline SVG flag badge. We intentionally don't use the 🇸🇦 flag
 * emoji here: on platforms without a regional-indicator flag font (most
 * commonly Windows/Chrome), it falls back to rendering the two letter
 * code as plain text at the emoji's normal size, which reads as a
 * squished "sa" glued onto the title next to it. An SVG has a fixed,
 * predictable size on every platform.
 */
function FlagBadge() {
  return (
    <svg
      width="22"
      height="16"
      viewBox="0 0 22 16"
      role="img"
      aria-label="Saudi Arabia"
      className="flex-shrink-0 rounded-[2px] shadow-sm"
    >
      <rect width="22" height="16" fill="#0B6E4F" />
      <rect x="3" y="10.5" width="16" height="1.6" fill="#FBF7EE" />
      <circle cx="17.5" cy="4.5" r="1.4" fill="#FBF7EE" />
    </svg>
  );
}

export default function Header({ right }: { right?: ReactNode }) {
  return (
    <header className="max-w-content mx-auto px-6 pt-8 flex items-center justify-between gap-4">
      <span className="font-display text-lg text-ink-900 flex items-center gap-2 min-w-0">
        <FlagBadge />
        <span className="truncate">Saudi Tourism Planner</span>
      </span>
      {right}
    </header>
  );
}
