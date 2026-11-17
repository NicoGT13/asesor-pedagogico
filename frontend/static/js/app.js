/* =============================================================================
 * Asesor Pedagógico Inteligente — SPA (JavaScript vainilla + Tailwind CSS)
 * Router por hash, cliente API con JWT, vistas por rol (RBAC en UI + backend).
 * ========================================================================== */
'use strict';

// ------------------------------------------------------------------ Estado
const S = {
  token: localStorage.getItem('api_token'),
  user: JSON.parse(localStorage.getItem('api_user') || 'null'),
  health: null,
  charts: [],
};
const isStaff = () => S.user && ['DOCENTE', 'ADMINISTRADOR'].includes(S.user.role);
const isAdmin = () => S.user && S.user.role === 'ADMINISTRADOR';

// ------------------------------------------------------------------ Utilidades
const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];
const esc = (v) => String(v ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const fmt = (n, d = 1) => (n === null || n === undefined ? '—' : Number(n).toFixed(d).replace('.', ','));
const fdate = (iso) => (iso ? new Date(iso).toLocaleDateString('es-CO', { year: 'numeric', month: 'short', day: 'numeric' }) : '—');
const initials = (name) => (name || '?').split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]).join('').toUpperCase();

const LEVEL = {
  Sobresaliente: { c: 'bg-emerald-100 text-emerald-800 ring-emerald-200', hex: '#059669' },
  Competente: { c: 'bg-sky-100 text-sky-800 ring-sky-200', hex: '#0284c7' },
  'En desarrollo': { c: 'bg-amber-100 text-amber-800 ring-amber-200', hex: '#d97706' },
  Inicial: { c: 'bg-rose-100 text-rose-800 ring-rose-200', hex: '#e11d48' },
  'Sin evidencia': { c: 'bg-slate-100 text-slate-600 ring-slate-200', hex: '#94a3b8' },
};
const levelOf = (s) => (s == null ? 'Sin evidencia' : s >= 4.6 ? 'Sobresaliente' : s >= 4 ? 'Competente' : s >= 3 ? 'En desarrollo' : 'Inicial');
const badge = (text, cls = 'bg-slate-100 text-slate-700 ring-slate-200') => `<span class="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset ${cls}">${esc(text)}</span>`;
const levelBadge = (lvl) => badge(lvl, (LEVEL[lvl] || LEVEL['Sin evidencia']).c);
const scoreColor = (s) => (LEVEL[levelOf(s)] || LEVEL['Sin evidencia']).hex;
const STATUS = {
  ENTREGADO: ['Entregado', 'bg-slate-100 text-slate-700 ring-slate-200'],
  EVALUADO_IA: ['Evaluado por IA · pendiente', 'bg-amber-100 text-amber-800 ring-amber-200'],
  PUBLICADO: ['Publicado', 'bg-emerald-100 text-emerald-800 ring-emerald-200'],
};
const statusBadge = (s) => badge(...(STATUS[s] || [s]));

const ICONS = {
  dashboard: 'M3 13h8V3H3v10zm0 8h8v-6H3v6zm10 0h8V11h-8v10zm0-18v6h8V3h-8z',
  folder: 'M10 4H4a2 2 0 00-2 2v12a2 2 0 002 2h16a2 2 0 002-2V8a2 2 0 00-2-2h-8l-2-2z',
  rubric: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4',
  ai: 'M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0112 15a9.065 9.065 0 00-6.23-.693L5 14.5m14.8.8l1.402 1.402c1.232 1.232.65 3.318-1.067 3.611A48.309 48.309 0 0112 21c-2.773 0-5.491-.235-8.135-.687-1.718-.293-2.3-2.379-1.067-3.61L5 14.5',
  grade: 'M12 14l9-5-9-5-9 5 9 5zm0 0l6.16-3.422a12.083 12.083 0 01.665 6.479A11.952 11.952 0 0012 20.055a11.952 11.952 0 00-6.824-2.998 12.078 12.078 0 01.665-6.479L12 14z',
  report: 'M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z',
  map: 'M12 3v4m0 10v4M3 12h4m10 0h4M5.6 5.6l2.8 2.8m7.2 7.2l2.8 2.8M5.6 18.4l2.8-2.8m7.2-7.2l2.8-2.8M12 15a3 3 0 100-6 3 3 0 000 6z',
  users: 'M17 20h5v-2a4 4 0 00-5-3.87M9 20H4v-2a4 4 0 015-3.87m6-4.13a4 4 0 11-8 0 4 4 0 018 0zm6 2a3 3 0 11-6 0 3 3 0 016 0z',
  audit: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z',
  team: 'M12 14l9-5-9-5-9 5 9 5zm0 7v-7',
  logout: 'M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1',
  menu: 'M4 6h16M4 12h16M4 18h16',
  upload: 'M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M16 8l-4-4m0 0L8 8m4-4v12',
  download: 'M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M8 12l4 4m0 0l4-4m-4 4V4',
  plus: 'M12 4v16m8-8H4',
  x: 'M6 18L18 6M6 6l12 12',
  check: 'M5 13l4 4L19 7',
  trash: 'M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6M9 7V4h6v3M4 7h16',
};
const icon = (name, cls = 'w-5 h-5') => `<svg class="${cls}" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" d="${ICONS[name]}"/></svg>`;

// ------------------------------------------------------------------ UI helpers
function toast(msg, type = 'info') {
  const colors = { info: 'bg-slate-900', ok: 'bg-emerald-600', err: 'bg-rose-600', warn: 'bg-amber-600' };
  const el = document.createElement('div');
  el.className = `${colors[type]} text-white text-sm rounded-xl shadow-soft px-4 py-3 fade-in`;
  el.innerHTML = esc(msg);
  $('#toast-root').appendChild(el);
  setTimeout(() => el.remove(), type === 'err' ? 7000 : 3800);
}

function modal(title, bodyHtml, { wide = false } = {}) {
  const root = $('#modal-root');
  root.innerHTML = `
  <div class="fixed inset-0 z-50 flex items-start sm:items-center justify-center bg-slate-900/50 backdrop-blur-sm p-3 overflow-y-auto" data-close>
    <div class="w-full ${wide ? 'max-w-5xl' : 'max-w-xl'} bg-white rounded-2xl shadow-2xl fade-in my-6" role="dialog" aria-modal="true">
      <div class="flex items-center justify-between px-6 py-4 border-b border-slate-100">
        <h3 class="font-bold text-lg text-slate-900">${esc(title)}</h3>
        <button class="p-1.5 rounded-lg hover:bg-slate-100" data-close aria-label="Cerrar">${icon('x')}</button>
      </div>
      <div class="p-6">${bodyHtml}</div>
    </div>
  </div>`;
  root.firstElementChild.addEventListener('click', (e) => { if (e.target.closest('[data-close]') === e.target || e.target.closest('button[data-close]')) closeModal(); });
  return root.firstElementChild;
}
const closeModal = () => ($('#modal-root').innerHTML = '');

const btn = (label, { kind = 'primary', ic = null, attrs = '' } = {}) => {
  const k = {
    primary: 'bg-brand-600 hover:bg-brand-700 text-white shadow-sm',
    ghost: 'bg-white hover:bg-slate-50 text-slate-700 ring-1 ring-inset ring-slate-200',
    success: 'bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm',
    danger: 'bg-white hover:bg-rose-50 text-rose-600 ring-1 ring-inset ring-rose-200',
  }[kind];
  // Fusiona un posible class="..." de attrs (evita atributos duplicados, donde gana el primero)
  let extra = '';
  attrs = attrs.replace(/class="([^"]*)"/, (_, c) => { extra = c; return ''; });
  return `<button ${attrs} class="inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold transition disabled:opacity-50 disabled:cursor-not-allowed ${k} ${extra}">${ic ? icon(ic, 'w-4 h-4') : ''}${label}</button>`;
};
const card = (inner, cls = '') => `<div class="bg-white rounded-2xl shadow-soft ring-1 ring-slate-100 ${cls}">${inner}</div>`;
const input = 'w-full rounded-xl border-0 ring-1 ring-inset ring-slate-200 px-3.5 py-2.5 text-sm focus:ring-2 focus:ring-brand-500 outline-none bg-white';
const label = (t) => `<label class="block text-xs font-semibold text-slate-600 mb-1.5 uppercase tracking-wide">${t}</label>`;
const loading = () => `<div class="flex items-center gap-3 text-slate-500 p-10 justify-center"><div class="spinner"></div> Cargando…</div>`;
const empty = (msg) => `<div class="text-center text-slate-500 py-12 px-4"><div class="mx-auto w-12 h-12 rounded-full bg-slate-100 grid place-items-center mb-3">${icon('folder', 'w-6 h-6 text-slate-400')}</div>${esc(msg)}</div>`;
const pageHeader = (title, subtitle = '', actions = '') => `
  <div class="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4 mb-6">
    <div><h1 class="text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-900">${title}</h1>
    ${subtitle ? `<p class="text-slate-500 mt-1">${subtitle}</p>` : ''}</div>
    <div class="flex flex-wrap gap-2 no-print">${actions}</div>
  </div>`;
const kpi = (title, value, hint = '', accent = 'text-slate-900') => card(`
  <div class="p-5"><p class="text-xs font-semibold uppercase tracking-wide text-slate-500">${title}</p>
  <p class="mt-2 text-3xl font-extrabold ${accent}">${value}</p>${hint ? `<p class="text-xs text-slate-500 mt-1">${hint}</p>` : ''}</div>`);

function destroyCharts() { S.charts.forEach((c) => c.destroy()); S.charts = []; }
function chart(canvasId, config) {
  const el = document.getElementById(canvasId);
  if (!el || !window.Chart) return;
  Chart.defaults.font.family = 'Inter';
  S.charts.push(new Chart(el, config));
}

// ------------------------------------------------------------------ API
async function api(path, { method = 'GET', body, form, raw = false } = {}) {
  const headers = {};
  if (S.token) headers.Authorization = `Bearer ${S.token}`;
  let payload;
  if (form) payload = form;
  else if (body !== undefined) { headers['Content-Type'] = 'application/json'; payload = JSON.stringify(body); }
  const res = await fetch(path, { method, headers, body: payload });
  if (res.status === 401 && S.token) { logout(false); toast('Sesión expirada. Inicie sesión nuevamente.', 'warn'); throw new Error('401'); }
  if (raw) { if (!res.ok) throw new Error(`Error ${res.status}`); return res; }
  const data = res.status === 204 ? null : await res.json().catch(() => null);
  if (!res.ok) {
    const d = data?.detail;
    let msg = `Error ${res.status}`;
    if (typeof d === 'string') msg = d;
    else if (Array.isArray(d)) msg = d.map((x) => `${(x.loc || []).slice(1).join('.')}: ${x.msg}`).join(' · ');
    else if (d?.errors) msg = d.errors.join(' ');
    const err = new Error(msg); err.detail = d; throw err;
  }
  return data;
}
async function downloadFile(path, filename) {
  try {
    const res = await api(path, { raw: true });
    const blob = await res.blob();
    const a = Object.assign(document.createElement('a'), { href: URL.createObjectURL(blob), download: filename });
    a.click(); URL.revokeObjectURL(a.href);
  } catch (e) { toast(e.message, 'err'); }
}

function setSession(token, user) {
  S.token = token; S.user = user;
  localStorage.setItem('api_token', token); localStorage.setItem('api_user', JSON.stringify(user));
}
function logout(redirect = true) {
  S.token = null; S.user = null;
  localStorage.removeItem('api_token'); localStorage.removeItem('api_user');
  if (redirect) location.hash = '#/login';
  render();
}

