import asyncio
import json
import time
import uuid
import random
from typing import Dict, List, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.agents import AgentEngine, AGENTS, SCENARIOS, ROUTE_MAP
from app.tools import TOOL_REGISTRY
from app.telemetry import MetricInstruments
from app.security import screen_input

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="GEAP Enterprise IT Helpdesk", version="4.0.0")

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

# ─── WebSocket Connection Manager ───
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        data = json.dumps(message)
        for connection in list(self.active_connections):
            try:
                await connection.send_text(data)
            except Exception:
                self.disconnect(connection)

manager = ConnectionManager()

# ─── Metric Catalog (57 metrics across 4 pillars) ───
CATALOG = {
    "pillars": {"build": "Build", "scale": "Scale", "govern": "Govern", "optimize": "Optimize"},
    "pillar_icons": {"build": "fa-cubes-stacked", "scale": "fa-arrows-up-down-left-right", "govern": "fa-shield-halved", "optimize": "fa-gauge-high"},
    "pillar_subtitles": {"build": "Compose agents, tools, A2A & MCP", "scale": "Run & survive in production under load", "govern": "Secure, control & attribute the fleet", "optimize": "Continuously improve quality & cost"},
    "metrics_by_pillar": {
        "build": [
            {"name": "gen_ai.agent.calls.count", "kind": "counter", "pillar": "build", "domain": "Agents", "unit": "count", "title": "Agent Invocations", "description": "Total agent invocations", "slo": {"op": "lte", "value": 30, "scope": "sum"}},
            {"name": "gen_ai.agent.handoff.count", "kind": "counter", "pillar": "build", "domain": "Agents", "unit": "count", "title": "Agent Handoffs", "description": "Control handoffs between agents", "slo": {"op": "lt", "value": 6, "scope": "sum"}},
            {"name": "gen_ai.a2a.messages.count", "kind": "counter", "pillar": "build", "domain": "A2A", "unit": "count", "title": "A2A Messages", "description": "Agent-to-Agent protocol messages exchanged", "slo": None},
            {"name": "gen_ai.a2a.trace_context.propagated", "kind": "counter", "pillar": "build", "domain": "A2A", "unit": "count", "title": "W3C Trace Context Propagated", "description": "Spans carrying propagated W3C trace context across agents", "slo": None},
            {"name": "gen_ai.tool.calls.count", "kind": "counter", "pillar": "build", "domain": "Tools", "unit": "count", "title": "Tool Calls", "description": "Total tool executions", "slo": {"op": "lte", "value": 25, "scope": "sum"}},
            {"name": "gen_ai.tool.errors.count", "kind": "counter", "pillar": "build", "domain": "Tools", "unit": "count", "title": "Tool Failures", "description": "Tool execution failures", "slo": {"op": "eq", "value": 0, "scope": "sum"}},
            {"name": "gen_ai.tool.execution.duration", "kind": "histogram", "pillar": "build", "domain": "Tools", "unit": "ms", "title": "Tool Latency", "description": "Tool execution duration", "slo": {"op": "lt", "value": 3000, "scope": "avg"}},
            {"name": "gen_ai.tool.cache.hit", "kind": "counter", "pillar": "build", "domain": "Tools", "unit": "count", "title": "Tool Cache Hits", "description": "Tool results served from cache", "slo": None},
            {"name": "gen_ai.mcp.skill.invocations", "kind": "counter", "pillar": "build", "domain": "MCP", "unit": "count", "title": "MCP / Skill Invocations", "description": "Skill Registry / MCP connector calls", "slo": None}
        ],
        "scale": [
            {"name": "gen_ai.workflow.duration", "kind": "histogram", "pillar": "scale", "domain": "Workflow", "unit": "ms", "title": "Workflow Duration", "description": "End-to-end session duration", "slo": {"op": "lt", "value": 15000, "scope": "avg"}},
            {"name": "gen_ai.workflow.success.count", "kind": "counter", "pillar": "scale", "domain": "Workflow", "unit": "count", "title": "Workflow Successes", "description": "Successful workflow runs", "slo": None},
            {"name": "gen_ai.workflow.errors.count", "kind": "counter", "pillar": "scale", "domain": "Workflow", "unit": "count", "title": "Workflow Failures", "description": "Failed workflow runs", "slo": {"op": "eq", "value": 0, "scope": "sum"}},
            {"name": "gen_ai.workflow.active_agents", "kind": "updowncounter", "pillar": "scale", "domain": "Workflow", "unit": "count", "title": "Concurrently Active Agents", "description": "Agents active at once", "slo": None},
            {"name": "gen_ai.workflow.queue.delay", "kind": "histogram", "pillar": "scale", "domain": "Workflow", "unit": "ms", "title": "Event Queue Delay", "description": "Scheduling queue wait time", "slo": {"op": "lt", "value": 50, "scope": "avg"}},
            {"name": "gen_ai.scale.circuit_breaker.open", "kind": "updowncounter", "pillar": "scale", "domain": "Resilience", "unit": "count", "title": "Circuit Breakers Open", "description": "Dependencies with an open circuit breaker", "slo": {"op": "eq", "value": 0, "scope": "last"}},
            {"name": "gen_ai.scale.fallback.depth", "kind": "histogram", "pillar": "scale", "domain": "Resilience", "unit": "depth", "title": "Fallback Ladder Depth", "description": "Depth reached: Pro->Flash->Cached->Human", "slo": {"op": "lte", "value": 2, "scope": "avg"}},
            {"name": "gen_ai.scale.retry.count", "kind": "counter", "pillar": "scale", "domain": "Resilience", "unit": "count", "title": "Retry Attempts", "description": "Total agent/tool retries", "slo": {"op": "lte", "value": 3, "scope": "sum"}},
            {"name": "gen_ai.scale.retry_storm.indicator", "kind": "histogram", "pillar": "scale", "domain": "Resilience", "unit": "ratio", "title": "Retry-Storm / Blast Radius", "description": "Token amplification ratio under retry", "slo": {"op": "lt", "value": 3.0, "scope": "avg"}},
            {"name": "gen_ai.scale.exit_reason.completed", "kind": "counter", "pillar": "scale", "domain": "Exit Reasons", "unit": "count", "title": "Exit: Task Completed", "description": "Runs ending in successful completion", "slo": None},
            {"name": "gen_ai.scale.exit_reason.token_budget", "kind": "counter", "pillar": "scale", "domain": "Exit Reasons", "unit": "count", "title": "Exit: Token Budget Exceeded", "description": "Runs halted on token budget", "slo": {"op": "eq", "value": 0, "scope": "sum"}},
            {"name": "gen_ai.scale.exit_reason.max_turns", "kind": "counter", "pillar": "scale", "domain": "Exit Reasons", "unit": "count", "title": "Exit: Max Turns", "description": "Runs halted on max-turns limit", "slo": {"op": "lte", "value": 1, "scope": "sum"}},
            {"name": "gen_ai.scale.exit_reason.stuck_loop", "kind": "counter", "pillar": "scale", "domain": "Exit Reasons", "unit": "count", "title": "Exit: Stuck Loop", "description": "Runs terminated for looping", "slo": {"op": "eq", "value": 0, "scope": "sum"}},
            {"name": "gen_ai.system.cpu.utilization", "kind": "histogram", "pillar": "scale", "domain": "System", "unit": "%", "title": "CPU Utilization", "description": "Host CPU utilisation", "slo": {"op": "lt", "value": 80, "scope": "last"}},
            {"name": "gen_ai.system.memory.utilization", "kind": "histogram", "pillar": "scale", "domain": "System", "unit": "%", "title": "Memory Utilization", "description": "Host RAM utilisation", "slo": {"op": "lt", "value": 85, "scope": "last"}},
            {"name": "gen_ai.system.active.connections", "kind": "updowncounter", "pillar": "scale", "domain": "System", "unit": "count", "title": "Active Connections", "description": "Active consumer connections", "slo": {"op": "lt", "value": 200, "scope": "last"}}
        ],
        "govern": [
            {"name": "gen_ai.security.model_armor.prompt_injection", "kind": "counter", "pillar": "govern", "domain": "Model Armor", "unit": "count", "title": "Prompt Injection (PIJB)", "description": "Prompt-injection attempts blocked", "slo": {"op": "eq", "value": 0, "scope": "sum"}},
            {"name": "gen_ai.security.model_armor.jailbreak", "kind": "counter", "pillar": "govern", "domain": "Model Armor", "unit": "count", "title": "Jailbreak (PIJB)", "description": "Jailbreak attempts blocked", "slo": {"op": "eq", "value": 0, "scope": "sum"}},
            {"name": "gen_ai.security.model_armor.rai", "kind": "counter", "pillar": "govern", "domain": "Model Armor", "unit": "count", "title": "Responsible-AI Filter (RAI)", "description": "Responsible-AI policy blocks", "slo": {"op": "eq", "value": 0, "scope": "sum"}},
            {"name": "gen_ai.security.model_armor.csam", "kind": "counter", "pillar": "govern", "domain": "Model Armor", "unit": "count", "title": "CSAM Filter", "description": "CSAM detections blocked", "slo": {"op": "eq", "value": 0, "scope": "sum"}},
            {"name": "gen_ai.security.dlp.redactions", "kind": "counter", "pillar": "govern", "domain": "Cloud DLP", "unit": "count", "title": "Cloud DLP Redactions", "description": "PII tokens redacted", "slo": None},
            {"name": "gen_ai.security.pii_leak.blocked", "kind": "counter", "pillar": "govern", "domain": "Cloud DLP", "unit": "count", "title": "PII Leak Blocked", "description": "PII exfiltration attempts blocked", "slo": {"op": "eq", "value": 0, "scope": "sum"}},
            {"name": "gen_ai.security.confused_deputy.detected", "kind": "counter", "pillar": "govern", "domain": "Threats", "unit": "count", "title": "Confused Deputy Detected", "description": "Lethal-trifecta: private data + untrusted content + exfil path", "slo": {"op": "eq", "value": 0, "scope": "sum"}},
            {"name": "gen_ai.security.cloud_armor.blocked", "kind": "counter", "pillar": "govern", "domain": "Cloud Armor", "unit": "count", "title": "Cloud Armor Blocks", "description": "Requests blocked at the WAF perimeter", "slo": {"op": "lte", "value": 2, "scope": "sum"}},
            {"name": "gen_ai.security.cloud_armor.violations", "kind": "counter", "pillar": "govern", "domain": "Cloud Armor", "unit": "count", "title": "Cloud Armor Violations", "description": "SQLi / XSS violations flagged", "slo": {"op": "eq", "value": 0, "scope": "sum"}},
            {"name": "gen_ai.identity.attributed.count", "kind": "counter", "pillar": "govern", "domain": "Identity", "unit": "count", "title": "Attributed Actions (SPIFFE)", "description": "Actions with verified agent identity", "slo": None},
            {"name": "gen_ai.identity.act_claim.delegations", "kind": "histogram", "pillar": "govern", "domain": "Identity", "unit": "hops", "title": "Delegation Depth (act claim)", "description": "Delegation chain depth: who acted for whom", "slo": {"op": "lte", "value": 3, "scope": "avg"}},
            {"name": "gen_ai.identity.unauthorized.blocked", "kind": "counter", "pillar": "govern", "domain": "Identity", "unit": "count", "title": "Unauthorized Blocked (IAM)", "description": "Deterministic IAM / RLS denials (the real 403)", "slo": None}
        ],
        "optimize": [
            {"name": "gen_ai.latency.ttft", "kind": "histogram", "pillar": "optimize", "domain": "Latency", "unit": "ms", "title": "TTFT — Time To First Token", "description": "Time to first streamed token", "slo": {"op": "lt", "value": 800, "scope": "avg"}},
            {"name": "gen_ai.latency.ttfa", "kind": "histogram", "pillar": "optimize", "domain": "Latency", "unit": "ms", "title": "TTFA — Time To First Answer", "description": "Time to first answer token (excludes thinking)", "slo": {"op": "lt", "value": 2500, "scope": "avg"}},
            {"name": "gen_ai.latency.ttlt", "kind": "histogram", "pillar": "optimize", "domain": "Latency", "unit": "ms", "title": "TTLT — Time To Last Token", "description": "Time to last token (full response)", "slo": {"op": "lt", "value": 5000, "scope": "avg"}},
            {"name": "gen_ai.tokens.input", "kind": "counter", "pillar": "optimize", "domain": "Tokens", "unit": "tokens", "title": "Input Tokens", "description": "Uncached prompt input tokens", "slo": None},
            {"name": "gen_ai.tokens.cached", "kind": "counter", "pillar": "optimize", "domain": "Tokens", "unit": "tokens", "title": "Cached Tokens", "description": "Prompt tokens served from prefix cache", "slo": None},
            {"name": "gen_ai.tokens.output", "kind": "counter", "pillar": "optimize", "domain": "Tokens", "unit": "tokens", "title": "Output Tokens", "description": "Generated output tokens", "slo": None},
            {"name": "gen_ai.tokens.thinking", "kind": "counter", "pillar": "optimize", "domain": "Tokens", "unit": "tokens", "title": "Thinking Tokens", "description": "Chain-of-thought tokens (billed at output rate)", "slo": {"op": "lt", "value": 4000, "scope": "avg"}},
            {"name": "gen_ai.cost.prefix_cache.hit_ratio", "kind": "histogram", "pillar": "optimize", "domain": "Cost", "unit": "%", "title": "Prefix Cache Hit-Ratio", "description": "cachedContentTokens / promptTokens (~90% cost lever)", "slo": {"op": "gte", "value": 40, "scope": "avg"}},
            {"name": "gen_ai.cost.per_call", "kind": "histogram", "pillar": "optimize", "domain": "Cost", "unit": "usd", "title": "Cost per Call", "description": "Estimated blended cost per invocation", "slo": {"op": "lt", "value": 0.05, "scope": "avg"}},
            {"name": "gen_ai.cost.per_resolved_task", "kind": "histogram", "pillar": "optimize", "domain": "Cost", "unit": "usd", "title": "Cost per Resolved Task", "description": "Cost normalised to resolved tasks (the metric that matters)", "slo": {"op": "lt", "value": 0.2, "scope": "avg"}},
            {"name": "gen_ai.routing.tier.flash_lite", "kind": "counter", "pillar": "optimize", "domain": "Routing", "unit": "count", "title": "Routed: Flash-Lite / Gemma", "description": "Requests routed to the cheapest tier", "slo": None},
            {"name": "gen_ai.routing.tier.flash", "kind": "counter", "pillar": "optimize", "domain": "Routing", "unit": "count", "title": "Routed: Flash", "description": "Requests routed to the mid tier", "slo": None},
            {"name": "gen_ai.routing.tier.pro", "kind": "counter", "pillar": "optimize", "domain": "Routing", "unit": "count", "title": "Routed: Pro / Gemini 2.5", "description": "Requests routed to the deep-reasoning tier", "slo": None},
            {"name": "gen_ai.quality.autorater.score", "kind": "histogram", "pillar": "optimize", "domain": "Quality", "unit": "score", "title": "Autorater Quality Score", "description": "LLM-as-judge quality (1-5 rubric)", "slo": {"op": "gte", "value": 4.0, "scope": "avg"}},
            {"name": "gen_ai.quality.autorater.agreement_kappa", "kind": "histogram", "pillar": "optimize", "domain": "Quality", "unit": "kappa", "title": "Inter-Rater Agreement (kappa)", "description": "Cohen's kappa between autoraters", "slo": {"op": "gte", "value": 0.6, "scope": "avg"}},
            {"name": "gen_ai.quality.groundedness", "kind": "histogram", "pillar": "optimize", "domain": "Quality", "unit": "%", "title": "Groundedness", "description": "Answer grounded in retrieved context", "slo": {"op": "gte", "value": 85, "scope": "avg"}},
            {"name": "gen_ai.context.reasoning_drift", "kind": "histogram", "pillar": "optimize", "domain": "Context", "unit": "score", "title": "Reasoning Drift", "description": "Drift of reasoning from the original task", "slo": {"op": "lt", "value": 0.35, "scope": "avg"}},
            {"name": "gen_ai.context.rot.indicator", "kind": "histogram", "pillar": "optimize", "domain": "Context", "unit": "score", "title": "Context Rot", "description": "Attention decay as the window fills", "slo": {"op": "lt", "value": 0.4, "scope": "avg"}},
            {"name": "gen_ai.context.window.utilization", "kind": "histogram", "pillar": "optimize", "domain": "Context", "unit": "%", "title": "Context Window Utilization", "description": "Window fill %; compact at 50-60%", "slo": {"op": "lt", "value": 60, "scope": "avg"}},
            {"name": "gen_ai.context.compaction.events", "kind": "counter", "pillar": "optimize", "domain": "Context", "unit": "count", "title": "Compaction Events", "description": "Context compactions triggered", "slo": None}
        ]
    },
    "total": 57,
    "agents": {a: d["model_label"] for a, d in AGENTS.items()}
}

