// Chart factory — created once, updated in place. Color normalized.
const charts={};
const PALETTE=['#06b6d4','#10b981','#a855f7','#f97316','#3b82f6','#ea4335','#6366f1'];
const PILLAR_COLOR={build:'#4285f4',scale:'#f97316',govern:'#ea4335',optimize:'#34a853',evaluate:'#6366f1'};
function themeColors(){ const l=document.body.classList.contains('light-theme');
  return { grid:l?'rgba(0,0,0,0.06)':'rgba(255,255,255,0.05)', tick:l?'#4b5563':'#9ca3af', border:l?'#fff':'rgba(255,255,255,0.05)' }; }
function baseOptions(){ const c=themeColors();
  return { responsive:true, maintainAspectRatio:false, animation:{duration:300}, plugins:{legend:{display:false}},
    scales:{ y:{grid:{color:c.grid},ticks:{color:c.tick}}, x:{grid:{display:false},ticks:{color:c.tick}} } }; }
export function pillarColor(p){ return PILLAR_COLOR[p]||'#4285f4'; }
export function chartType(kind,domain){
  if((domain==='System'||domain==='Cost')&&kind==='histogram'&&(domain==='System')) return 'doughnut';
  if(kind==='histogram') return 'line';
  return 'bar';
}
function firstColor(c){ return Array.isArray(c)?(c[0]||'#4285f4'):c; }
export function renderChart(id,type,labels,data,color){
  const canvas=document.getElementById(id); if(!canvas) return; const c=themeColors();
  if(charts[id]){ const ch=charts[id]; ch.data.labels=labels; ch.data.datasets[0].data=data; ch.update('none'); return; }
  const ctx=canvas.getContext('2d'); let dataset, options=baseOptions();
  if(type==='doughnut'){ const s=firstColor(color);
    dataset={data,backgroundColor:[s,'rgba(255,255,255,0.05)'],borderColor:c.border,borderWidth:1};
    options={responsive:true,maintainAspectRatio:false,cutout:'70%',plugins:{legend:{position:'right',labels:{color:c.tick,boxWidth:10,font:{size:9}}}}};
  } else if(type==='line'){ const s=firstColor(color);
    const g=ctx.createLinearGradient(0,0,0,170); g.addColorStop(0,s+'4d'); g.addColorStop(1,s+'00');
    dataset={data,borderColor:s,backgroundColor:g,borderWidth:2,fill:true,tension:0.35,pointRadius:3,pointBackgroundColor:s};
  } else { dataset={data,backgroundColor:color,borderRadius:6,borderWidth:1,borderColor:c.border}; }
  charts[id]=new Chart(ctx,{type,data:{labels,datasets:[dataset]},options});
}
export function destroyAll(){ Object.values(charts).forEach(c=>c.destroy()); Object.keys(charts).forEach(k=>delete charts[k]); }
export { PALETTE };