// ------------------------------------------------------------------ Layout
const NAV = [
  { href: '#/dashboard', label: 'Panel principal', ic: 'dashboard' },
  { href: '#/portfolio', label: 'Portafolio académico', ic: 'folder' },
  { href: '#/rubrics', label: 'Rúbricas', ic: 'rubric', staff: true },
  { href: '#/evaluations', label: 'Supervisión IA', ic: 'ai', staff: true },
  { href: '#/grades', label: 'Mis calificaciones', ic: 'grade', student: true },
  { href: '#/report', label: 'Informe integrado', ic: 'report' },
  { href: '#/mindmap', label: 'Mapa de competencias', ic: 'map' },
  { href: '#/students', label: 'Estudiantes', ic: 'users', staff: true },
  { href: '#/audit', label: 'Trazabilidad', ic: 'audit', staff: true },
  { href: '#/project', label: 'Proyecto y equipo', ic: 'team' },
];

function shell(content) {
  const route = location.hash.split('?')[0] || '#/dashboard';
  const items = NAV.filter((n) => (!n.staff || isStaff()) && (!n.student || !isStaff()));
  const nav = items.map((n) => {
    const active = route.startsWith(n.href);
    return `<a href="${n.href}" class="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition ${active ? 'bg-white/10 text-white' : 'text-slate-300 hover:bg-white/5 hover:text-white'}">${icon(n.ic)}${n.label}</a>`;
  }).join('');
  return `
  <div class="lg:pl-72">
    <aside id="sidebar" class="fixed inset-y-0 left-0 z-40 w-72 -translate-x-full lg:translate-x-0 transition-transform bg-slate-950 text-white flex flex-col">
      <div class="px-6 py-6 flex items-center gap-3 border-b border-white/5">
        <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-brand-500 to-emerald-400 grid place-items-center font-black">AP</div>
        <div><p class="font-bold leading-tight">Asesor Pedagógico</p><p class="text-xs text-slate-400">Inteligente · UManizales</p></div>
      </div>
      <nav class="flex-1 overflow-y-auto scroll-thin px-3 py-4 space-y-1">${nav}</nav>
      <div class="p-4 border-t border-white/5">
        <div class="flex items-center gap-3">
          <div class="w-9 h-9 rounded-full bg-brand-600 grid place-items-center text-sm font-bold">${esc(initials(S.user.full_name))}</div>
          <div class="min-w-0 flex-1"><p class="text-sm font-semibold truncate">${esc(S.user.full_name)}</p><p class="text-xs text-slate-400">${esc(S.user.role)}</p></div>
          <button id="btn-logout" class="p-2 rounded-lg hover:bg-white/10" title="Cerrar sesión">${icon('logout')}</button>
        </div>
      </div>
    </aside>
    <div id="backdrop" class="fixed inset-0 z-30 bg-slate-900/40 hidden lg:hidden"></div>
    <header class="sticky top-0 z-20 bg-white/80 backdrop-blur border-b border-slate-200 lg:hidden flex items-center gap-3 px-4 h-14">
      <button id="btn-menu" class="p-2 -ml-2 rounded-lg hover:bg-slate-100" aria-label="Menú">${icon('menu')}</button>
      <p class="font-bold">Asesor Pedagógico Inteligente</p>
    </header>
    <main class="px-4 sm:px-6 lg:px-10 py-8 max-w-7xl mx-auto fade-in" id="view">${content}</main>
  </div>`;
}

function bindShell() {
  $('#btn-logout')?.addEventListener('click', () => logout());
  const sb = $('#sidebar'), bd = $('#backdrop');
  const toggle = (open) => { sb.classList.toggle('-translate-x-full', !open); bd.classList.toggle('hidden', !open); };
  $('#btn-menu')?.addEventListener('click', () => toggle(true));
  bd?.addEventListener('click', () => toggle(false));
  $$('#sidebar a').forEach((a) => a.addEventListener('click', () => toggle(false)));
}

// ------------------------------------------------------------------ Router
const ROUTES = {
  '#/login': viewLogin,
  '#/dashboard': viewDashboard,
  '#/portfolio': viewPortfolio,
  '#/rubrics': viewRubrics,
  '#/evaluations': viewEvaluations,
  '#/evaluation': viewEvaluationDetail,
  '#/grades': viewGrades,
  '#/report': viewReport,
  '#/mindmap': viewMindmap,
  '#/students': viewStudents,
  '#/audit': viewAudit,
  '#/project': viewProject,
};
const PUBLIC = ['#/login', '#/project'];

function params() { return new URLSearchParams(location.hash.split('?')[1] || ''); }

async function render() {
  destroyCharts(); closeModal();
  let route = location.hash.split('?')[0] || (S.token ? '#/dashboard' : '#/login');
  if (route.startsWith('#/evaluation/')) route = '#/evaluation';
  if (!S.token && !PUBLIC.includes(route)) { location.hash = '#/login'; return; }
  if (S.token && route === '#/login') { location.hash = '#/dashboard'; return; }
  const view = ROUTES[route] || viewDashboard;
  const app = $('#app');
  if (!S.token) { app.innerHTML = ''; await view(app); return; }
  app.innerHTML = shell(loading());
  bindShell();
  try { await view($('#view')); }
  catch (e) { if (e.message !== '401') $('#view').innerHTML = card(`<div class="p-8 text-rose-600">${esc(e.message)}</div>`); }
}
window.addEventListener('hashchange', render);

// ============================================================================ VISTAS
// ---------------------------------------------------------------- Login / Registro
async function viewLogin(root) {
  // No bloquea el primer pintado: en Render Free /api/health puede tardar durante el cold start
  if (!S.health) api('/api/health').then((h) => { S.health = h; if (h?.demo_accounts && !S.token && $('#f-login') && !$('[data-demo]')) render(); }).catch(() => {});
  root.innerHTML = `
  <div class="min-h-screen grid lg:grid-cols-2">
    <section class="relative hidden lg:flex flex-col justify-between p-12 bg-slate-950 text-white overflow-hidden">
      <div class="absolute -top-32 -right-32 w-96 h-96 rounded-full bg-brand-600/40 blur-3xl"></div>
      <div class="absolute bottom-0 -left-20 w-80 h-80 rounded-full bg-emerald-500/20 blur-3xl"></div>
      <div class="relative flex items-center gap-3"><div class="w-11 h-11 rounded-xl bg-gradient-to-br from-brand-500 to-emerald-400 grid place-items-center font-black">AP</div>
      <div><p class="font-bold">Universidad de Manizales</p><p class="text-sm text-slate-400">Ingeniería de Sistemas y Telecomunicaciones</p></div></div>
      <div class="relative">
        <p class="text-brand-300 font-semibold mb-3">Profundización I · Inteligencia Artificial</p>
        <h1 class="text-5xl font-extrabold leading-tight">Asesor Pedagógico<br/><span class="bg-gradient-to-r from-brand-300 to-emerald-300 bg-clip-text text-transparent">Inteligente</span></h1>
        <p class="mt-5 text-slate-300 text-lg max-w-md">Evaluación asistida por IA con calificación determinista, supervisión docente y seguimiento integral del aprendizaje en las Cohortes 1 y 2.</p>
        <div class="mt-8 grid grid-cols-3 gap-4 max-w-md text-sm">
          <div class="rounded-xl bg-white/5 p-3"><p class="font-bold text-xl">100%</p><p class="text-slate-400">Rúbricas validadas</p></div>
          <div class="rounded-xl bg-white/5 p-3"><p class="font-bold text-xl">0,0–5,0</p><p class="text-slate-400">Nota determinista</p></div>
          <div class="rounded-xl bg-white/5 p-3"><p class="font-bold text-xl">JSON</p><p class="text-slate-400">Esquema Pydantic</p></div>
        </div>
      </div>
      <a href="#/project" class="relative text-sm text-slate-400 hover:text-white">Conozca el proyecto y el equipo →</a>
    </section>
    <section class="flex items-center justify-center p-6 sm:p-12">
      <div class="w-full max-w-md">
        <div class="lg:hidden mb-8 text-center"><h1 class="text-3xl font-extrabold">Asesor Pedagógico Inteligente</h1><p class="text-slate-500">Universidad de Manizales</p></div>
        <div class="flex rounded-xl bg-slate-100 p-1 mb-6 text-sm font-semibold">
          <button data-tab="login" class="tab flex-1 rounded-lg py-2 bg-white shadow">Iniciar sesión</button>
          <button data-tab="register" class="tab flex-1 rounded-lg py-2 text-slate-500">Registrarme</button>
        </div>
        <form id="f-login" class="space-y-4">
          <div>${label('Correo institucional')}<input name="email" type="email" required class="${input}" placeholder="usuario@umanizales.edu.co"/></div>
          <div>${label('Contraseña')}<input name="password" type="password" required class="${input}"/></div>
          ${btn('Ingresar', { attrs: 'type="submit" class="w-full"' })}
        </form>
        <form id="f-register" class="space-y-4 hidden">
          <div>${label('Nombre completo')}<input name="full_name" required minlength="3" class="${input}"/></div>
          <div class="grid grid-cols-2 gap-3"><div>${label('Correo')}<input name="email" type="email" required class="${input}"/></div>
          <div>${label('Código estudiantil')}<input name="student_code" class="${input}"/></div></div>
          <div>${label('Contraseña (mín. 8)')}<input name="password" type="password" minlength="8" required class="${input}"/></div>
          ${btn('Crear cuenta de estudiante', { attrs: 'type="submit"' })}
          <p class="text-xs text-slate-500">Las cuentas de docente y administrador son creadas por un administrador (RBAC).</p>
        </form>
        ${S.health?.demo_accounts ? `
        <div class="mt-8 rounded-2xl bg-brand-50 ring-1 ring-brand-100 p-4 text-sm">
          <p class="font-semibold text-brand-900 mb-2">Cuentas de demostración · contraseña <code class="font-mono">Demo2026*</code></p>
          <div class="grid gap-1.5">${[['docente@umanizales.edu.co', 'Docente'], ['ana.rios@umanizales.edu.co', 'Estudiante'], ['admin@umanizales.edu.co', 'Administrador']]
            .map(([e, r]) => `<button type="button" data-demo="${e}" class="text-left rounded-lg px-3 py-1.5 bg-white hover:bg-brand-100 ring-1 ring-brand-100"><span class="font-mono text-xs">${e}</span> <span class="text-brand-700 text-xs font-semibold">· ${r}</span></button>`).join('')}</div>
        </div>` : ''}
      </div>
    </section>
  </div>`;

  $$('.tab', root).forEach((t) => t.addEventListener('click', () => {
    $$('.tab', root).forEach((x) => x.className = 'tab flex-1 rounded-lg py-2 text-slate-500');
    t.className = 'tab flex-1 rounded-lg py-2 bg-white shadow';
    $('#f-login').classList.toggle('hidden', t.dataset.tab !== 'login');
    $('#f-register').classList.toggle('hidden', t.dataset.tab !== 'register');
  }));
  $$('[data-demo]', root).forEach((b) => b.addEventListener('click', () => {
    $('#f-login [name=email]').value = b.dataset.demo; $('#f-login [name=password]').value = 'Demo2026*';
  }));
  const submit = (formId, path) => $(formId).addEventListener('submit', async (e) => {
    e.preventDefault();
    const b = e.target.querySelector('button[type=submit]'); b.disabled = true;
    try {
      const body = Object.fromEntries(new FormData(e.target));
      if (!body.student_code) delete body.student_code;
      const r = await api(path, { method: 'POST', body });
      setSession(r.access_token, r.user);
      toast(`Bienvenido(a), ${r.user.full_name}`, 'ok');
      location.hash = '#/dashboard';
    } catch (err) { toast(err.message, 'err'); } finally { b.disabled = false; }
  });
  submit('#f-login', '/api/auth/login');
  submit('#f-register', '/api/auth/register');
}

