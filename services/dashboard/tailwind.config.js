/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        green:  { DEFAULT: '#2d6a3f', light: '#4a9261', dark: '#1a2414' },
        gold:   { DEFAULT: '#c9860a', light: '#e8a82c' },
      },
    },
  },
  plugins: [],
}
