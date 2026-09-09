// Builds the pillar-organized metrics section from /api/catalog and updates
// charts, signals, pillar strip, alerts and executive KPIs.
import { renderChart, chartType, pillarColor, PALETTE } from './charts.js';

let catalog = null;

const AGENTS = ['triage_agent', 'identity_agent', 'software_agent', 'incident_agent', 'access_agent'];
const AGENT_LABELS = ['Triage', 'Identity', 'Software', 'Incident', 'Access'];
const TOOLS = ['reset_ad_password', 'send_mfa_token', 'deploy_software', 'check_license_pool', 'create_pagerduty_incident', 'query_datadog_metrics', 'restart_service_ansible', 'create_servicenow_approval', 'assign_iam_role'];
const TOOL_LABELS = ['AD Reset', 'MFA', 'SCCM', 'License', 'PagerDuty', 'Datadog', 'Ansible', 'ServiceNow', 'IAM'];

const cid = (n) => 'chart-' + n.replace(/[._]/g, '-');
const sid = (n) => 'sig-' + n.replace(/[._]/g, '-');

// ---------------- build tabs (one per pillar) ---------------- //
export function buildDashboard(cat) {
  catalog = cat;
  const tabs = document.getElementById('metrics-tabs');
  const contents = document.getElementById('metrics-tab-contents');
  tabs.innerHTML = ''; contents.innerHTML = '';

  Object.entries(cat.pillars).forEach(([pillar, label], idx) => {
    const metrics = cat.metrics_by_pillar[pillar] || [];
    const icon = (cat.pillar_icons && cat.pillar_icons[pillar]) || 'fa-chart-line';

    const btn = document.createElement('button');
    btn.className = 'tab-btn' + (idx === 0 ? ' active' : '');
    btn.dataset.tab = `tab-${pillar}`;
    btn.dataset.pillar = pillar;
    btn.innerHTML = `<i class="fa-solid ${icon}"></i> ${label}<span class="count">${metrics.length}</span>`;
    tabs.appendChild(btn);

    const pane = document.createElement('div');
    pane.className = 'tab-content' + (idx === 0 ? ' active' : '');
    pane.id = `tab-${pillar}`;

    // group metrics by domain within the pillar
    const byDomain = {};
    metrics.forEach((m) => { (byDomain[m.domain] = byDomain[m.domain] || []).push(m); });
    Object.entries(byDomain).forEach(([domain, list]) => {
      const group = document.createElement('div');
      group.className = 'domain-group';
      group.innerHTML = `<h4>${domain}</h4>`;
      const grid = document.createElement('div');
      grid.className = 'metrics-grid';
      list.forEach((m) => grid.appendChild(metricCard(m)));
      group.appendChild(grid);
      pane.appendChild(group);
    });
    contents.appendChild(pane);
  });

  tabs.querySelectorAll('.tab-btn').forEach((b) => {
    b.addEventListener('click', () => {
      tabs.querySelectorAll('.tab-btn').forEach((x) => x.classList.remove('active'));
      contents.querySelectorAll('.tab-content').forEach((x) => x.classList.remove('active'));
      b.classList.add('active');
      document.getElementById(b.dataset.tab).classList.add('active');
    });
  });

  buildPillarStrip(cat);
}

function metricCard(m) {
  const card = document.createElement('div');
  card.className = 'card metric-card';
  card.innerHTML = `
    <div class="card-header">
      <div><h3>${m.title}</h3><span class="metric-desc">${m.name} · ${m.unit}</span></div>
      <span class="status-signal-dot grey" id="${sid(m.name)}"></span>
    </div>
    <div class="card-body chart-container">
      <canvas id="${cid(m.name)}"></canvas>
      <div class="chart-no-data" id="nodata-${cid(m.name)}">Execute a scenario to populate OTel metrics</div>
    </div>`;
  return card;
}

function buildPillarStrip(cat) {
  const strip = document.getElementById('pillar-strip');
  if (!strip) return;
  strip.innerHTML = '';
  Object.entries(cat.pillars).forEach(([pillar, label]) => {
    const icon = (cat.pillar_icons && cat.pillar_icons[pillar]) || 'fa-chart-line';
    const sub = (cat.pillar_subtitles && cat.pillar_subtitles[pillar]) || '';
    const card = document.createElement('div');
    card.className = 'pillar-card';
    card.style.setProperty('--pc', pillarColor(pillar));
    card.innerHTML = `
      <div class="pc-icon"><i class="fa-solid ${icon}"></i></div>
      <div class="pc-body">
        <div class="pc-name">${label} <span class="pc-dot grey" id="pc-dot-${pillar}"></span></div>
        <div class="pc-sub">${sub}</div>
        <div class="pc-count" id="pc-count-${pillar}">—</div>
      </div>`;
    strip.appendChild(card);
  });
}

