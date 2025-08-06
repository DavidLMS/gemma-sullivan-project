/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Logo color as primary
        primary: '#9E72DA',
        'primary-light': '#B18CE6',
        'primary-dark': '#8B5FCC',
        // Color palette for buttons
        'learn-blue': '#3B82F6',
        'learn-blue-dark': '#2563EB',
        'practice-green': '#10B981',
        'practice-green-dark': '#059669',
        'experiment-orange': '#F59E0B',
        'experiment-orange-dark': '#D97706',
        // Gray background
        'app-bg': '#F5F5F5',
        'card-bg': '#FFFFFF',
      },
      fontFamily: {
        'sans': ['Roboto', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}