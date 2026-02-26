/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        sto: {
          bg: "#f5f4f0",
          card: "#ffffff",
          cardBorder: "#e8e6e1",
          accent: "#0d9488",
          accentLight: "#2dd4bf",
          muted: "#6b7280",
          text: "#374151",
          danger: "#dc2626",
          positive: "#16a34a",
        },
      },
      borderRadius: {
        "sto": "1rem",
        "sto-lg": "1.25rem",
      },
      boxShadow: {
        "sto": "0 2px 8px rgba(0,0,0,0.06)",
        "sto-hover": "0 8px 24px rgba(0,0,0,0.08)",
      },
    },
  },
  plugins: [],
};