// ---------------------------------------------------------------- Dashboard
async function viewDashboard(root) {
  if (isStaff()) return dashboardStaff(root);
  return dashboardStudent(root);
}

async function dashboardStaff(root) {
  const [ov, pending] = await Promise.all([api('/api/reports/overview'), api('/api/evaluations?pending=true')]);
  const subsTotal = ov.cohorts.reduce((a, c) => a + c.submissions, 0);
  const pubTotal = ov.cohorts.reduce((a, c) => a + c.published, 0);
  root.innerHTML = `
    ${pageHeader(`Hola, ${esc(S.user.full_name.split(' ')[0])}`, 'Panorama analítico del rendimiento en Cohorte 1 y Cohorte 2')}
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      ${kpi('Estudiantes', ov.students)}
      ${kpi('Entregas', subsTotal)}
      ${kpi('Notas publicadas', pubTotal, '', 'text-emerald-600')}
      ${kpi('Pendientes de revisión', pending.length, 'Evaluadas por IA, sin aprobar', pending.length ? 'text-amber-600' : '')}
    </div>
    <div class="grid lg:grid-cols-3 gap-6 mb-6">
      ${card(`<div class="p-6"><h3 class="font-bold mb-4">Promedio por laboratorio</h3><div class="h-72"><canvas id="ch-labs"></canvas></div></div>`, 'lg:col-span-2')}
      ${card(`<div class="p-6"><h3 class="font-bold mb-4">Cohortes</h3><div class="space-y-4">${ov.cohorts.map((c) => `
        <div class="rounded-xl ring-1 ring-slate-100 p-4"><div class="flex justify-between items-center"><p class="font-semibold">${esc(c.name)}</p>${levelBadge(levelOf(c.average))}</div>
        <div class="mt-3 grid grid-cols-3 text-center text-sm"><div><p class="text-2xl font-extrabold" style="color:${scoreColor(c.average)}">${fmt(c.average)}</p><p class="text-slate-500 text-xs">Promedio</p></div>
        <div><p class="text-2xl font-extrabold">${c.pass_rate == null ? '—' : fmt(c.pass_rate, 0) + '%'}</p><p class="text-slate-500 text-xs">Aprobación</p></div>
        <div><p class="text-2xl font-extrabold">${c.published}/${c.submissions}</p><p class="text-slate-500 text-xs">Publicadas</p></div></div></div>`).join('')}</div></div>`)}
    </div>
    <div class="grid lg:grid-cols-2 gap-6">
      ${card(`<div class="p-6"><h3 class="font-bold mb-4">Dominio global por competencia</h3><div class="h-72"><canvas id="ch-comp"></canvas></div></div>`)}
      ${card(`<div class="p-6"><div class="flex justify-between items-center mb-4"><h3 class="font-bold">Cola de supervisión docente</h3><a href="#/evaluations" class="text-sm text-brand-600 font-semibold">Ver todo →</a></div>
        ${pending.length ? `<ul class="divide-y divide-slate-100">${pending.slice(0, 6).map((e) => `
          <li class="py-3 flex items-center justify-between gap-3"><div class="min-w-0"><p class="font-semibold truncate">${esc(e.student_name)}</p><p class="text-xs text-slate-500 truncate">${esc(e.laboratory_title)}</p></div>
          <div class="flex items-center gap-3"><span class="font-extrabold" style="color:${scoreColor(e.calculated_score)}">${fmt(e.calculated_score)}</span><a href="#/evaluation/${e.id}" class="text-sm font-semibold text-brand-600">Revisar</a></div></li>`).join('')}</ul>`
        : empty('No hay evaluaciones pendientes de aprobación.')}</div>`)}
    </div>
    ${card(`<div class="p-6"><h3 class="font-bold mb-4">Ranking de estudiantes (notas publicadas)</h3>${ov.students_summary.length ? `
      <div class="overflow-x-auto"><table class="w-full text-sm"><thead class="text-left text-slate-500"><tr><th class="py-2">Estudiante</th><th>Labs</th><th>Promedio</th><th>Nivel</th><th></th></tr></thead><tbody class="divide-y divide-slate-100">
      ${ov.students_summary.map((s) => `<tr><td class="py-2.5 font-medium">${esc(s.full_name)}</td><td>${s.labs}</td><td class="font-bold" style="color:${scoreColor(s.average)}">${fmt(s.average, 2)}</td><td>${levelBadge(levelOf(s.average))}</td>
      <td class="text-right"><a class="text-brand-600 font-semibold" href="#/report?student=${s.student_id}">Informe →</a></td></tr>`).join('')}</tbody></table></div>` : empty('Aún no hay notas publicadas.')}</div>`, 'mt-6')}`;

  const labs = ov.cohorts.flatMap((c) => c.labs.map((l) => ({ ...l, cohort: c.name })));
  chart('ch-labs', { type: 'bar', data: { labels: labs.map((l) => l.title.replace(/^Lab \d+ · /, '')), datasets: [{ label: 'Promedio', data: labs.map((l) => l.average), backgroundColor: labs.map((l) => scoreColor(l.average)), borderRadius: 8 }] },
    options: { maintainAspectRatio: false, scales: { y: { min: 0, max: 5 } }, plugins: { legend: { display: false } } } });
  chart('ch-comp', { type: 'bar', data: { labels: ov.competencies.map((c) => c.name), datasets: [{ data: ov.competencies.map((c) => c.average), backgroundColor: ov.competencies.map((c) => scoreColor(c.average)), borderRadius: 6 }] },
    options: { indexAxis: 'y', maintainAspectRatio: false, scales: { x: { min: 0, max: 5 } }, plugins: { legend: { display: false } } } });
}

async function dashboardStudent(root) {
  const [rep, evs] = await Promise.all([api('/api/reports/student'), api('/api/evaluations')]);
  root.innerHTML = `
    ${pageHeader(`Hola, ${esc(S.user.full_name.split(' ')[0])}`, 'Tu progreso de aprendizaje en Inteligencia Artificial', `<a href="#/portfolio">${btn('Nueva entrega', { ic: 'upload' })}</a>`)}
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      ${kpi('Promedio general', fmt(rep.overall_average), rep.overall_level, '')}
      ${kpi('Laboratorios evaluados', `${rep.evaluated_labs}/${rep.total_labs}`)}
      ${kpi('Evolución C1 → C2', rep.trend_between_cohorts == null ? '—' : (rep.trend_between_cohorts >= 0 ? '+' : '') + fmt(rep.trend_between_cohorts, 2), 'puntos', rep.trend_between_cohorts >= 0 ? 'text-emerald-600' : 'text-rose-600')}
      ${kpi('Brechas detectadas', rep.gaps.length, 'competencias < 3,5', rep.gaps.length ? 'text-amber-600' : 'text-emerald-600')}
    </div>
    <div class="grid lg:grid-cols-3 gap-6">
      ${card(`<div class="p-6"><h3 class="font-bold mb-4">Evolución del aprendizaje</h3><div class="h-72"><canvas id="ch-evo"></canvas></div></div>`, 'lg:col-span-2')}
      ${card(`<div class="p-6"><h3 class="font-bold mb-4">Últimas retroalimentaciones</h3>${evs.length ? `<ul class="space-y-3">${evs.slice(0, 4).map((e) => `
        <li><a href="#/evaluation/${e.id}" class="block rounded-xl ring-1 ring-slate-100 hover:ring-brand-200 p-3"><div class="flex justify-between"><p class="font-semibold text-sm">${esc(e.laboratory_title)}</p><span class="font-extrabold" style="color:${scoreColor(e.calculated_score)}">${fmt(e.calculated_score)}</span></div>
        <p class="text-xs text-slate-500 mt-1 line-clamp-2">${esc(e.general_summary)}</p></a></li>`).join('')}</ul>` : empty('Aún no tienes notas publicadas.')}</div>`)}
    </div>`;
  chart('ch-evo', { type: 'line', data: { labels: rep.evolution.map((e) => e.label.replace(/ · .*/, '')), datasets: [{ label: 'Nota', data: rep.evolution.map((e) => e.score), borderColor: '#4f46e5', backgroundColor: 'rgba(79,70,229,.12)', fill: true, tension: .35, pointRadius: 5 }] },
    options: { maintainAspectRatio: false, scales: { y: { min: 0, max: 5 } }, plugins: { legend: { display: false } } } });
}

