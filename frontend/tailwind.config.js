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
          DEFAULT: '#39FF14',
          light: '#7CFF62',
          dark: '#1FB700',
        },
        secondary: {
          DEFAULT: '#00C853',
          light: '#5EFC82',
          dark: '#008F3A',
        },
        background: {
          DEFAULT: '#030603',
          card: 'rgba(57, 255, 20, 0.08)',
        },
        text: {
          primary: '#B8FF9A',
          secondary: '#75C66A',
          tertiary: '#3A7E40',
        },
      },
      gradients: {
        'primary-gradient': 'linear-gradient(135deg, #00A63E, #39FF14)',
        'glow-effect': 'radial-gradient(circle, rgba(57, 255, 20, 0.45), transparent)',
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
        'display': ['"Share Tech Mono"', '"JetBrains Mono"', 'ui-monospace', 'monospace'],
        'sans': ['"Share Tech Mono"', '"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
      boxShadow: {
        'glow': '0 0 22px rgba(57, 255, 20, 0.32)',
        'glow-lg': '0 0 40px rgba(57, 255, 20, 0.45)',
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
