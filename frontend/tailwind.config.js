/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Design System Colors
        primary: {
          DEFAULT: '#66FCF1',
          light: '#66FCF1',
          dark: '#45A29E',
        },
        secondary: {
          DEFAULT: '#45A29E',
          light: '#66FCF1',
          dark: '#1F2833',
        },
        background: {
          DEFAULT: '#0B0C10',
          card: 'rgba(31, 40, 51, 0.76)',
        },
        text: {
          primary: '#C5C6C7',
          secondary: '#8E969F',
          tertiary: '#66707A',
        },
      },
      gradients: {
        'primary-gradient': 'linear-gradient(135deg, #45A29E, #66FCF1)',
        'glow-effect': 'radial-gradient(circle, rgba(102, 252, 241, 0.3), transparent)',
      },
      spacing: {
        'card': '16px',
        'card-lg': '24px',
      },
      borderRadius: {
        'sm': '8px',
        'md': '12px',
        'lg': '16px',
        'xl': '24px',
      },
      fontSize: {
        'h1': '28px',
        'h2': '20px',
        'body': '14px',
      },
      fontFamily: {
        'display': ['"Manrope"', '"IBM Plex Sans"', 'ui-sans-serif', 'sans-serif'],
        'sans': ['"IBM Plex Sans"', '"Manrope"', 'ui-sans-serif', 'sans-serif'],
      },
      boxShadow: {
        'glow': '0 12px 24px rgba(15, 23, 42, 0.28)',
        'glow-lg': '0 20px 40px rgba(15, 23, 42, 0.36)',
      },
      animation: {
        'typing': 'typing 0.7s steps(4, end) infinite',
        'fade-in': 'fadeIn 0.3s ease-in-out',
        'scale-pop': 'scalePop 0.3s cubic-bezier(0.34, 1.56, 0.64, 1)',
        'pulse': 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      keyframes: {
        typing: {
          '0%': { width: '0px' },
          '100%': { width: '16px' },
        },
        fadeIn: {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        scalePop: {
          '0%': { transform: 'scale(0.8)', opacity: '0' },
          '50%': { transform: 'scale(1.05)' },
          '100%': { transform: 'scale(1)', opacity: '1' },
        },
        pulse: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.5' },
        },
      },
      screens: {
        'sm': '640px',
        'md': '768px',
        'lg': '1024px',
        'xl': '1280px',
        '2xl': '1536px',
      },
    },
  },
  plugins: [],
}
