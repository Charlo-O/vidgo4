// tailwind.config.cjs
// Premium SaaS Modernism Design System
module.exports = {
  content: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // 核心品牌色 - Indigo-Violet-Pink 渐变色系
        primary: '#6366f1',           // Indigo-500
        'primary-dark': '#4f46e5',    // Indigo-600
        'primary-light': '#818cf8',   // Indigo-400
        secondary: '#a855f7',         // Violet-500
        accent: '#ec4899',            // Pink-500

        // 文字颜色
        textmain: '#1e293b',          // Slate-800
        'text-secondary': '#64748b',  // Slate-500
        'text-muted': '#94a3b8',      // Slate-400

        // 背景色 - 极淡蓝灰色
        background: '#f8f9ff',        // 淡蓝灰背景
        'background-alt': '#f1f5f9',  // Slate-100

        // 表面色 - 卡片、容器
        surface: '#ffffff',
        'surface-hover': '#f8fafc',

        // 边框和分割线
        border: '#e2e8f0',            // Slate-200
        'border-light': '#f1f5f9',    // Slate-100

        // 深色主题 - 实验室氛围
        'dark-surface': '#0f172a',    // Slate-900
        'dark-surface-alt': '#1e293b', // Slate-800
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
      borderRadius: {
        '4xl': '2rem',
        '5xl': '2.5rem',
        '6xl': '3rem',
      },
      boxShadow: {
        'glass': '0 8px 32px rgba(0, 0, 0, 0.08)',
        'glass-lg': '0 16px 48px rgba(0, 0, 0, 0.12)',
        'glow': '0 0 40px rgba(99, 102, 241, 0.15)',
        'glow-pink': '0 0 60px rgba(236, 72, 153, 0.1)',
      },
      backdropBlur: {
        'xs': '2px',
      },
      animation: {
        'float': 'float 3s ease-in-out infinite',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'gradient': 'gradient 8s ease infinite',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-10px)' },
        },
        gradient: {
          '0%, 100%': { backgroundPosition: '0% 50%' },
          '50%': { backgroundPosition: '100% 50%' },
        },
      },
    },
  },
  plugins: [],
};