// ---------------------------------------------------------------- Portafolio
async function viewPortfolio(root) {
  const [cohorts, subs, students] = await Promise.all([
    api('/api/cohorts'), api('/api/submissions'), isStaff() ? api('/api/users?role=ESTUDIANTE') : Promise.resolve([]),
  ]);
  const p = params();
  const activeCohort = Number(p.get('cohort')) || cohorts[0]?.id;
  const co = cohorts.find((c) => c.id === activeCohort) || cohorts[0];

  root.innerHTML = `
    ${pageHeader('Portafolio académico', 'Entregas organizadas por Cohorte y laboratorio (RF-201 / RF-202)', btn('Cargar entrega', { ic: 'upload', attrs: 'id="btn-upload"' }) + (isStaff() ? btn('Nuevo laboratorio', { kind: 'ghost', ic: 'plus', attrs: 'id="btn-lab"' }) : ''))}
    <div class="flex gap-2 mb-6 overflow-x-auto">${cohorts.map((c) => `<a href="#/portfolio?cohort=${c.id}" class="whitespace-nowrap rounded-xl px-4 py-2 text-sm font-semibold ${c.id === co?.id ? 'bg-slate-900 text-white' : 'bg-white ring-1 ring-slate-200 text-slate-600'}">${esc(c.name)}</a>`).join('')}</div>
    ${co ? `<p class="text-slate-600 mb-5">${esc(co.description)}</p>
    <div class="space-y-6">${co.laboratories.map((lab) => {
      const ls = subs.filter((s) => s.laboratory_id === lab.id);
      return card(`
        <div class="p-6 border-b border-slate-100 flex flex-col md:flex-row md:items-start md:justify-between gap-4">
          <div><h3 class="font-bold text-lg">${esc(lab.title)}</h3><p class="text-sm text-slate-500 mt-1">${esc(lab.objectives)}</p>
          <div class="flex flex-wrap gap-1.5 mt-3">${lab.competencies.map((c) => badge(c, 'bg-brand-50 text-brand-700 ring-brand-100')).join('')}</div></div>
          <div class="flex items-center gap-2 shrink-0">${lab.has_active_rubric ? badge('Rúbrica activa ✓', 'bg-emerald-50 text-emerald-700 ring-emerald-200') : badge('Sin rúbrica activa', 'bg-rose-50 text-rose-700 ring-rose-200')}
          ${btn('Entregar', { kind: 'ghost', ic: 'upload', attrs: `data-upload-lab="${lab.id}"` })}</div>
        </div>
        <div class="p-2 sm:p-4">${ls.length ? `<div class="overflow-x-auto"><table class="w-full text-sm"><thead class="text-left text-slate-500"><tr>
          ${isStaff() ? '<th class="px-3 py-2">Estudiante</th>' : ''}<th class="px-3 py-2">Evidencias</th><th class="px-3 py-2">Fecha</th><th class="px-3 py-2">Estado</th><th class="px-3 py-2">Nota</th><th class="px-3 py-2"></th></tr></thead>
          <tbody class="divide-y divide-slate-100">${ls.map((s) => `<tr class="align-top">
            ${isStaff() ? `<td class="px-3 py-3 font-medium">${esc(s.student_name)}</td>` : ''}
            <td class="px-3 py-3"><div class="flex flex-wrap gap-1.5">
              ${s.pdf_original_name ? `<button data-pdf="${s.id}" data-name="${esc(s.pdf_original_name)}" class="text-xs rounded-lg bg-rose-50 text-rose-700 px-2 py-1 font-semibold ${s.has_pdf ? 'hover:bg-rose-100' : 'cursor-default'}" title="${s.pdf_text_chars} caracteres extraídos">PDF · ${esc(s.pdf_original_name)}</button>` : ''}
              ${s.has_code_zip ? `<span class="text-xs rounded-lg bg-sky-50 text-sky-700 px-2 py-1 font-semibold" title="${esc(Object.entries(s.code_manifest.by_extension || {}).map(([k, v]) => `${k}:${v}`).join(' '))}">ZIP · ${s.code_manifest.total_files} archivos</span>` : ''}
              ${s.repo_url ? `<a href="${esc(s.repo_url)}" target="_blank" rel="noopener" class="text-xs rounded-lg bg-slate-100 text-slate-700 px-2 py-1 font-semibold hover:bg-slate-200">GitHub ↗</a>` : ''}
            </div>${s.notes ? `<p class="text-xs text-slate-500 mt-1.5">${esc(s.notes)}</p>` : ''}</td>
            <td class="px-3 py-3 whitespace-nowrap text-slate-500">${fdate(s.submitted_at)}</td>
            <td class="px-3 py-3">${statusBadge(s.status)}</td>
            <td class="px-3 py-3 font-extrabold" style="color:${scoreColor(s.latest_score)}">${fmt(s.latest_score)}</td>
            <td class="px-3 py-3 text-right whitespace-nowrap">
              ${isStaff() ? (lab.has_active_rubric ? btn(s.latest_evaluation_id ? 'Re-evaluar IA' : 'Evaluar con IA', { kind: s.latest_evaluation_id ? 'ghost' : 'primary', ic: 'ai', attrs: `data-eval="${s.id}"` }) : '') : ''}
              ${s.latest_evaluation_id ? `<a href="#/evaluation/${s.latest_evaluation_id}" class="ml-2 text-sm font-semibold text-brand-600">Ver</a>` : ''}
            </td></tr>`).join('')}</tbody></table></div>` : empty('Sin entregas para este laboratorio.')}</div>`);
    }).join('')}</div>` : empty('No hay cohortes configuradas.')}`;

  const allLabs = cohorts.flatMap((c) => c.laboratories.map((l) => ({ ...l, cohort: c.name })));
  const openUpload = (labId) => {
    const m = modal('Cargar entrega', `
      <form id="f-sub" class="space-y-4">
        <div>${label('Laboratorio')}<select name="laboratory_id" required class="${input}">${allLabs.map((l) => `<option value="${l.id}" ${l.id == labId ? 'selected' : ''}>${esc(l.cohort)} — ${esc(l.title)}</option>`).join('')}</select></div>
        ${isStaff() ? `<div>${label('Estudiante')}<select name="student_id" required class="${input}">${students.map((s) => `<option value="${s.id}">${esc(s.full_name)} (${esc(s.email)})</option>`).join('')}</select></div>` : ''}
        <div>${label('Informe PDF (texto legible, máx. 10 MB)')}<input name="pdf" type="file" accept="application/pdf,.pdf" class="${input} file:mr-3 file:rounded-lg file:border-0 file:bg-brand-50 file:px-3 file:py-1 file:text-brand-700"/></div>
        <div>${label('Código fuente (.zip)')}<input name="code_zip" type="file" accept=".zip,application/zip" class="${input} file:mr-3 file:rounded-lg file:border-0 file:bg-brand-50 file:px-3 file:py-1 file:text-brand-700"/></div>
        <div>${label('Repositorio GitHub')}<input name="repo_url" type="url" placeholder="https://github.com/usuario/repositorio" class="${input}"/></div>
        <div>${label('Notas')}<textarea name="notes" rows="2" class="${input}"></textarea></div>
        <div class="rounded-xl bg-slate-50 p-3 text-xs text-slate-500">🔒 El código nunca se ejecuta en el servidor: se analiza estáticamente (protección Zip-Slip / Zip-Bomb).</div>
        <div class="flex justify-end gap-2">${btn('Cancelar', { kind: 'ghost', attrs: 'type="button" data-close' })}${btn('Subir entrega', { ic: 'upload', attrs: 'type="submit"' })}</div>
      </form>`);
    $('#f-sub', m).addEventListener('submit', async (e) => {
      e.preventDefault();
      const fd = new FormData(e.target);
      ['pdf', 'code_zip'].forEach((k) => { if (!fd.get(k)?.size) fd.delete(k); });
      if (!fd.get('repo_url')) fd.delete('repo_url');
      const b = e.target.querySelector('[type=submit]'); b.disabled = true; b.innerHTML = '<div class="spinner !w-4 !h-4"></div> Procesando…';
      try { await api('/api/submissions', { method: 'POST', form: fd }); toast('Entrega cargada correctamente.', 'ok'); render(); }
      catch (err) { toast(err.message, 'err'); b.disabled = false; b.textContent = 'Subir entrega'; }
    });
  };
  $('#btn-upload')?.addEventListener('click', () => openUpload(co?.laboratories[0]?.id));
  $$('[data-upload-lab]').forEach((b) => b.addEventListener('click', () => openUpload(b.dataset.uploadLab)));
  $$('[data-pdf]').forEach((b) => b.addEventListener('click', () => downloadFile(`/api/submissions/${b.dataset.pdf}/pdf`, b.dataset.name)));
  $$('[data-eval]').forEach((b) => b.addEventListener('click', () => runEvaluation(b.dataset.eval, b)));
  $('#btn-lab')?.addEventListener('click', () => {
    const m = modal('Nuevo laboratorio', `<form id="f-lab" class="space-y-4">
      <div>${label('Cohorte')}<select name="cohort_id" class="${input}">${cohorts.map((c) => `<option value="${c.id}" ${c.id === co?.id ? 'selected' : ''}>${esc(c.name)}</option>`).join('')}</select></div>
      <div>${label('Título')}<input name="title" required class="${input}"/></div>
      <div>${label('Objetivos')}<textarea name="objectives" rows="3" class="${input}"></textarea></div>
      <div>${label('Competencias IA (separadas por coma)')}<input name="competencies" class="${input}" placeholder="Redes neuronales, Evaluación de modelos"/></div>
      <div>${label('Orden')}<input name="order" type="number" value="${allLabs.length + 1}" class="${input}"/></div>
      <div class="flex justify-end">${btn('Crear laboratorio', { attrs: 'type="submit"' })}</div></form>`);
    $('#f-lab', m).addEventListener('submit', async (e) => {
      e.preventDefault();
      const d = Object.fromEntries(new FormData(e.target));
      try {
        await api('/api/laboratories', { method: 'POST', body: { ...d, cohort_id: +d.cohort_id, order: +d.order, competencies: d.competencies.split(',').map((x) => x.trim()).filter(Boolean) } });
        toast('Laboratorio creado.', 'ok'); render();
      } catch (err) { toast(err.message, 'err'); }
    });
  });
}

async function runEvaluation(submissionId, b) {
  const old = b.innerHTML; b.disabled = true; b.innerHTML = '<div class="spinner !w-4 !h-4"></div> Evaluando…';
  try {
    const ev = await api(`/api/submissions/${submissionId}/evaluate`, { method: 'POST' });
    toast(`Evaluación generada (${ev.ai_provider}). Nota calculada: ${fmt(ev.calculated_score)}`, 'ok');
    location.hash = `#/evaluation/${ev.id}`;
  } catch (err) { toast(err.message, 'err'); b.disabled = false; b.innerHTML = old; }
}

// ---------------------------------------------------------------- Rúbricas
const DEFAULT_LEVELS = [
  { label: 'Inicial', min_score: 0, max_score: 2.9, descriptor: 'Evidencia ausente o con errores conceptuales.' },
  { label: 'En desarrollo', min_score: 3, max_score: 3.9, descriptor: 'Cumple parcialmente; falta justificación.' },
  { label: 'Competente', min_score: 4, max_score: 4.5, descriptor: 'Cumple con solidez técnica.' },
  { label: 'Sobresaliente', min_score: 4.6, max_score: 5, descriptor: 'Supera lo esperado con análisis crítico.' },
];

async function viewRubrics(root) {
  const [rubrics, cohorts] = await Promise.all([api('/api/rubrics'), api('/api/cohorts')]);
  const labs = cohorts.flatMap((c) => c.laboratories.map((l) => ({ ...l, cohort: c.name })));
  root.innerHTML = `
    ${pageHeader('Rúbricas', 'Parametrización con validación matemática estricta del 100 % (RF-203 / RF-204)', btn('Nueva rúbrica', { ic: 'plus', attrs: 'id="btn-new"' }) + btn('Importar JSON', { kind: 'ghost', attrs: 'id="btn-import"' }))}
    <div class="grid md:grid-cols-2 gap-5">${labs.map((lab) => {
      const rs = rubrics.filter((r) => r.laboratory_id === lab.id);
      return card(`<div class="p-5"><p class="text-xs font-semibold text-brand-600 uppercase">${esc(lab.cohort)}</p><h3 class="font-bold">${esc(lab.title)}</h3>
        ${rs.length ? rs.map((r) => `<div class="mt-4 rounded-xl ring-1 ${r.is_active ? 'ring-emerald-200 bg-emerald-50/40' : 'ring-slate-100'} p-4">
          <div class="flex justify-between items-start gap-2"><p class="font-semibold text-sm">${esc(r.name)}</p>${r.is_active ? badge('Activa', 'bg-emerald-100 text-emerald-800 ring-emerald-200') : badge('Inactiva')}</div>
          <div class="mt-3 space-y-1.5">${r.criteria.map((c) => `<div class="flex items-center gap-2 text-xs"><span class="font-mono text-slate-400 w-8">${esc(c.id)}</span><span class="flex-1 truncate">${esc(c.name)}</span>
            <div class="w-24 h-1.5 rounded-full bg-slate-100"><div class="h-1.5 rounded-full bg-brand-500" style="width:${c.weight}%"></div></div><span class="w-10 text-right font-semibold">${c.weight}%</span></div>`).join('')}</div>
          <div class="mt-3 flex justify-between items-center text-xs"><span class="font-semibold ${Math.abs(r.total_weight - 100) < 1e-9 ? 'text-emerald-600' : 'text-rose-600'}">Σ = ${r.total_weight}%</span>
          <div class="flex gap-3">${!r.is_active ? `<button data-activate="${r.id}" class="font-semibold text-emerald-700">Activar</button>` : ''}<button data-edit="${r.id}" class="font-semibold text-brand-600">Editar / duplicar</button></div></div></div>`).join('')
        : `<div class="mt-4 rounded-xl border-2 border-dashed border-slate-200 p-5 text-center text-sm text-slate-500">Sin rúbrica. <button data-new-lab="${lab.id}" class="text-brand-600 font-semibold">Crear</button></div>`}</div>`);
    }).join('')}</div>`;

  const open = (preset) => rubricBuilder(labs, preset);
  $('#btn-new').addEventListener('click', () => open({ laboratory_id: labs[0]?.id }));
  $$('[data-new-lab]').forEach((b) => b.addEventListener('click', () => open({ laboratory_id: +b.dataset.newLab })));
  $$('[data-edit]').forEach((b) => b.addEventListener('click', () => open(rubrics.find((r) => r.id === +b.dataset.edit))));
  $$('[data-activate]').forEach((b) => b.addEventListener('click', async () => {
    try { await api(`/api/rubrics/${b.dataset.activate}/activate`, { method: 'POST' }); toast('Rúbrica activada.', 'ok'); render(); } catch (e) { toast(e.message, 'err'); }
  }));
  $('#btn-import').addEventListener('click', () => {
    const m = modal('Importar rúbrica (JSON)', `<p class="text-sm text-slate-500 mb-3">Formato: <code class="font-mono text-xs">{"laboratory_id":1,"name":"…","criteria":[{"id":"C1","name":"…","competency":"…","description":"…","weight":40}]}</code></p>
      <textarea id="json-in" rows="12" class="${input} font-mono text-xs"></textarea><div class="flex justify-end mt-4">${btn('Cargar en el editor', { attrs: 'id="btn-parse"' })}</div>`, { wide: true });
    $('#btn-parse', m).addEventListener('click', () => {
      try { const data = JSON.parse($('#json-in').value); open(data); } catch (e) { toast('JSON inválido: ' + e.message, 'err'); }
    });
  });
}

