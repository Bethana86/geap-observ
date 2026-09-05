export class RealtimeClient {
  constructor(onEvent, onStatus){ this.onEvent=onEvent; this.onStatus=onStatus; this.ws=null; this.retry=0; }
  connect(){
    const proto = location.protocol==='https:'?'wss':'ws';
    try { this.ws = new WebSocket(`${proto}://${location.host}/api/ws`); }
    catch(e){ return this._fallback(); }
    this.ws.onopen=()=>{ this.retry=0; this.onStatus('connected'); };
    this.ws.onmessage=(ev)=>{ try{ this.onEvent(JSON.parse(ev.data)); }catch(_){} };
    this.ws.onclose=()=>{ this.onStatus('disconnected'); this._reconnect(); };
    this.ws.onerror=()=>{ this.ws&&this.ws.close(); };
  }
  _reconnect(){ this.retry=Math.min(this.retry+1,6); setTimeout(()=>this.connect(),1000*this.retry); }
  _fallback(){ const es=new EventSource('/api/stream');
    es.onmessage=(ev)=>{ try{ this.onEvent(JSON.parse(ev.data)); }catch(_){} };
    es.onopen=()=>this.onStatus('connected'); es.onerror=()=>this.onStatus('disconnected'); }
}
