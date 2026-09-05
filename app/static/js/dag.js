const nodes={}, links={};
export function initDag(){
  ['user','triage_agent','identity_agent','software_agent','incident_agent','access_agent'].forEach(id=>nodes[id]=document.getElementById(`node-${id}`));
  links.userTriage=document.getElementById('link-user-triage');
  links.identity=document.getElementById('link-triage-identity');
  links.software=document.getElementById('link-triage-software');
  links.incident=document.getElementById('link-triage-incident');
  links.access=document.getElementById('link-triage-access');
}
function setStatus(n,t){ const el=n&&n.querySelector('.node-status'); if(el) el.textContent=t; }
export function reset(){
  Object.values(nodes).forEach(n=>{ if(!n)return; n.classList.remove('active-node');
    n.querySelectorAll('.tool-anchor').forEach(t=>t.classList.remove('active-tool')); setStatus(n,'Idle'); });
  Object.values(links).forEach(l=>l&&l.classList.remove('active-trail'));
}
export function onEvent(evt){
  if(evt.type==='start'){ reset(); nodes.user&&nodes.user.classList.add('active-node'); links.userTriage&&links.userTriage.classList.add('active-trail'); return; }
  if(evt.type==='complete'){ setTimeout(reset,800); return; }
  const a=evt.author; if(!a) return;
  Object.values(nodes).forEach(n=>n&&n.classList.remove('active-node'));
  const node=nodes[a]; if(node){ node.classList.add('active-node'); setStatus(node, evt.type==='tool_call'?'Tool':'Running'); }
  if(a==='triage_agent'&&links.userTriage) links.userTriage.classList.add('active-trail');
  if(a==='identity_agent'&&links.identity) links.identity.classList.add('active-trail');
  if(a==='software_agent'&&links.software) links.software.classList.add('active-trail');
  if(a==='incident_agent'&&links.incident) links.incident.classList.add('active-trail');
  if(a==='access_agent'&&links.access) links.access.classList.add('active-trail');
  if(evt.type==='tool_call'){ const n=evt.data&&evt.data.tool_call&&evt.data.tool_call.name; const an=document.getElementById(`tool-${n}`); if(an) an.classList.add('active-tool'); }
  if(evt.type==='tool_response'){ const n=evt.data&&evt.data.tool_response&&evt.data.tool_response.name; const an=document.getElementById(`tool-${n}`); if(an) setTimeout(()=>an.classList.remove('active-tool'),500); }
}
