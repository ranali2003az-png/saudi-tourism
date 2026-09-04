/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        sand: {
          50: "#FBF7EE",
          100: "#F6EFDD",
          200: "#EAE0C4",
        },
        ink: {
          900: "#1E2A22",
          700: "#33443A",
        },
        palm: {
          600: "#0B6E4F",
          700: "#095A41",
          50: "#E9F4EE",
        },
        dune: {
          400: "#C08A4E",
          500: "#AD7640",
        },
        rock: {
          600: "#8C4A34",
        },
      },
      fontFamily: {
        display: ["Fraunces", "ui-serif", "Georgia", "serif"],
        body: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      maxWidth: {
        content: "1180px",
      },
    },
  },
  plugins: [],
};
