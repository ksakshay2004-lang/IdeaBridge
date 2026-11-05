/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: { sans: ["Inter", "ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "Roboto", "sans-serif"] },
      colors: {
        navy: { 50: "#f3f5fb", 100: "#e5e9f6", 200: "#c9d1ec", 300: "#a0aedd", 400: "#7084c9", 500: "#4a5fb3", 600: "#3a4a96", 700: "#2f3b78", 800: "#1f2754", 900: "#141a3b", 950: "#0b0f26" },
      },
      boxShadow: { card: "0 1px 2px rgba(16,24,64,.06), 0 4px 16px rgba(16,24,64,.05)" },
      keyframes: { fadeUp: { "0%": { opacity: 0, transform: "translateY(6px)" }, "100%": { opacity: 1, transform: "none" } } },
      animation: { fadeUp: "fadeUp .25s ease-out both" },
    },
  },
  plugins: [],
};
