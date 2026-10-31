/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#f0f5ff',
          100: '#e0ebff',
          200: '#c7d7fe',
          300: '#a4bcfd',
          400: '#7897fc',
          500: '#536dfb',
          600: '#414ef0',
          700: '#353fe1',
          800: '#2f37bf',
          900: '#2f359e',
        },
        dark: {
          900: '#0a0a0f',
          800: '#12121a',
          700: '#1a1a24',
          600: '#242430',
          500: '#2e2e3c',
        }
      }
    },
  },
  plugins: [],
}