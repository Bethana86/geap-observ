import { api } from './api.js';
import { RealtimeClient } from './realtime.js';
import * as dag from './dag.js';
import * as terminal from './terminal.js';
import { buildDashboard, updateDashboard } from './dashboard.js';
import { destroyAll } from './charts.js';

let currentScenario='password_reset', running=false;

async function init(){
  dag.initDag(); initTheme(); wireControls();
  const [config, catalog] = await Promise.all([api.config(), api.catalog()]);
  applyConfig(config); buildDashboard(catalog);
  new RealtimeClient(handleEvent, setWsStatus).connect();
  await refresh();
}
function applyConfig(cfg){
  const et=document.getElementById('engine-text'), ed=document.getElementById('engine-dot');
  if(cfg.is_live_gemini){ et.textContent='Engine: LIVE GEMINI'; ed.className='pulse-dot'; }
  else { et.textContent='Engine: SIMULATION'; ed.className='pulse-dot blue'; }
}
function handleEvent(evt){
  dag.onEvent(evt); terminal.onEvent(evt);
  if(evt.type==='complete'||evt.type==='metrics'||evt.type==='alert'){ setTimeout(refresh,300); setRunning(false); }
  if(evt.type==='error') setRunning(false);
}
async function refresh(){
  try{
    const [obs, tk, ev] = await Promise.all([
      api.observability(),
      api.tokenomics().catch(()=>null),
      api.evaluation().catch(()=>null)
    ]);
    updateDashboard(obs);
    if(tk) updateTokenomics(tk);
    if(ev) updateEvaluation(ev);
  }catch(e){ console.error('refresh',e); }
}

function updateTokenomics(t){
  const set=(id,v)=>{ const el=document.getElementById(id); if(el) el.textContent=v; };
  set('tk-input', (t.total_input_tokens || 0).toLocaleString());
  set('tk-cached', (t.total_cached_tokens || 0).toLocaleString());
  set('tk-output', (t.total_output_tokens || 0).toLocaleString());
  set('tk-cost', `$${(t.total_cost || 0).toFixed(4)}`);
  set('tk-budget', `${t.budget_utilization_pct || 0}% used`);
  set('tk-savings', `${t.cache_savings_pct || 0}% ratio`);
  const fill = document.getElementById('tk-budget-fill');
  if(fill) fill.style.width = `${Math.min(100, t.budget_utilization_pct || 0)}%`;
}

function updateEvaluation(e){
  const set=(id,v)=>{ const el=document.getElementById(id); if(el) el.textContent=v; };
  if(e.total_evaluations > 0){
    set('eval-task-acc', `${e.avg_task_accuracy}%`);
    set('eval-routing-acc', `${e.avg_routing_accuracy}%`);
    set('eval-tool-acc', `${e.avg_tool_selection_accuracy}%`);
    set('eval-relevance', `${e.avg_relevance} / 5`);
    set('eval-hallucination', `${e.avg_hallucination_rate}%`);
    set('eval-csat', `${e.avg_user_satisfaction} / 5`);
    const status = document.getElementById('eval-status');
    if(status) status.textContent = `${e.total_evaluations} Evaluated · ${e.regressions_detected} Regressions`;
  }
}

function wireControls(){
  document.querySelectorAll('.scenario-option').forEach(opt=>opt.addEventListener('click',()=>{
    document.querySelectorAll('.scenario-option').forEach(o=>o.classList.remove('active'));
    opt.classList.add('active'); currentScenario=opt.dataset.scenario; }));
  document.getElementById('btn-run').addEventListener('click',()=>run());
  document.getElementById('btn-run-query').addEventListener('click',runQuery);
  document.getElementById('custom-query').addEventListener('keyup',e=>{ if(e.key==='Enter') runQuery(); });
  document.querySelectorAll('.chip[data-threat]').forEach(chip=>chip.addEventListener('click',async()=>{
    await api.injectThreat(chip.dataset.threat); setTimeout(refresh,300); }));
  
  const bmkBtn = document.getElementById('btn-benchmark');
  if(bmkBtn){
    bmkBtn.addEventListener('click', async()=>{
      bmkBtn.disabled = true;
      bmkBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Running Benchmark…';
      try {
        const res = await api.benchmark();
        alert(`Benchmark Complete!\n\nRouting Accuracy: ${res.overall.routing_pass_rate}%\nPassed: ${res.overall.passed}/${res.overall.total_tests}`);
        await refresh();
      } catch(err) {
        alert('Benchmark failed: ' + err.message);
      } finally {
        bmkBtn.disabled = false;
        bmkBtn.innerHTML = '<i class="fa-solid fa-flask"></i> Run Golden Benchmark (12 Tests)';
      }
    });
  }

  document.getElementById('btn-reset-all').addEventListener('click',async()=>{
    if(!confirm('Reset all OpenTelemetry metric accumulators?')) return;
    await api.reset(); destroyAll(); dag.reset(); refresh(); });
}
async function run(){ if(running) return; setRunning(true); dag.reset(); await api.simulate(currentScenario); }
async function runQuery(){ const i=document.getElementById('custom-query'); const q=i.value.trim();
  if(!q||running) return; setRunning(true); dag.reset(); await api.chat(q); }
function setRunning(s){ running=s;
  const b=document.getElementById('btn-run'), qb=document.getElementById('btn-run-query');
  if(s){ b.disabled=true; qb.disabled=true; b.innerHTML='<i class="fa-solid fa-spinner fa-spin"></i> Executing…'; }
  else { b.disabled=false; qb.disabled=false; b.innerHTML='<i class="fa-solid fa-bolt"></i> Execute Selected Flow'; qb.innerHTML='<i class="fa-solid fa-paper-plane"></i> Run'; } }
function setWsStatus(s){ const d=document.getElementById('ws-dot'), t=document.getElementById('ws-text');
  if(s==='connected'){ d.className='pulse-dot'; t.textContent='Live: WebSocket'; } else { d.className='pulse-dot red'; t.textContent='Reconnecting…'; } }
function initTheme(){ const icon=document.getElementById('theme-icon'), label=document.getElementById('theme-text');
  if(localStorage.getItem('theme')==='light'){ document.body.classList.add('light-theme'); icon.className='fa-solid fa-moon'; label.textContent='Dark'; }
  document.getElementById('btn-theme-toggle').addEventListener('click',()=>{
    const l=document.body.classList.toggle('light-theme'); localStorage.setItem('theme',l?'light':'dark');
    icon.className=l?'fa-solid fa-moon':'fa-solid fa-sun'; label.textContent=l?'Dark':'Light'; refresh(); }); }
document.addEventListener('DOMContentLoaded', init);