# ─── Observability State ───
class ObservabilityState:
    def __init__(self):
        self.reset()

    def reset(self):
        self.metrics: Dict[str, List[dict]] = {}
        self.alerts: List[dict] = []
        self.total_runs = 0
        self.successful_runs = 0
        self.failed_runs = 0
        self.total_cost = 0.0
        self.total_ttlt_ms = 0.0
        self.total_ttft_ms = 0.0
        self.total_input_tokens = 0
        self.total_cached_tokens = 0
        self.total_output_tokens = 0
        self.quality_scores: List[float] = []
        self.threat_incidents = 0

    def add_metric(self, name: str, value: float, attributes: dict = None):
        if name not in self.metrics:
            self.metrics[name] = []
        point = {"value": value, "timestamp": time.time()}
        if attributes:
            point["attributes"] = attributes
        self.metrics[name].append(point)

    def get_observability(self) -> dict:
        success_rate = (self.successful_runs / self.total_runs * 100.0) if self.total_runs > 0 else 100.0
        avg_ttlt = (self.total_ttlt_ms / self.total_runs) if self.total_runs > 0 else 0.0
        avg_cost = (self.total_cost / max(1, self.successful_runs)) if self.total_runs > 0 else 0.0
        total_prompt = self.total_input_tokens + self.total_cached_tokens
        cache_ratio = (self.total_cached_tokens / total_prompt * 100.0) if total_prompt > 0 else 0.0
        avg_quality = (sum(self.quality_scores) / len(self.quality_scores)) if self.quality_scores else 0.0

        risk_score = min(100, self.threat_incidents * 25)
        risk_band = "LOW"
        if risk_score > 70: risk_band = "CRITICAL"
        elif risk_score > 40: risk_band = "HIGH"
        elif risk_score > 0: risk_band = "MEDIUM"

        signals = {}
        for m in [m for p in CATALOG["metrics_by_pillar"].values() for m in p]:
            signals[m["name"]] = "green" if m["name"] in self.metrics and len(self.metrics[m["name"]]) > 0 else "grey"

        pillars_status = {}
        for p in CATALOG["pillars"]:
            breaches = len([a for a in self.alerts if a.get("pillar") == p])
            pillars_status[p] = {
                "label": CATALOG["pillars"][p], "breaches": breaches,
                "active": len(CATALOG["metrics_by_pillar"][p]),
                "status": "red" if breaches > 0 else ("green" if self.total_runs > 0 else "grey")
            }

        return {
            "metrics": self.metrics, "signals": signals, "alerts": self.alerts,
            "compliant": len(self.alerts) == 0, "pillars": pillars_status,
            "slo": {
                "success_rate": round(success_rate, 1), "ttlt_ms": round(avg_ttlt, 1),
                "ttft_ms": round(self.total_ttft_ms / max(1, self.total_runs), 1),
                "cost_per_task": round(avg_cost, 4), "cache_hit_ratio": round(cache_ratio, 1),
                "autorater_quality": round(avg_quality, 1),
                "risk_score": {"score": risk_score, "band": risk_band}
            },
            "generated_at": time.time()
        }

