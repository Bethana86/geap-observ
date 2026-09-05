const sessionBadge=()=>document.getElementById('session-badge');
export function clear(){}
export function onEvent(evt){
  if(evt.type==='start'){ const b=sessionBadge(); if(b) b.textContent=`SESSION: ${evt.session_id}`; }
}
