/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#FFFFFF',
        primary: '#059669',    // Emerald 600
        accent: '#7C3AED',     // Violet 600
        secondary: '#E11D48',  // Rose 600
        textMain: '#111827',   // Gray 900
        textMuted: '#4B5563',  // Gray 600
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