state = ObservabilityState()
engine = AgentEngine()
otel = MetricInstruments(state)

# ─── Simulation Flow ───
async def run_helpdesk_flow(scenario_key: str, custom_query: str = None):
    """Run full IT Helpdesk agent flow with real-time WebSocket events."""
    scenario = SCENARIOS.get(scenario_key)
    if not scenario and custom_query:
        # Custom query — classify first
        query = custom_query
    elif scenario:
        query = custom_query or scenario["query"]
    else:
        query = custom_query or "I need help with my account."

    session_id = f"sess-{uuid.uuid4().hex[:8]}"
    workflow_start = time.perf_counter()
    total_cost = 0.0

    # Security screening
    screening = screen_input(query)

    # 1. Start
    await manager.broadcast({"type": "start", "session_id": session_id, "scenario": scenario_key})
    await asyncio.sleep(0.2)

    # 2. Triage Agent classifies intent
    await manager.broadcast({"type": "agent_call", "author": "triage_agent", "data": {"status": "classifying", "query": query}})
    triage_start = time.perf_counter()
    classification = await engine.classify(query)
    triage_ms = (time.perf_counter() - triage_start) * 1000
    cost, _ = otel.record_agent_call("triage_agent", triage_ms, classification["input_tokens"], classification["output_tokens"], "flash")
    total_cost += cost

    category = classification["category"]
    target_agent = ROUTE_MAP.get(category, "identity_agent")

    # Use scenario definition if available, else use classification
    if scenario:
        target_agent = scenario["target_agent"]
        tools_sequence = scenario["tools_sequence"]
        tool_args_sequence = scenario["tool_args_sequence"]
    else:
        tools_sequence = AGENTS[target_agent]["tools"]
        tool_args_sequence = [{} for _ in tools_sequence]

    await asyncio.sleep(0.2)

    # 3. Handoff to specialist
    otel.record_handoff("triage_agent", target_agent)
    await manager.broadcast({"type": "handoff", "author": target_agent, "from": "triage_agent", "to": target_agent})
    await asyncio.sleep(0.3)

    # 4. Specialist agent processes
    await manager.broadcast({"type": "agent_call", "author": target_agent, "data": {"status": "processing"}})
    specialist_start = time.perf_counter()
    specialist_result = await engine.run_specialist(target_agent, query)
    specialist_ms = (time.perf_counter() - specialist_start) * 1000
    cost, _ = otel.record_agent_call(target_agent, specialist_ms, specialist_result["input_tokens"], specialist_result["output_tokens"], specialist_result["model"])
    total_cost += cost
    await asyncio.sleep(0.2)

    # 5. Tool calls
    for i, tool_name in enumerate(tools_sequence):
        if tool_name not in TOOL_REGISTRY:
            continue
        tool_fn = TOOL_REGISTRY[tool_name]
        args = tool_args_sequence[i] if i < len(tool_args_sequence) else {}

        await manager.broadcast({"type": "tool_call", "author": target_agent, "data": {"tool_call": {"name": tool_name, "args": args}}})

        tool_start = time.perf_counter()
        try:
            result = await tool_fn(**args)
            tool_ms = (time.perf_counter() - tool_start) * 1000
            otel.record_tool_call(tool_name, tool_ms, success=True)
        except Exception:
            tool_ms = (time.perf_counter() - tool_start) * 1000
            otel.record_tool_call(tool_name, tool_ms, success=False)
            result = {"status": "error"}

        await manager.broadcast({"type": "tool_response", "author": target_agent, "data": {"tool_response": {"name": tool_name, "output": result}}})
        await asyncio.sleep(0.3)

    # 6. Complete
    workflow_ms = (time.perf_counter() - workflow_start) * 1000
    otel.record_workflow_complete(workflow_ms, total_cost, success=True)

    await manager.broadcast({"type": "complete", "session_id": session_id, "duration_ms": round(workflow_ms, 1), "cost": round(total_cost, 6)})

