import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // ── Core surfaces ───────────────────────────────────────────────────
        background: "#09090b",
        surface: "#18181b",
        "surface-elevated": "#27272a",
        "surface-hover": "#2a2a2e",

        // ── Borders ─────────────────────────────────────────────────────────
        border: "#3f3f46",
        "border-subtle": "#27272a",

        // ── Text ────────────────────────────────────────────────────────────
        "text-primary": "#fafafa",
        "text-secondary": "#a1a1aa",
        "text-muted": "#71717a",

        // ── Accent — Emerald (health metrics, success) ─────────────────────
        emerald: {
          50: "#ecfdf5",
          100: "#d1fae5",
          200: "#a7f3d0",
          300: "#6ee7b7",
          400: "#34d399",
          500: "#10b981",
          600: "#059669",
          700: "#047857",
          800: "#065f46",
          900: "#064e3b",
          950: "#022c22",
        },

        // ── Accent — Blue (AI, insights, information) ──────────────────────
        blue: {
          50: "#eff6ff",
          100: "#dbeafe",
          200: "#bfdbfe",
          300: "#93c5fd",
          400: "#60a5fa",
          500: "#3b82f6",
          600: "#2563eb",
          700: "#1d4ed8",
          800: "#1e40af",
          900: "#1e3a8a",
          950: "#172554",
        },

        // ── Accent — Indigo (AI assistant, premium features) ───────────────
        indigo: {
          400: "#818cf8",
          500: "#6366f1",
          600: "#4f46e5",
        },
      },

      fontFamily: {
        sans: ["var(--font-geist-sans)", "Inter", "system-ui", "sans-serif"],
        mono: ["var(--font-geist-mono)", "JetBrains Mono", "monospace"],
      },

      borderRadius: {
        "4xl": "2rem",
        "5xl": "2.5rem",
      },

      boxShadow: {
        "glow-emerald": "0 0 20px rgba(16, 185, 129, 0.15)",
        "glow-blue": "0 0 20px rgba(59, 130, 246, 0.15)",
        "glow-indigo": "0 0 20px rgba(99, 102, 241, 0.15)",
        "card": "0 1px 3px rgba(0, 0, 0, 0.4), 0 1px 2px rgba(0, 0, 0, 0.3)",
        "card-hover": "0 4px 12px rgba(0, 0, 0, 0.5)",
        "float": "0 8px 32px rgba(0, 0, 0, 0.6)",
      },

      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "shimmer": "shimmer 2s linear infinite",
        "float": "float 6s ease-in-out infinite",
      },

      keyframes: {
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        float: {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-8px)" },
        },
      },

      backgroundImage: {
        "gradient-radial": "radial-gradient(var(--tw-gradient-stops))",
        "shimmer-gradient":
          "linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.05) 50%, transparent 100%)",
        "emerald-gradient": "linear-gradient(135deg, #059669, #10b981)",
        "blue-gradient": "linear-gradient(135deg, #1d4ed8, #3b82f6)",
        "indigo-gradient": "linear-gradient(135deg, #4f46e5, #818cf8)",
        "card-gradient": "linear-gradient(180deg, #18181b 0%, #111113 100%)",
      },

      spacing: {
        "safe-bottom": "env(safe-area-inset-bottom)",
        "nav-height": "5rem",
      },
    },
  },
  plugins: [],
};

export default config;
