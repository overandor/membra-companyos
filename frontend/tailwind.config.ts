import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{js,ts,jsx,tsx,mdx}", "./components/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        membrabg: "#0b0f1a",
        membragold: "#c9a84c",
        membragoldlight: "#e4c76b",
        membrasurface: "#111827",
        membraborder: "#1f2937",
        membramuted: "#9ca3af",
      },
    },
  },
  plugins: [],
};

export default config;
