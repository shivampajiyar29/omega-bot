/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        mono: ["IBM Plex Mono", "monospace"],
        sans: ["Syne", "sans-serif"],
        display: ["Syne", "sans-serif"],
      },
      colors: {
        bg: {
          DEFAULT: "#0a0b0e",
          1: "#111318",
          2: "#16191f",
          3: "#1c2029",
          4: "#22263040",
        },
        border: {
          DEFAULT: "rgba(255,255,255,0.07)",
          2: "rgba(255,255,255,0.12)",
        },
        text: {
          DEFAULT: "#e8eaf0",
          2: "#8b90a0",
          3: "#545870",
        },
        green:  { DEFAULT: "#00d4a0", dim: "rgba(0,212,160,0.08)" },
        red:    { DEFAULT: "#ff4757", dim: "rgba(255,71,87,0.08)" },
        amber:  { DEFAULT: "#ffb347", dim: "rgba(255,179,71,0.08)" },
        blue:   { DEFAULT: "#4a9eff", dim: "rgba(74,158,255,0.08)" },
        purple: { DEFAULT: "#9b8fff", dim: "rgba(155,143,255,0.08)" },
      },
      borderRadius: {
        DEFAULT: "6px",
        card: "10px",
        lg: "12px",
        xl: "16px",
      },
    },
  },
  plugins: [],
};
