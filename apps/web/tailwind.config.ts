import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        editorial: {
          bg: "#F8F7F4",
          surface: "#FFFFFF",
          ink: "#161B22",
          muted: "#4A5568",
          border: "#DCE1E7",
          accent: "#0F3D5E",
          warn: "#B45309",
          danger: "#9B1C1C",
          ok: "#166534",
        },
      },
    },
  },
  plugins: [],
};

export default config;