function rubricBuilder(labs, preset = {}) {
  const editingId = preset.id && preset.is_active !== undefined ? preset.id : null;
  let criteria = (preset.criteria || [{ id: 'C1', name: '', competency: '', description: '', weight: 100 }]).map((c) => ({ ...c, levels: c.levels?.length ? c.levels : DEFAULT_LEVELS }));
  const m = modal(editingId ? 'Editar rúbrica' : 'Nueva rúbrica', `
    <form id="f-rub" class="space-y-5">
      <div class="grid sm:grid-cols-2 gap-4">
        <div>${label('Laboratorio')}<select name="laboratory_id" class="${input}">${labs.map((l) => `<option value="${l.id}" ${l.id == preset.laboratory_id ? 'selected' : ''}>${esc(l.cohort)} — ${esc(l.title)}</option>`).join('')}</select></div>
        <div>${label('Nombre')}<input name="name" required minlength="3" value="${esc(preset.name || '')}" class="${input}"/></div>
      </div>
      <div><div class="flex items-center justify-between mb-2"><p class="text-sm font-bold">Criterios</p>${btn('Agregar criterio', { kind: 'ghost', ic: 'plus', attrs: 'type="button" id="btn-add"' })}</div>
      <div id="crit-list" class="space-y-3"></div></div>
      <div id="sum-box" class="rounded-xl p-4"></div>
      <datalist id="comp-list"></datalist>
      <label class="flex items-center gap-2 text-sm"><input type="checkbox" name="activate" checked class="rounded"> Activar para evaluación al guardar (desactiva otras rúbricas del laboratorio)</label>
      <div class="flex flex-wrap justify-end gap-2">${btn('Validar en servidor', { kind: 'ghost', attrs: 'type="button" id="btn-val"' })}${editingId ? btn('Guardar cambios', { attrs: 'type="submit" data-mode="update"' }) : ''}${btn(editingId ? 'Guardar como nueva' : 'Guardar rúbrica', { kind: editingId ? 'ghost' : 'primary', attrs: 'type="submit" data-mode="create"' })}</div>
    </form>`, { wide: true });

  const labSel = $('[name=laboratory_id]', m);
  const fillComps = () => { const lab = labs.find((l) => l.id == labSel.value); $('#comp-list', m).innerHTML = (lab?.competencies || []).map((c) => `<option value="${esc(c)}">`).join(''); };
  labSel.addEventListener('change', fillComps); fillComps();

  const draw = () => {
    $('#crit-list', m).innerHTML = criteria.map((c, i) => `
      <div class="grid grid-cols-12 gap-2 items-start rounded-xl ring-1 ring-slate-100 p-3" data-i="${i}">
        <input data-k="id" value="${esc(c.id)}" class="${input} col-span-3 sm:col-span-1 font-mono" placeholder="ID"/>
        <input data-k="name" value="${esc(c.name)}" class="${input} col-span-9 sm:col-span-4" placeholder="Nombre del criterio"/>
        <input data-k="competency" list="comp-list" value="${esc(c.competency)}" class="${input} col-span-7 sm:col-span-3" placeholder="Competencia IA"/>
        <div class="col-span-4 sm:col-span-3 relative"><input data-k="weight" type="number" step="0.01" min="0" max="100" value="${c.weight}" class="${input} pr-8 font-semibold"/><span class="absolute right-3 top-2.5 text-slate-400 text-sm">%</span></div>
        <button type="button" data-del="${i}" class="col-span-1 p-2.5 text-rose-500 hover:bg-rose-50 rounded-lg" title="Eliminar">${icon('trash', 'w-4 h-4')}</button>
        <textarea data-k="description" rows="1" class="${input} col-span-12" placeholder="Descriptor de desempeño esperado">${esc(c.description)}</textarea>
      </div>`).join('');
    $$('#crit-list [data-k]', m).forEach((el) => el.addEventListener('input', () => {
      const i = +el.closest('[data-i]').dataset.i; const k = el.dataset.k;
      criteria[i][k] = k === 'weight' ? parseFloat(el.value || '0') : el.value; updateSum();
    }));
    $$('[data-del]', m).forEach((b) => b.addEventListener('click', () => { criteria.splice(+b.dataset.del, 1); draw(); }));
    updateSum();
  };
  // Suma exacta en centésimas enteras (evita error de coma flotante, igual que Decimal en backend)
  const updateSum = () => {
    const cents = criteria.reduce((a, c) => a + Math.round((Number(c.weight) || 0) * 100), 0);
    const total = cents / 100, ok = cents === 10000;
    $('#sum-box', m).className = `rounded-xl p-4 ${ok ? 'bg-emerald-50 ring-1 ring-emerald-200' : 'bg-rose-50 ring-1 ring-rose-200'}`;
    $('#sum-box', m).innerHTML = `<div class="flex justify-between text-sm font-semibold mb-2"><span>${ok ? '✓ Ponderación válida' : '✕ La suma debe ser exactamente 100 %'}</span><span class="font-mono">Σ = ${total}%${ok ? '' : ` (${total > 100 ? '+' : ''}${(total - 100).toFixed(2)})`}</span></div>
      <div class="h-2.5 rounded-full bg-white overflow-hidden"><div class="h-full ${ok ? 'bg-emerald-500' : total > 100 ? 'bg-rose-500' : 'bg-amber-500'}" style="width:${Math.min(100, total)}%"></div></div>`;
    $$('[data-mode]', m).forEach((b) => (b.disabled = !ok));
  };
  draw();
  $('#btn-add', m).addEventListener('click', () => { criteria.push({ id: `C${criteria.length + 1}`, name: '', competency: '', description: '', weight: 0, levels: DEFAULT_LEVELS }); draw(); });

  const payload = () => ({ laboratory_id: +labSel.value, name: $('[name=name]', m).value, activate: $('[name=activate]', m).checked, criteria });
  $('#btn-val', m).addEventListener('click', async () => {
    try { const v = await api('/api/rubrics/validate', { method: 'POST', body: payload() }); toast(v.valid ? `Rúbrica válida (Σ = ${v.total_weight}%)` : v.errors.join(' '), v.valid ? 'ok' : 'err'); }
    catch (e) { toast(e.message, 'err'); }
  });
  let mode = 'create';
  $$('[data-mode]', m).forEach((b) => b.addEventListener('click', () => (mode = b.dataset.mode)));
  $('#f-rub', m).addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      if (mode === 'update') await api(`/api/rubrics/${editingId}`, { method: 'PUT', body: payload() });
      else await api('/api/rubrics', { method: 'POST', body: payload() });
      toast('Rúbrica guardada y validada al 100 %.', 'ok'); render();
    } catch (err) { toast(err.message, 'err'); }
  });
}

// ---------------------------------------------------------------- Supervisión IA
async function viewEvaluations(root) {
  const tab = params().get('tab') || 'pending';
  const [evs, subs, ai] = await Promise.all([api('/api/evaluations'), api('/api/submissions'), api('/api/ai/status')]);
  const pending = evs.filter((e) => !e.teacher_approved), published = evs.filter((e) => e.teacher_approved);
  const unevaluated = subs.filter((s) => !s.latest_evaluation_id);
  const tabs = [['pending', `Pendientes (${pending.length})`], ['new', `Sin evaluar (${unevaluated.length})`], ['published', `Publicadas (${published.length})`]];
  const evTable = (list) => list.length ? `<div class="overflow-x-auto"><table class="w-full text-sm"><thead class="text-left text-slate-500"><tr><th class="px-4 py-3">Estudiante</th><th>Laboratorio</th><th>Proveedor IA</th><th>Nota</th><th>Estado</th><th></th></tr></thead><tbody class="divide-y divide-slate-100">
    ${list.map((e) => `<tr><td class="px-4 py-3 font-medium">${esc(e.student_name)}</td><td>${esc(e.laboratory_title)}<p class="text-xs text-slate-400">${esc(e.cohort_name)}</p></td><td class="text-xs font-mono text-slate-500">${esc(e.ai_provider)}</td>
    <td class="font-extrabold" style="color:${scoreColor(e.calculated_score)}">${fmt(e.calculated_score)}${e.adjusted ? ' <span class="text-xs text-amber-600" title="Ajustada por docente">✎</span>' : ''}</td><td>${e.teacher_approved ? statusBadge('PUBLICADO') : statusBadge('EVALUADO_IA')}</td>
    <td class="text-right pr-4"><a href="#/evaluation/${e.id}" class="font-semibold text-brand-600">${e.teacher_approved ? 'Ver' : 'Revisar →'}</a></td></tr>`).join('')}</tbody></table></div>` : empty('Nada por aquí.');

  root.innerHTML = `
    ${pageHeader('Supervisión de evaluaciones IA', 'Revise, ajuste y apruebe las calificaciones antes de publicarlas (RF-208)')}
    ${card(`<div class="p-4 flex flex-wrap items-center gap-3 text-sm">${icon('ai', 'w-5 h-5 text-brand-600')}<span>Motor activo: <b class="font-mono">${esc(ai.provider)}</b>${ai.model ? ` · modelo <b class="font-mono">${esc(ai.model)}</b>` : ''}</span>
      ${ai.configured ? badge('LLM conectado', 'bg-emerald-100 text-emerald-800 ring-emerald-200') : badge('Modo determinista (sin API key)', 'bg-amber-100 text-amber-800 ring-amber-200')}
      <span class="text-slate-500">La IA aporta puntajes parciales y evidencias; <b>la nota final la calcula el backend</b>.</span></div>`, 'mb-6')}
    <div class="flex gap-2 mb-4">${tabs.map(([k, l]) => `<a href="#/evaluations?tab=${k}" class="rounded-xl px-4 py-2 text-sm font-semibold ${k === tab ? 'bg-slate-900 text-white' : 'bg-white ring-1 ring-slate-200 text-slate-600'}">${l}</a>`).join('')}</div>
    ${card(tab === 'new' ? (unevaluated.length ? `<div class="overflow-x-auto"><table class="w-full text-sm"><thead class="text-left text-slate-500"><tr><th class="px-4 py-3">Estudiante</th><th>Laboratorio</th><th>Entregado</th><th></th></tr></thead><tbody class="divide-y divide-slate-100">
      ${unevaluated.map((s) => `<tr><td class="px-4 py-3 font-medium">${esc(s.student_name)}</td><td>${esc(s.laboratory_title)}</td><td class="text-slate-500">${fdate(s.submitted_at)}</td><td class="text-right pr-4 py-2">${btn('Evaluar con IA', { ic: 'ai', attrs: `data-eval="${s.id}"` })}</td></tr>`).join('')}</tbody></table></div>` : empty('Todas las entregas tienen evaluación.'))
      : evTable(tab === 'published' ? published : pending))}`;
  $$('[data-eval]').forEach((b) => b.addEventListener('click', () => runEvaluation(b.dataset.eval, b)));
}