// ---------------- extract data per metric ---------------- //
function aggPoint(p, kind) {
  if ('value' in p) return p.value;
  if (kind === 'histogram' && p.count) return p.sum / p.count;
  return p.sum || 0;
}
function extract(metric, points) {
  const { domain, kind, pillar } = metric;
  // Filter to only attributed points for agent/tool breakdowns
  if (pillar === 'optimize' || pillar === 'build' || pillar === 'evaluate') {
    const agentPoints = points.filter((p) => p.attributes && p.attributes['gen_ai.agent.name']);
    if (agentPoints.length > 0) {
      const data = AGENTS.map((a) => {
        const pt = agentPoints.find((p) => p.attributes['gen_ai.agent.name'] === a);
        return pt ? aggPoint(pt, kind) : 0;
      });
      return { labels: AGENT_LABELS, data };
    }
    const toolPoints = points.filter((p) => p.attributes && p.attributes['gen_ai.tool.name']);
    if (toolPoints.length > 0) {
      const data = TOOLS.map((t) => {
        const pt = toolPoints.find((p) => p.attributes['gen_ai.tool.name'] === t);
        return pt ? aggPoint(pt, kind) : 0;
      });
      return { labels: TOOL_LABELS, data };
    }
  }
  if (domain === 'System' && kind === 'histogram') {
    const last = points.length ? aggPoint(points[points.length - 1], kind) : 0;
    return { labels: ['Used', 'Free'], data: [last, Math.max(0, 100 - last)] };
  }
  // Generic: only use non-attributed points for time-series
  const plain = points.filter((p) => !p.attributes);
  const pts = plain.length > 0 ? plain : points;
  const labels = pts.map((_, i) => `#${i + 1}`);
  const data = pts.map((p) => aggPoint(p, kind));
  return { labels, data };
}

// ---------------- update everything ---------------- //
export function updateDashboard(payload) {
  if (!catalog) return;
  const { metrics, signals, alerts, slo, pillars } = payload;

  Object.values(catalog.metrics_by_pillar).flat().forEach((m) => {
    try {
    const points = metrics[m.name] || [];
    const { labels, data } = extract(m, points);
    const id = cid(m.name);
    const hasData = data.some((v) => v && v !== 0);
    const overlay = document.getElementById(`nodata-${id}`);
    if (overlay) overlay.style.display = hasData ? 'none' : 'flex';
    if (hasData) {
      const type = chartType(m.kind, m.domain);
      const color = (m.pillar === 'optimize' || m.pillar === 'build')
        && points.some((p) => p.attributes && (p.attributes['gen_ai.agent.name'] || p.attributes['gen_ai.tool.name']))
        ? PALETTE : pillarColor(m.pillar);
      renderChart(id, type, labels, data, color);
    }
    const dot = document.getElementById(sid(m.name));
    if (dot) dot.className = `status-signal-dot ${signals[m.name] || 'grey'}`;
    } catch(e) { console.warn('metric render error', m.name, e); }
  });

  updatePillars(pillars);
  updateExec(slo);
  updateAlerts(alerts);
}

function updatePillars(pillars) {
  if (!pillars) return;
  Object.entries(pillars).forEach(([p, v]) => {
    const dot = document.getElementById(`pc-dot-${p}`);
    if (dot) dot.className = `pc-dot ${v.status}`;
    const cnt = document.getElementById(`pc-count-${p}`);
    if (cnt) cnt.textContent = v.breaches ? `${v.breaches} breach${v.breaches > 1 ? 'es' : ''}` : `${v.active} active · healthy`;
  });
}

function updateExec(slo) {
  if (!slo) return;
  set('kpi-success', `${slo.success_rate.toFixed(1)}%`);
  set('kpi-ttlt', `${slo.ttlt_ms} ms`);
  set('kpi-cost', `$${slo.cost_per_task.toFixed(4)}`);
  set('kpi-cache', `${slo.cache_hit_ratio.toFixed(0)}%`);
  set('kpi-quality', `${slo.autorater_quality.toFixed(1)}`);
  const risk = slo.risk_score || { score: 0, band: 'LOW' };
  const el = document.getElementById('kpi-risk');
  if (el) el.innerHTML = `${risk.score} <small id="kpi-risk-band">${risk.band}</small>`;
}

function updateAlerts(alerts) {
  const feed = document.getElementById('alerts-feed');
  const badge = document.getElementById('alert-status');
  if (!feed || !badge) return;
  if (!alerts || alerts.length === 0) {
    badge.textContent = 'All SLOs Compliant';
    badge.className = 'alert-status-badge green';
    feed.innerHTML = `<div class="alert-item empty-state"><i class="fa-solid fa-shield-halved"></i>
      <p>No active incidents. All thresholds within SLA limits.</p></div>`;
    return;
  }
  badge.textContent = `${alerts.length} Active Alert${alerts.length > 1 ? 's' : ''}`;
  badge.className = 'alert-status-badge red';
  feed.innerHTML = alerts.map((a) => `
    <div class="alert-record">
      <div class="alert-header"><span>&#128680; ${a.severity.toUpperCase()} — ${a.pillar.toUpperCase()} SLA BREACH</span><span class="alert-time">${a.time}</span></div>
      <div><strong>${a.title}</strong> (${a.domain})</div>
      <div>Value ${a.actual} · expected ${a.op} ${a.threshold} ${a.unit}</div>
    </div>`).join('');
}

function set(id, val) { const el = document.getElementById(id); if (el) el.textContent = val; }