# ─── Routes ───
@app.get("/", response_class=HTMLResponse)
async def get_index():
    return HTMLResponse(content=(BASE_DIR / "static" / "index.html").read_text(encoding="utf-8"))

@app.get("/api/config")
async def get_config():
    return {
        "app_env": "production", "gcp_project": engine.project_id, "gcp_location": engine.location,
        "service_name": "geap-it-helpdesk", "engine": "live_gemini" if engine.is_live else "simulation",
        "is_live_gemini": engine.is_live, "is_otlp_enabled": False,
        "use_gcp_exporter": True, "otlp_endpoint": "in-memory (local reader)",
        "platform": "Gemini Enterprise Agent Platform (GEAP) aligned"
    }

@app.get("/api/catalog")
async def get_catalog():
    return CATALOG

@app.get("/api/observability")
async def get_observability():
    return state.get_observability()

@app.post("/api/reset")
async def reset_metrics():
    state.reset()
    return {"status": "ok", "message": "All metric accumulators reset."}

@app.post("/api/simulate")
async def simulate_flow(scenario: str = "password_reset"):
    asyncio.create_task(run_helpdesk_flow(scenario))
    return {"status": "initiated", "scenario": scenario}

@app.post("/api/chat")
async def chat_flow(query: str):
    asyncio.create_task(run_helpdesk_flow(scenario_key="custom", custom_query=query))
    return {"status": "initiated", "query": query}

