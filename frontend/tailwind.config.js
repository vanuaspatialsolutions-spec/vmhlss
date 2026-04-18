/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        suitability: {
          s1: '#1a5c30',
          s2: '#4aa040',
          s3: '#c8a000',
          s4: '#c85000',
          s5: '#8b2000',
          ns: '#1a1a1a',
        },
      },
      animation: {
        spin: 'spin 1s linear infinite',
      },
    },
  },
  plugins: [],
};
