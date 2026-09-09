# GEAP Enterprise IT Helpdesk — Observability Platform

> Full-lifecycle **Build · Scale · Govern · Optimize · Evaluate** observability for agentic AI workflows, powered by Gemini on Vertex AI.

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi)
![Gemini](https://img.shields.io/badge/Gemini-2.5_Pro/Flash-4285F4?logo=google)
![License](https://img.shields.io/badge/License-MIT-green)

---

## 🧠 What Is This?

A real-time observability dashboard for monitoring **multi-agent AI systems** in production. It tracks **84 OpenTelemetry-aligned metrics** across 5 governance pillars, with live DAG visualization of agent handoffs, tool calls, model-tier routing, granular tokenomics attribution, and LLM-as-judge automated evaluation with golden benchmark testing.

Built as an **Enterprise IT Helpdesk** — 5 specialized agents resolve employee tickets (password resets, software installs, incident response, access requests) while the platform monitors every aspect of the workflow.

---

## 🏗️ Architecture

```
Employee Query
      │
      ▼
┌─────────────┐
│ Triage Agent│  (Gemini Flash — classifies intent)
│   ROUTER    │
└──────┬──────┘
       │
  ┌────┼────────┬──────────┐
  ▼    ▼        ▼          ▼
┌────┐┌────┐ ┌────────┐ ┌──────┐
│ ID ││ SW │ │INCIDENT│ │ACCESS│
│Agent││Agent│ │ Agent  │ │Agent │
│Flash││Flash│ │  Pro   │ │ Pro  │
└──┬─┘└──┬─┘ └───┬────┘ └──┬───┘
   │     │       │         │
   ▼     ▼       ▼         ▼
AD Reset License  Datadog  ServiceNow
MFA Token SCCM   PagerDuty IAM Role
                  Ansible
```

---

## ✨ Features

### 5 Specialized Agents
| Agent | Model | Purpose |
|-------|-------|---------|
| **Triage** | Gemini 2.5 Flash | Intent classification & routing |
| **Identity** | Gemini 2.5 Flash | Password resets, MFA, account recovery |
| **Software** | Gemini 2.5 Flash | Software installs, license management |
| **Incident** | Gemini 2.5 Pro | Production outages, SRE response |
| **Access** | Gemini 2.5 Pro | Access requests, IAM provisioning |

### 9 Enterprise Tools
| Tool | Integration |
|------|-------------|
| `reset_ad_password` | Active Directory |
| `send_mfa_token` | MFA Provider |
| `check_license_pool` | License Server |
| `deploy_software` | SCCM |
| `query_datadog_metrics` | Datadog |
| `create_pagerduty_incident` | PagerDuty |
| `restart_service_ansible` | Ansible |
| `create_servicenow_approval` | ServiceNow |
| `assign_iam_role` | IAM / RBAC |

### 84 OTel Metrics Across 5 Pillars

| Pillar | Metrics | What It Tracks |
|--------|---------|----------------|
| **Build** | 9 | Agent calls, handoffs, A2A messages, tool execution, MCP skills |
| **Scale** | 16 | Workflow duration, circuit breakers, retry storms, exit reasons, system resources |
| **Govern** | 12 | Prompt injection, jailbreak, PII/DLP, Cloud Armor, SPIFFE identity |
| **Optimize** | 32 | Latency, tokens, tokenomics (per-agent/model cost), cache savings, budget utilization |
| **Evaluate** | 15 | Task accuracy, routing accuracy, tool selection, hallucination, CSAT, benchmark pass rate |

### Real-Time Dashboard
- **Live DAG visualization** — Watch agent handoffs and tool calls animate in real-time
- **Tokenomics Strip** — Track input/cached/output tokens, spend, cache savings ratio, daily budget progress
- **Agent Evaluation Scorecard** — Task accuracy, routing accuracy, tool selection, hallucination rate, and 12-test golden benchmark runner
- **WebSocket streaming** — Sub-second event propagation
- **Executive KPI strip** — Success rate, latency, cost, cache hit ratio, quality score, risk score
- **Pillar compliance strip** — At-a-glance status across Build/Scale/Govern/Optimize/Evaluate
- **Alert panel** — SLO breaches, security incidents, and quality regression alerts
- **Dark/Light theme** — Toggle with one click

---

## 🚀 Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/Bethana86/geap-observ.git
cd geap-observ
pip install -r requirements.txt
```

### 2. Run (Simulation Mode)

```bash
python run.py
```

Open **http://localhost:8000** — select a scenario and click **Execute Selected Flow**.

### 3. Run (Live Gemini via Vertex AI)

```bash
# Authenticate with GCP
gcloud auth application-default login

# Set your project
export GOOGLE_CLOUD_PROJECT=your-project-id        # Linux/Mac
$env:GOOGLE_CLOUD_PROJECT = "your-project-id"      # PowerShell

# Start
python run.py
```

The dashboard header will show **Engine: LIVE GEMINI** when connected.

---

## 📂 Project Structure

```
geap-observ/
├── .gitignore
├── requirements.txt          # fastapi, uvicorn, websockets, google-genai
├── run.py                    # Server launcher (port 8000)
└── app/
    ├── main.py               # FastAPI app — routes, WebSocket hub, flow orchestrator
    ├── agents.py             # 5 agent definitions + AgentEngine (Vertex AI + fallback)
    ├── tools.py              # 9 enterprise tool implementations + registry
    ├── telemetry.py          # MetricInstruments — records all 57 OTel metrics
    ├── security.py           # Prompt injection detection + PII scanning
    └── static/
        ├── index.html        # Dashboard HTML — DAG, KPIs, metric cards
        ├── css/style.css     # Full stylesheet (dark/light themes)
        └── js/
            ├── api.js        # REST API client
            ├── charts.js     # Chart.js rendering factory
            ├── dag.js        # Live agent flow DAG animation
            ├── dashboard.js  # Metric card builder + updater
            ├── main.js       # App entry point + controls
            ├── realtime.js   # WebSocket/SSE client
            └── terminal.js   # Session badge tracker
```

---

## 🎯 4 Preset Scenarios

| # | Scenario | Flow | Tools |
|---|----------|------|-------|
| 🔑 | **Password Reset** | Triage → Identity | AD Reset, MFA Token |
| 📥 | **Software Install** | Triage → Software | License Check, SCCM Deploy |
| 🔴 | **System Outage** | Triage → Incident | Datadog, PagerDuty, Ansible |
| 🔓 | **Access Request** | Triage → Access | ServiceNow, IAM Role |

You can also type **any custom IT query** in the prompt box — the Triage Agent classifies it automatically.

---

## 🛡️ Security Features

- **Prompt Injection Detection** — Pattern-based screening for injection, jailbreak, DAN mode
- **PII Scanning** — Detects SSN, credit cards, emails, phone numbers, IP addresses
- **Cloud DLP Redaction** — Auto-redacts sensitive data before agent processing
- **Threat Injection Demo** — Click Govern buttons to simulate prompt injection, jailbreak, PII leak, confused deputy attacks

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Dashboard UI |
| `GET` | `/api/config` | Platform configuration & engine status |
| `GET` | `/api/catalog` | Full metric catalog (84 metrics, 5 pillars) |
| `GET` | `/api/observability` | Live metrics, signals, alerts, SLOs |
| `GET` | `/api/tokenomics` | Token breakdown, per-agent cost attribution, budget utilization |
| `GET` | `/api/evaluation` | Evaluation summary — task accuracy, hallucination, CSAT |
| `POST` | `/api/evaluation/benchmark` | Execute 12-test golden dataset routing benchmark |
| `POST` | `/api/simulate?scenario=` | Execute a preset scenario |
| `POST` | `/api/chat?query=` | Run a custom natural language query |
| `POST` | `/api/inject-threat?kind=` | Inject a security threat for demo |
| `POST` | `/api/reset` | Reset all metric accumulators & evaluation history |
| `WS` | `/api/ws` | WebSocket for real-time events |
| `GET` | `/api/stream` | SSE fallback stream |

---

## 🧩 Extending

### Add a New Agent

1. Add agent definition in `app/agents.py` → `AGENTS` dict
2. Add routing in `ROUTE_MAP`
3. Add scenario in `SCENARIOS`
4. Add DAG node in `index.html`
5. Update `dag.js` with new node/link IDs

### Add a New Tool

1. Create async function in `app/tools.py`
2. Register in `TOOL_REGISTRY`
3. Add to an agent's `tools` list in `agents.py`
4. Add tool anchor in `index.html`

### Switch to Production OTel

Replace `MetricInstruments` in `telemetry.py` with real OpenTelemetry SDK:

```python
from opentelemetry import metrics
meter = metrics.get_meter("geap-helpdesk")
agent_calls = meter.create_counter("gen_ai.agent.calls.count")
```

---

## 📊 Cost Estimates

| Scale | Tickets/Month | Monthly Cost |
|-------|--------------|-------------:|
| Small | 500 | **$7 – $9** |
| Medium | 5,000 | **$95 – $200** |
| Enterprise | 50,000 | **$255 – $507** |

> Free tier covers ~500 tickets/month at $0.

---

## 🛠️ Tech Stack

- **Backend**: Python 3.11+, FastAPI, Uvicorn, WebSockets
- **Frontend**: Vanilla JS (ES Modules), Chart.js, Font Awesome
- **AI**: Google Gemini 2.5 Pro/Flash via Vertex AI (`google-genai`)
- **Observability**: OpenTelemetry-aligned metric schema (57 metrics)
- **Security**: Pattern-based prompt injection + PII detection

---

## 📜 License

MIT

---

Built with 🧠 by GEAP — Gemini Enterprise Agent Platform