async function viewEvaluationDetail(root) {
  const id = location.hash.split('?')[0].split('/')[2];
  const e = await api(`/api/evaluations/${id}`);
  const editable = isStaff() && !e.teacher_approved;
  const list = (title, items, color) => `<div><h4 class="text-sm font-bold mb-2 ${color}">${title}</h4><ul class="space-y-1.5 text-sm">${items.map((x) => `<li class="flex gap-2"><span class="${color}">•</span><span>${esc(x)}</span></li>`).join('') || '<li class="text-slate-400">—</li>'}</ul></div>`;

  root.innerHTML = `
    ${pageHeader(esc(e.laboratory_title), `${esc(e.student_name)} · ${esc(e.cohort_name)} · ${fdate(e.created_at)}`, `<a href="${isStaff() ? '#/evaluations' : '#/grades'}">${btn('← Volver', { kind: 'ghost' })}</a>`)}
    <div class="grid lg:grid-cols-3 gap-6">
      <div class="lg:col-span-2 space-y-6">
        ${card(`<div class="p-6"><div class="flex items-center gap-2 mb-3">${icon('ai', 'w-5 h-5 text-brand-600')}<h3 class="font-bold">Resumen de la IA</h3><span class="text-xs font-mono text-slate-400 ml-auto">${esc(e.ai_provider)}</span></div>
          <p class="text-slate-700">${esc(e.general_summary)}</p>
          <div class="grid md:grid-cols-3 gap-5 mt-6">${list('Fortalezas', e.strengths, 'text-emerald-600')}${list('Debilidades', e.weaknesses, 'text-rose-600')}${list('Recomendaciones', e.recommendations, 'text-brand-600')}</div></div>`)}
        ${card(`<div class="p-6"><h3 class="font-bold mb-4">Evaluación por criterio</h3><div class="space-y-4">${e.criteria_scores.map((c) => `
          <div class="rounded-xl ring-1 ring-slate-100 p-4" data-cid="${esc(c.criterion_id)}">
            <div class="flex flex-wrap items-start justify-between gap-3">
              <div class="min-w-0"><p class="font-semibold"><span class="font-mono text-xs text-slate-400 mr-1">${esc(c.criterion_id)}</span>${esc(c.name)}</p>
              <p class="text-xs text-slate-500">${esc(c.competency)} · ponderación <b>${c.weight}%</b> · aporte <b>${c.contribution.toFixed(4)}</b></p></div>
              <div class="flex items-center gap-2">
                ${c.adjusted ? `<span class="text-xs text-slate-400 line-through" title="Puntaje original IA">${fmt(c.ai_partial_score)}</span>` : ''}
                ${editable ? `<input type="text" inputmode="decimal" autocomplete="off" value="${fmt(c.partial_score)}" data-score class="${input} !w-20 !py-1.5 text-center font-bold" aria-label="Puntaje de 0 a 5"/>` : `<span class="text-2xl font-extrabold" style="color:${scoreColor(c.partial_score)}">${fmt(c.partial_score)}</span>`}
                <span class="text-slate-400 text-sm">/ 5</span></div></div>
            <blockquote class="mt-3 border-l-4 border-brand-200 bg-brand-50/40 rounded-r-lg px-3 py-2 text-sm italic text-slate-600">“${esc(c.evidence_quote)}”</blockquote>
            <p class="mt-2 text-sm text-slate-600">${esc(c.reasoning)}</p>
            ${c.adjusted ? `<p class="mt-2 text-xs text-amber-700">✎ Ajuste docente: ${esc(c.adjust_reason)}</p>` : ''}
            ${editable ? `<input data-reason placeholder="Justificación del ajuste (obligatoria si cambia el puntaje)" class="${input} mt-3 hidden"/>` : ''}
          </div>`).join('')}</div></div>`)}
      </div>
      <div class="space-y-6">
        ${card(`<div class="p-6 text-center"><p class="text-xs font-semibold uppercase tracking-wide text-slate-500">Nota final (backend)</p>
          <p class="text-6xl font-black mt-2" style="color:${scoreColor(e.calculated_score)}">${fmt(e.calculated_score)}</p><p class="text-slate-400">sobre 5,0</p>
          <div class="mt-3">${levelBadge(levelOf(e.calculated_score))}</div>
          <div class="mt-5 text-left rounded-xl bg-slate-950 text-slate-200 p-4 font-mono text-[11px] leading-relaxed break-words">${esc(e.formula)}</div>
          <p class="text-xs text-slate-500 mt-3 text-left">Cálculo determinista con aritmética decimal y redondeo ROUND_HALF_UP. El modelo de IA no interviene en esta cifra (RF-207).</p></div>`)}
        ${card(`<div class="p-6">${e.teacher_approved ? `<div class="flex items-center gap-2 text-emerald-700 font-semibold">${icon('check')} Publicada el ${fdate(e.approved_at)}</div>${e.teacher_comment ? `<p class="mt-3 text-sm text-slate-600">💬 ${esc(e.teacher_comment)}</p>` : ''}`
          : editable ? `<h3 class="font-bold mb-3">Supervisión docente</h3><div class="space-y-3">
            ${btn('Guardar ajustes y recalcular', { kind: 'ghost', attrs: 'id="btn-adjust" class="w-full"' })}
            <textarea id="t-comment" rows="3" class="${input}" placeholder="Comentario para el estudiante (opcional)"></textarea>
            ${btn('Aprobar y publicar nota', { kind: 'success', ic: 'check', attrs: 'id="btn-approve"' })}</div>`
          : '<p class="text-sm text-slate-500">Pendiente de aprobación docente.</p>'}</div>`)}
      </div>
    </div>`;

  if (!editable) return;
  // Acepta coma o punto decimal (configuración regional es-CO): "3,5" y "3.5" → 3.5
  const parseScore = (v) => { const t = String(v).trim().replace(',', '.'); return /^\d+(\.\d+)?$/.test(t) ? Number(t) : NaN; };
  const origScore = {};
  e.criteria_scores.forEach((c) => (origScore[c.criterion_id] = c.partial_score));
  $$('[data-cid]').forEach((box) => {
    const s = $('[data-score]', box), r = $('[data-reason]', box);
    s.addEventListener('input', () => {
      const v = parseScore(s.value);
      const bad = Number.isNaN(v) || v < 0 || v > 5;
      s.classList.toggle('!ring-rose-400', bad);
      r.classList.toggle('hidden', !bad && v === origScore[box.dataset.cid]);
    });
  });
  $('#btn-adjust').addEventListener('click', async () => {
    const all = $$('[data-cid]').map((box) => ({ criterion_id: box.dataset.cid, name: $('p.font-semibold', box).textContent.trim().replace(box.dataset.cid, '').trim(), partial_score: parseScore($('[data-score]', box).value), reason: $('[data-reason]', box).value.trim() }));
    const invalid = all.find((a) => Number.isNaN(a.partial_score) || a.partial_score < 0 || a.partial_score > 5);
    if (invalid) return toast(`Puntaje inválido en "${invalid.name}": use un número entre 0 y 5 (ej. 3,5).`, 'err');
    const adjustments = all.filter((a) => Math.round(a.partial_score * 10) !== Math.round(origScore[a.criterion_id] * 10))
      .map((a) => ({ criterion_id: a.criterion_id, partial_score: Math.round(a.partial_score * 10) / 10, reason: a.reason }));
    if (!adjustments.length) return toast('No hay cambios en los puntajes.', 'warn');
    if (adjustments.some((a) => a.reason.length < 3)) return toast('Escriba la justificación de cada criterio ajustado (mínimo 3 caracteres).', 'err');
    try { await api(`/api/evaluations/${e.id}/adjust`, { method: 'PATCH', body: { adjustments } }); toast('Ajustes guardados. Nota recalculada por el backend.', 'ok'); render(); }
    catch (err) { toast(err.message, 'err'); }
  });
  $('#btn-approve').addEventListener('click', async () => {
    if (!confirmInline('#btn-approve')) return;
    try { await api(`/api/evaluations/${e.id}/approve`, { method: 'POST', body: { teacher_comment: $('#t-comment').value } }); toast('Nota publicada para el estudiante.', 'ok'); render(); }
    catch (err) { toast(err.message, 'err'); }
  });
}
// Confirmación de doble clic (evita diálogos bloqueantes del navegador)
function confirmInline(sel) {
  const b = $(sel);
  if (b.dataset.armed) return true;
  b.dataset.armed = '1'; const old = b.innerHTML; b.innerHTML = '¿Confirmar publicación? Clic de nuevo';
  setTimeout(() => { if (b.isConnected) { delete b.dataset.armed; b.innerHTML = old; } }, 4000);
  return false;
}

// ---------------------------------------------------------------- Mis calificaciones
async function viewGrades(root) {
  const evs = await api('/api/evaluations');
  root.innerHTML = `${pageHeader('Mis calificaciones', 'Notas publicadas por el docente con retroalimentación detallada')}
    ${evs.length ? `<div class="grid md:grid-cols-2 xl:grid-cols-3 gap-5">${evs.map((e) => `<a href="#/evaluation/${e.id}" class="block">${card(`<div class="p-6 hover:bg-slate-50/60 rounded-2xl transition">
      <div class="flex justify-between items-start gap-3"><div><p class="text-xs font-semibold text-brand-600 uppercase">${esc(e.cohort_name)}</p><h3 class="font-bold">${esc(e.laboratory_title)}</h3></div>
      <span class="text-3xl font-black" style="color:${scoreColor(e.calculated_score)}">${fmt(e.calculated_score)}</span></div>
      <p class="text-sm text-slate-600 mt-3 line-clamp-3">${esc(e.general_summary)}</p>
      <div class="mt-4 flex justify-between items-center">${levelBadge(levelOf(e.calculated_score))}<span class="text-xs text-slate-400">${fdate(e.approved_at)}</span></div></div>`)}</a>`).join('')}</div>` : card(empty('Aún no tienes calificaciones publicadas.'))}`;
}

