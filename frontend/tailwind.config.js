/** Design tokens taken from the Rollcall UI/UX screenshot (green, soft mint surfaces). */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: { sans: ["Manrope", "ui-sans-serif", "system-ui", "sans-serif"] },
      colors: {
        brand: {
          50: "#f1f8f4",
          100: "#e1f1e8",
          200: "#c3e3d1",
          300: "#93cdae",
          400: "#5fb386",
          500: "#2f9663",
          600: "#177a4d",
          700: "#0f6340",
          800: "#0c4f35",
          900: "#083d29",
        },
        surface: "#f6faf7",
        ink: { DEFAULT: "#16231c", soft: "#5d6b63", faint: "#93a09a" },
        // Attendance status colours (spec: green >= 85, amber 75-85, red < 75)
        ok: "#2f9663",
        warn: "#e9a23b",
        danger: "#e0614f",
      },
      borderRadius: { xl2: "1.25rem", xl3: "1.75rem" },
      boxShadow: { card: "0 1px 2px rgba(16,40,28,.04), 0 8px 24px rgba(16,40,28,.05)" },
    },
  },
  plugins: [],
};