@app.post("/api/inject-threat")
async def inject_threat(kind: str):
    otel.record_threat(kind)
    threat_titles = {
        "prompt_injection": "Prompt Injection Blocked",
        "jailbreak": "Jailbreak Attempt Intercepted",
        "pii_leak": "PII Exfiltration Blocked by DLP",
        "confused_deputy": "Confused Deputy Attack Flagged"
    }
    state.alerts.append({
        "severity": "critical" if kind == "confused_deputy" else "high",
        "pillar": "govern", "domain": "Model Armor",
        "title": threat_titles.get(kind, "Unknown Threat"),
        "actual": 1, "op": "eq", "threshold": 0, "unit": "count",
        "time": time.strftime("%H:%M:%S")
    })
    # Also record a failed workflow for the threat
    otel.record_workflow_complete(1200, 0.015, success=False)
    await manager.broadcast({"type": "alert", "threat": kind, "timestamp": time.time()})
    return {"status": "ok", "threat_injected": kind}

@app.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/api/stream")
async def sse_stream(request: Request):
    async def event_generator():
        while True:
            if await request.is_disconnected():
                break
            yield f"data: {json.dumps({'type': 'ping', 'timestamp': time.time()})}\n\n"
            await asyncio.sleep(5)
    return StreamingResponse(event_generator(), media_type="text/event-stream")