// ---------------------------------------------------------------- Informe integrado
async function viewReport(root) {
  const p = params();
  let students = [], sid = p.get('student'), pend = p.get('pending') === '1';
  if (isStaff()) {
    students = await api('/api/users?role=ESTUDIANTE');
    if (!sid && students[0]) sid = students[0].id;
    if (!sid) { root.innerHTML = pageHeader('Informe integrado') + card(empty('No hay estudiantes registrados.')); return; }
  }
  const q = isStaff() ? `?student_id=${sid}&include_pending=${pend}` : '';
  const r = await api(`/api/reports/student${q}`);
  const selector = isStaff() ? `<select id="sel-st" class="${input} !w-auto">${students.map((s) => `<option value="${s.id}" ${s.id === sid ? 'selected' : ''}>${esc(s.full_name)}</option>`).join('')}</select>
    <label class="flex items-center gap-2 text-sm bg-white ring-1 ring-slate-200 rounded-xl px-3"><input type="checkbox" id="chk-pend" ${pend ? 'checked' : ''}/> Incluir pendientes</label>` : '';

  root.innerHTML = `
    ${pageHeader('Informe Integrado del Aprendizaje', `${esc(r.student.full_name)} · ${esc(r.student.student_code || r.student.email)}`, selector + btn('Descargar PDF', { ic: 'download', attrs: 'id="btn-pdf"' }))}
    ${r.includes_pending ? `<div class="mb-4 rounded-xl bg-amber-50 ring-1 ring-amber-200 p-3 text-sm text-amber-800">Vista preliminar: incluye evaluaciones aún no aprobadas.</div>` : ''}
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      ${kpi('Promedio global', fmt(r.overall_average, 2), r.overall_level)}
      ${r.cohorts.map((c) => kpi(esc(c.name), fmt(c.average, 2), levelOf(c.average))).join('')}
      ${kpi('Tendencia C1→C2', r.trend_between_cohorts == null ? '—' : (r.trend_between_cohorts >= 0 ? '▲ +' : '▼ ') + fmt(r.trend_between_cohorts, 2), 'Evolución del aprendizaje', r.trend_between_cohorts >= 0 ? 'text-emerald-600' : 'text-rose-600')}
    </div>
    <div class="grid lg:grid-cols-2 gap-6 mb-6">
      ${card(`<div class="p-6"><h3 class="font-bold mb-4">Evolución por laboratorio</h3><div class="h-72"><canvas id="ch-evo"></canvas></div></div>`)}
      ${card(`<div class="p-6"><h3 class="font-bold mb-4">Perfil de competencias</h3><div class="h-72"><canvas id="ch-radar"></canvas></div></div>`)}
    </div>
    <div class="grid lg:grid-cols-3 gap-6">
      ${card(`<div class="p-6"><h3 class="font-bold mb-4">Rendimiento por cohorte</h3>${r.cohorts.map((c) => `<div class="mb-5"><p class="text-sm font-bold text-slate-700 mb-2">${esc(c.name)}</p>
        ${c.labs.map((l) => `<div class="flex items-center justify-between py-1.5 text-sm border-b border-slate-50"><span class="truncate pr-2">${esc(l.title)}</span><span class="font-bold shrink-0" style="color:${scoreColor(l.score)}">${fmt(l.score)}</span></div>`).join('')}</div>`).join('')}</div>`)}
      ${card(`<div class="p-6"><h3 class="font-bold mb-4">Brechas de conocimiento</h3>${r.gaps.length ? r.gaps.map((g) => `<div class="mb-3"><div class="flex justify-between text-sm mb-1"><span class="font-medium">${esc(g.name)}</span><span class="font-bold" style="color:${scoreColor(g.average)}">${fmt(g.average, 2)}</span></div>
        <div class="h-2 rounded-full bg-slate-100"><div class="h-2 rounded-full" style="width:${g.average * 20}%;background:${scoreColor(g.average)}"></div></div></div>`).join('') : '<p class="text-sm text-emerald-700">✓ Sin brechas por debajo de 3,5.</p>'}
        ${r.pending_labs.length ? `<h4 class="font-bold text-sm mt-6 mb-2">Laboratorios sin nota publicada</h4><ul class="text-sm text-slate-600 list-disc pl-5">${r.pending_labs.map((l) => `<li>${esc(l.title)}</li>`).join('')}</ul>` : ''}</div>`)}
      ${card(`<div class="p-6"><h3 class="font-bold mb-4">Plan personalizado de fortalecimiento</h3><ol class="space-y-4">${r.plan.map((pl) => `<li class="rounded-xl ring-1 ring-slate-100 p-4">
        <div class="flex justify-between items-start gap-2"><p class="font-semibold text-sm">${pl.order}. ${esc(pl.competency)}</p>${badge(`Prioridad ${pl.priority}`, pl.priority === 'Alta' ? 'bg-rose-100 text-rose-800 ring-rose-200' : pl.priority === 'Media' ? 'bg-amber-100 text-amber-800 ring-amber-200' : 'bg-emerald-100 text-emerald-800 ring-emerald-200')}</div>
        <p class="text-xs text-slate-500 mt-1">${esc(pl.current_level)} → ${esc(pl.target)}</p>
        <ul class="mt-2 space-y-1 text-sm text-slate-600 list-disc pl-5">${pl.actions.map((a) => `<li>${esc(a)}</li>`).join('')}</ul></li>`).join('') || empty('Sin datos suficientes.')}</ol></div>`)}
    </div>`;

  $('#sel-st')?.addEventListener('change', (e) => (location.hash = `#/report?student=${e.target.value}&pending=${pend ? 1 : 0}`));
  $('#chk-pend')?.addEventListener('change', (e) => (location.hash = `#/report?student=${sid}&pending=${e.target.checked ? 1 : 0}`));
  $('#btn-pdf').addEventListener('click', () => downloadFile(`/api/reports/student/pdf${q}`, `informe_integrado_${r.student.full_name.replace(/\s+/g, '_')}.pdf`));
  chart('ch-evo', { type: 'line', data: { labels: r.evolution.map((e) => e.label.replace(/ · .*/, '')), datasets: [{ data: r.evolution.map((e) => e.score), borderColor: '#4f46e5', backgroundColor: 'rgba(79,70,229,.12)', fill: true, tension: .35, pointRadius: 5, pointBackgroundColor: r.evolution.map((e) => scoreColor(e.score)) }] },
    options: { maintainAspectRatio: false, scales: { y: { min: 0, max: 5 } }, plugins: { legend: { display: false } } } });
  chart('ch-radar', { type: 'radar', data: { labels: r.competencies.map((c) => c.name), datasets: [{ data: r.competencies.map((c) => c.average), borderColor: '#10b981', backgroundColor: 'rgba(16,185,129,.18)', pointBackgroundColor: '#10b981' }] },
    options: { maintainAspectRatio: false, scales: { r: { min: 0, max: 5, ticks: { stepSize: 1 } } }, plugins: { legend: { display: false } } } });
}

// ---------------------------------------------------------------- Mapa mental (D3)
async function viewMindmap(root) {
  const p = params();
  let students = [], sid = p.get('student') || '';
  if (isStaff()) students = await api('/api/users?role=ESTUDIANTE');
  const data = await api(`/api/mindmap${isStaff() && sid ? `?student_id=${sid}` : ''}`);
  root.innerHTML = `
    ${pageHeader('Mapa mental de competencias en IA', 'Haga clic en un nodo para expandir/contraer y ver evidencias, dominio y áreas de profundización (RF-211 / RF-212)',
      isStaff() ? `<select id="sel-st" class="${input} !w-auto"><option value="">Vista global (todas las notas)</option>${students.map((s) => `<option value="${s.id}" ${s.id === sid ? 'selected' : ''}>${esc(s.full_name)}</option>`).join('')}</select>` : '')}
    <div class="flex flex-wrap gap-3 mb-4 text-xs">${Object.entries(LEVEL).map(([k, v]) => `<span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded-full" style="background:${v.hex}"></span>${k}</span>`).join('')}</div>
    <div class="grid xl:grid-cols-3 gap-6">
      ${card(`<div id="mm" class="overflow-auto scroll-thin" style="height:620px"></div>`, 'xl:col-span-2')}
      ${card(`<div id="mm-panel" class="p-6"></div>`)}
    </div>`;
  $('#sel-st')?.addEventListener('change', (e) => (location.hash = `#/mindmap?student=${e.target.value}`));
  drawMindmap(data);
}

function nodePanel(d) {
  const n = d.data;
  const typeLabel = { root: 'Raíz', cohort: 'Cohorte', competency: 'Competencia', laboratory: 'Laboratorio' }[n.type];
  $('#mm-panel').innerHTML = `
    <p class="text-xs font-semibold uppercase tracking-wide text-brand-600">${typeLabel}</p>
    <h3 class="text-xl font-bold mt-1">${esc(n.name)}</h3>
    <div class="flex items-center gap-3 mt-3"><span class="text-4xl font-black" style="color:${scoreColor(n.mastery)}">${fmt(n.mastery, 2)}</span>${levelBadge(n.level)}</div>
    <p class="text-xs text-slate-500 mt-1">Nivel de dominio alcanzado (0–5)</p>
    ${n.description || n.objectives ? `<p class="text-sm text-slate-600 mt-4">${esc(n.description || n.objectives)}</p>` : ''}
    ${n.score != null ? `<p class="text-sm mt-3">Nota del laboratorio: <b style="color:${scoreColor(n.score)}">${fmt(n.score)}</b></p>` : ''}
    ${n.children?.length || d._children?.length ? `<h4 class="font-bold text-sm mt-5 mb-2">${n.type === 'competency' ? 'Laboratorios asociados' : 'Contiene'}</h4><ul class="space-y-1 text-sm">${(n.children || []).map((c) => `<li class="flex justify-between gap-2"><span class="truncate">${esc(c.name)}</span><b style="color:${scoreColor(c.mastery)}">${fmt(c.mastery)}</b></li>`).join('')}</ul>` : ''}
    ${n.evidences?.length ? `<h4 class="font-bold text-sm mt-5 mb-2">Evidencias</h4><div class="space-y-2">${n.evidences.map((e) => `<blockquote class="border-l-4 border-brand-200 bg-brand-50/40 rounded-r-lg px-3 py-2 text-xs"><p class="font-semibold text-slate-700">${esc(e.lab || '')} ${esc(e.criterion)}</p><p class="italic text-slate-600 mt-0.5">“${esc(e.quote)}”</p></blockquote>`).join('')}</div>` : ''}
    ${n.deepening?.length ? `<h4 class="font-bold text-sm mt-5 mb-2">Áreas de profundización</h4><ul class="list-disc pl-5 text-sm text-slate-600 space-y-1">${n.deepening.map((x) => `<li>${esc(x)}</li>`).join('')}</ul>` : ''}`;
}

function drawMindmap(data) {
  const container = $('#mm');
  if (!window.d3) { container.innerHTML = empty('No se pudo cargar D3.js'); return; }
  const dx = 34, dy = 240, left = 210;
  const width = Math.max(container.clientWidth, left + 3 * dy + 300);
  const root = d3.hierarchy(data);
  root.x0 = 0; root.y0 = 0;
  root.descendants().forEach((d, i) => { d.id = i; d._children = d.children; if (d.depth >= 2) d.children = null; });
  const tree = d3.tree().nodeSize([dx, dy]);
  const svg = d3.select(container).append('svg').attr('width', width).style('font', '12px Inter');
  const g = svg.append('g').attr('transform', `translate(${left},0)`);
  const gLink = g.append('g'), gNode = g.append('g');

  function update(source) {
    tree(root);
    let x0 = Infinity, x1 = -Infinity;
    root.each((d) => { if (d.x > x1) x1 = d.x; if (d.x < x0) x0 = d.x; });
    const height = Math.max(600, x1 - x0 + dx * 2);
    svg.transition().duration(300).attr('height', height).attr('viewBox', [0, x0 - dx, width, height]);
    const nodes = root.descendants(), links = root.links();
    const node = gNode.selectAll('g').data(nodes, (d) => d.id);
    const enter = node.enter().append('g').attr('class', 'mm-node').attr('transform', () => `translate(${source.y0},${source.x0})`)
      .on('click', (_, d) => { d.children = d.children ? null : d._children; update(d); nodePanel(d); });
    enter.append('circle').attr('r', (d) => (d.depth === 0 ? 14 : d.depth === 1 ? 11 : 8))
      .attr('fill', (d) => scoreColor(d.data.mastery)).attr('stroke', '#fff').attr('stroke-width', 3);
    // Raíz y cohortes: etiqueta a la izquierda; competencias y labs: a la derecha (evita solapes con los enlaces)
    enter.append('text').attr('dy', '0.32em').attr('x', (d) => (d.depth < 2 ? -18 : 14)).attr('text-anchor', (d) => (d.depth < 2 ? 'end' : 'start'))
      .text((d) => `${d.data.name}${d.data.mastery != null ? ` · ${fmt(d.data.mastery)}` : ''}`).attr('fill', '#1e293b')
      .clone(true).lower().attr('stroke', 'white').attr('stroke-width', 4);
    node.merge(enter).transition().duration(300).attr('transform', (d) => `translate(${d.y},${d.x})`);
    node.exit().transition().duration(300).attr('transform', () => `translate(${source.y},${source.x})`).remove();
    const diag = d3.linkHorizontal().x((d) => d.y).y((d) => d.x);
    const link = gLink.selectAll('path').data(links, (d) => d.target.id);
    link.enter().append('path').attr('class', 'mm-link').attr('d', () => { const o = { x: source.x0, y: source.y0 }; return diag({ source: o, target: o }); })
      .merge(link).transition().duration(300).attr('d', diag);
    link.exit().transition().duration(300).attr('d', () => { const o = { x: source.x, y: source.y }; return diag({ source: o, target: o }); }).remove();
    root.eachBefore((d) => { d.x0 = d.x; d.y0 = d.y; });
  }
  update(root);
  nodePanel(root);
}

