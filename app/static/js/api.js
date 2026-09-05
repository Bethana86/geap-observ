const json = (r) => r.json();
export const api = {
  config: () => fetch('/api/config').then(json),
  catalog: () => fetch('/api/catalog').then(json),
  observability: () => fetch('/api/observability').then(json),
  simulate: (s) => fetch(`/api/simulate?scenario=${encodeURIComponent(s)}`, { method:'POST' }).then(json),
  chat: (q) => fetch(`/api/chat?query=${encodeURIComponent(q)}`, { method:'POST' }).then(json),
  injectThreat: (k) => fetch(`/api/inject-threat?kind=${encodeURIComponent(k)}`, { method:'POST' }).then(json),
  reset: () => fetch('/api/reset', { method:'POST' }).then(json),
};
