/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}",
  ],

  theme: {
    extend: {
      colors: {
        fileforgeBg: "#0f0f0f",
        fileforgeCard: "#1a1a1a",
        fileforgeAccent: "#ff6b00",
        fileforgeAccentSoft: "#ff8c3a",
        fileforgeBorder: "#2a2a2a",
        fileforgeText: "#e5e5e5",
        fileforgeMuted: "#9a9a9a",
      },

      boxShadow: {
        fileforge: "0 0 20px rgba(255, 107, 0, 0.25)",
        fileforgeSoft: "0 0 10px rgba(255, 140, 58, 0.25)",
      },

      borderRadius: {
        fileforge: "14px",
      },

      animation: {
        fileforgePulse: "fileforgePulse 2s ease-in-out infinite",
      },

      keyframes: {
        fileforgePulse: {
          "0%, 100%": { opacity: 1 },
          "50%": { opacity: 0.6 },
        },
      },
    },
  },

  plugins: [],
};