// ---------------------------------------------------------------- Estudiantes
async function viewStudents(root) {
  const users = await api(isAdmin() ? '/api/users' : '/api/users?role=ESTUDIANTE');
  root.innerHTML = `
    ${pageHeader(isAdmin() ? 'Usuarios' : 'Estudiantes', 'Registro y gestión de participantes de las cohortes', btn('Registrar', { ic: 'plus', attrs: 'id="btn-new"' }))}
    ${card(`<div class="overflow-x-auto"><table class="w-full text-sm"><thead class="text-left text-slate-500"><tr><th class="px-4 py-3">Nombre</th><th>Correo</th><th>Código</th><th>Rol</th><th>Alta</th><th></th></tr></thead><tbody class="divide-y divide-slate-100">
    ${users.map((u) => `<tr class="${u.is_active ? '' : 'opacity-50'}"><td class="px-4 py-3 font-medium"><div class="flex items-center gap-3"><div class="w-8 h-8 rounded-full bg-brand-100 text-brand-700 grid place-items-center text-xs font-bold">${esc(initials(u.full_name))}</div>${esc(u.full_name)}</div></td>
    <td class="text-slate-600">${esc(u.email)}</td><td class="font-mono text-xs">${esc(u.student_code || '—')}</td><td>${badge(u.role)}</td><td class="text-slate-500">${fdate(u.created_at)}</td>
    <td class="text-right pr-4 whitespace-nowrap">${u.role === 'ESTUDIANTE' ? `<a href="#/report?student=${u.id}" class="font-semibold text-brand-600 mr-3">Informe</a>` : ''}${isAdmin() && u.id !== S.user.id ? `<button data-toggle="${u.id}" data-active="${u.is_active}" class="text-xs font-semibold ${u.is_active ? 'text-rose-600' : 'text-emerald-600'}">${u.is_active ? 'Desactivar' : 'Activar'}</button>` : ''}</td></tr>`).join('')}
    </tbody></table></div>`)}`;
  $$('[data-toggle]').forEach((b) => b.addEventListener('click', async () => {
    try { await api(`/api/users/${b.dataset.toggle}/active?active=${b.dataset.active !== 'true'}`, { method: 'PATCH' }); render(); } catch (e) { toast(e.message, 'err'); }
  }));
  $('#btn-new').addEventListener('click', () => {
    const m = modal('Registrar usuario', `<form id="f-user" class="space-y-4">
      <div>${label('Nombre completo')}<input name="full_name" required minlength="3" class="${input}"/></div>
      <div class="grid grid-cols-2 gap-3"><div>${label('Correo')}<input name="email" type="email" required class="${input}"/></div><div>${label('Código')}<input name="student_code" class="${input}"/></div></div>
      <div>${label('Contraseña inicial (mín. 8)')}<input name="password" type="password" minlength="8" required class="${input}"/></div>
      ${isAdmin() ? `<div>${label('Rol')}<select name="role" class="${input}"><option>ESTUDIANTE</option><option>DOCENTE</option><option>ADMINISTRADOR</option></select></div>` : ''}
      <div class="flex justify-end">${btn('Registrar', { attrs: 'type="submit"' })}</div></form>`);
    $('#f-user', m).addEventListener('submit', async (e) => {
      e.preventDefault(); const body = Object.fromEntries(new FormData(e.target)); if (!body.student_code) delete body.student_code;
      try { await api('/api/users', { method: 'POST', body }); toast('Usuario registrado.', 'ok'); render(); } catch (err) { toast(err.message, 'err'); }
    });
  });
}

// ---------------------------------------------------------------- Auditoría
async function viewAudit(root) {
  const rows = await api('/api/audit?limit=200');
  root.innerHTML = `${pageHeader('Trazabilidad y auditoría', 'Bitácora inmutable de acciones relevantes (SRS §8.3)')}
    ${card(rows.length ? `<div class="overflow-x-auto"><table class="w-full text-sm"><thead class="text-left text-slate-500"><tr><th class="px-4 py-3">Fecha</th><th>Acción</th><th>Entidad</th><th>Detalle</th></tr></thead><tbody class="divide-y divide-slate-100">
    ${rows.map((r) => `<tr><td class="px-4 py-2.5 whitespace-nowrap text-slate-500">${new Date(r.created_at).toLocaleString('es-CO')}</td><td>${badge(r.action, 'bg-brand-50 text-brand-700 ring-brand-100')}</td><td class="font-mono text-xs">${esc(r.entity)}#${esc(r.entity_id)}</td>
    <td class="font-mono text-[11px] text-slate-500 max-w-md truncate" title="${esc(JSON.stringify(r.detail))}">${esc(JSON.stringify(r.detail))}</td></tr>`).join('')}</tbody></table></div>` : empty('Sin registros aún. Las acciones del sistema aparecerán aquí.'))}`;
}

// ---------------------------------------------------------------- Proyecto y equipo
async function viewProject(root) {
  const p = await api('/api/project');
  const html = `
    <section class="relative overflow-hidden rounded-3xl bg-slate-950 text-white p-8 sm:p-12 mb-8">
      <div class="absolute -top-24 -right-24 w-80 h-80 rounded-full bg-brand-600/40 blur-3xl"></div>
      <div class="absolute -bottom-24 left-10 w-72 h-72 rounded-full bg-emerald-500/20 blur-3xl"></div>
      <div class="relative">
        <p class="text-brand-300 font-semibold">${esc(p.institution)} · ${esc(p.faculty)}</p>
        <h1 class="text-4xl sm:text-5xl font-extrabold mt-2">${esc(p.title)}</h1>
        <p class="text-lg text-slate-300 mt-3 max-w-3xl">${esc(p.subtitle)}</p>
        <div class="flex flex-wrap gap-2 mt-6 text-xs">${[p.program, p.course, p.year].map((x) => `<span class="rounded-full bg-white/10 px-3 py-1">${esc(x)}</span>`).join('')}</div>
      </div>
    </section>
    <div class="grid lg:grid-cols-3 gap-6 mb-8">
      ${card(`<div class="p-7"><h2 class="text-xl font-bold mb-3">Abstract</h2><p class="text-slate-700 leading-relaxed">${esc(p.abstract)}</p></div>`, 'lg:col-span-2')}
      ${card(`<div class="p-7"><h2 class="text-xl font-bold mb-3">Objetivos</h2><ol class="space-y-3">${p.objectives.map((o, i) => `<li class="flex gap-3"><span class="shrink-0 w-7 h-7 rounded-full bg-brand-600 text-white grid place-items-center text-xs font-bold">${i + 1}</span><span class="text-sm text-slate-700">${esc(o)}</span></li>`).join('')}</ol></div>`)}
    </div>
    <h2 class="text-xl font-bold mb-4">Arquitectura tecnológica</h2>
    <div class="grid sm:grid-cols-2 lg:grid-cols-5 gap-4 mb-8">${p.architecture.map((a, i) => card(`<div class="p-5 h-full"><p class="text-xs font-bold text-brand-600">CAPA ${i + 1}</p><p class="font-bold mt-1">${esc(a.layer)}</p><p class="text-xs font-mono text-slate-500 mt-2">${esc(a.tech)}</p><p class="text-sm text-slate-600 mt-2">${esc(a.detail)}</p></div>`)).join('')}</div>
    ${card(`<div class="p-7"><h2 class="text-xl font-bold mb-4">Aportes de ingeniería</h2><div class="grid sm:grid-cols-2 gap-3">${p.contributions.map((c) => `<div class="flex gap-3 rounded-xl bg-slate-50 p-4">${icon('check', 'w-5 h-5 text-emerald-600 shrink-0')}<span class="text-sm">${esc(c)}</span></div>`).join('')}</div></div>`, 'mb-8')}
    <h2 class="text-xl font-bold mb-4">Equipo desarrollador</h2>
    <div class="grid md:grid-cols-2 xl:grid-cols-3 gap-6">${p.team.map((m) => `
      <div class="${m.highlight ? 'md:col-span-2 xl:col-span-3' : ''}">${card(`<div class="p-7 flex flex-col ${m.highlight ? 'sm:flex-row' : ''} gap-6 items-center ${m.highlight ? 'bg-gradient-to-br from-brand-50 to-emerald-50 rounded-2xl' : ''}">
        <div class="relative shrink-0"><img src="${esc(m.photo)}" alt="${esc(m.name)}" class="w-40 h-40 rounded-2xl object-cover ring-4 ring-white shadow-lg" onerror="this.replaceWith(Object.assign(document.createElement('div'),{className:'w-40 h-40 rounded-2xl bg-gradient-to-br from-brand-600 to-emerald-500 grid place-items-center text-5xl font-black text-white ring-4 ring-white shadow-lg',textContent:'${esc(initials(m.name))}'}))"/>
        ${m.highlight ? '<span class="absolute -bottom-3 left-1/2 -translate-x-1/2 whitespace-nowrap rounded-full bg-slate-900 text-white text-xs font-bold px-3 py-1 shadow">★ Autor principal</span>' : ''}</div>
        <div class="${m.highlight ? 'text-center sm:text-left' : 'text-center'}"><h3 class="text-2xl font-extrabold">${esc(m.name)}</h3><p class="text-brand-700 font-semibold mt-1">${esc(m.role)}</p><p class="text-slate-600 mt-3 text-sm leading-relaxed max-w-2xl">${esc(m.bio)}</p></div></div>`)}</div>`).join('')}</div>
    ${!S.token ? `<div class="text-center mt-10"><a href="#/login">${btn('Ingresar a la plataforma')}</a></div>` : ''}`;
  if (!S.token) root.innerHTML = `<div class="max-w-7xl mx-auto px-4 sm:px-6 py-8 fade-in">${html}</div>`;
  else root.innerHTML = html;
}

// ------------------------------------------------------------------ Boot
function boot() {
  render().catch((e) => {
    console.error(e);
    $('#app').innerHTML = `<div class="p-10 text-center text-rose-600">No se pudo cargar la aplicación: ${esc(e.message)}. Recargue la página.</div>`;
  });
}
if (document.readyState === 'loading') window.addEventListener('DOMContentLoaded', boot);
else boot();
