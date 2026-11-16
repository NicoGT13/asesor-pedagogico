/** Tailwind CSS v3 — se compila UNA vez en desarrollo y se versiona el CSS resultante
 *  (frontend/static/css/app.css). Render no necesita Node ni paso de build. */
module.exports = {
  content: ['./frontend/index.html', './frontend/static/js/**/*.js'],
  theme: {
    extend: {
      fontFamily: { sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'], mono: ['JetBrains Mono', 'ui-monospace', 'monospace'] },
      colors: { brand: { 50:'#eef2ff',100:'#e0e7ff',200:'#c7d2fe',300:'#a5b4fc',400:'#818cf8',500:'#6366f1',600:'#4f46e5',700:'#4338ca',800:'#3730a3',900:'#312e81' } },
      boxShadow: { soft: '0 1px 2px rgba(15,23,42,.04), 0 8px 24px -12px rgba(15,23,42,.18)' },
    },
  },
  plugins: [],
};
