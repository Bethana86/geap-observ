import os
import json
import asyncio
import random
import time

# Try to import google-genai for real Gemini
try:
    from google import genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

from app.tools import TOOL_REGISTRY

# Agent definitions
AGENTS = {
    "triage_agent": {
        "name": "Triage Agent",
        "model": "gemini-2.5-flash",
        "model_label": "Gemini 2.5 Flash",
        "instruction": """You are the IT Helpdesk Triage Agent. Classify the user's request into exactly one category:
- password_reset: Password resets, account lockouts, login issues
- software_install: Software installation, license requests, application issues
- system_outage: Server down, service outage, performance degradation, production issues
- access_request: Access to systems, SharePoint, databases, role assignments

Respond with ONLY a JSON object: {"category": "<category>", "summary": "<brief summary>", "priority": "<low|medium|high|critical>"}""",
        "tools": []
    },
    "identity_agent": {
        "name": "Identity Agent",
        "model": "gemini-2.5-flash",
        "model_label": "Gemini 2.5 Flash",
        "instruction": "You are the Identity & Access Management agent. You handle password resets, MFA token management, and account recovery. Be helpful and security-conscious.",
        "tools": ["reset_ad_password", "send_mfa_token"]
    },
    "software_agent": {
        "name": "Software Agent",
        "model": "gemini-2.5-flash",
        "model_label": "Gemini 2.5 Flash",
        "instruction": "You are the Software Provisioning agent. You handle software installations, license checks, and application deployments via SCCM.",
        "tools": ["check_license_pool", "deploy_software"]
    },
    "incident_agent": {
        "name": "Incident Agent",
        "model": "gemini-2.5-pro",
        "model_label": "Gemini 2.5 Pro",
        "instruction": "You are the Incident Response agent. You handle production outages, service degradation, and system failures. You can query metrics, create PagerDuty incidents, and restart services.",
        "tools": ["query_datadog_metrics", "create_pagerduty_incident", "restart_service_ansible"]
    },
    "access_agent": {
        "name": "Access Agent",
        "model": "gemini-2.5-pro",
        "model_label": "Gemini 2.5 Pro",
        "instruction": "You are the Access Provisioning agent. You handle access requests, permission grants, and role assignments through ServiceNow approvals and IAM.",
        "tools": ["create_servicenow_approval", "assign_iam_role"]
    }
}

# Scenario definitions
SCENARIOS = {
    "password_reset": {
        "title": "Password Reset",
        "query": "I forgot my VPN password and I'm locked out of my account. Employee ID: EMP-4521.",
        "triage_category": "password_reset",
        "target_agent": "identity_agent",
        "tools_sequence": ["reset_ad_password", "send_mfa_token"],
        "tool_args_sequence": [
            {"employee_id": "EMP-4521"},
            {"employee_id": "EMP-4521", "method": "email"}
        ]
    },
    "software_install": {
        "title": "Software Install",
        "query": "I need Tableau Desktop installed on my laptop LAPTOP-7832 for the analytics team.",
        "triage_category": "software_install",
        "target_agent": "software_agent",
        "tools_sequence": ["check_license_pool", "deploy_software"],
        "tool_args_sequence": [
            {"software_name": "Tableau Desktop"},
            {"package_name": "Tableau Desktop", "device_id": "LAPTOP-7832"}
        ]
    },
    "system_outage": {
        "title": "System Outage",
        "query": "The production payment service is returning 500 errors and customers can't complete orders!",
        "triage_category": "system_outage",
        "target_agent": "incident_agent",
        "tools_sequence": ["query_datadog_metrics", "create_pagerduty_incident", "restart_service_ansible"],
        "tool_args_sequence": [
            {"service_name": "payment-service", "metric": "error_rate"},
            {"title": "Payment Service 500 Errors", "severity": "critical", "service": "payment-service"},
            {"service_name": "payment-service", "host": "prod-payment-01"}
        ]
    },
    "access_request": {
        "title": "Access Request",
        "query": "I need read access to the Finance SharePoint site for the quarterly audit. I'm user john.doe@company.com.",
        "triage_category": "access_request",
        "target_agent": "access_agent",
        "tools_sequence": ["create_servicenow_approval", "assign_iam_role"],
        "tool_args_sequence": [
            {"request_type": "SharePoint Access", "resource": "Finance SharePoint", "requester": "john.doe@company.com"},
            {"user_id": "john.doe@company.com", "role": "Reader", "resource": "Finance SharePoint"}
        ]
    }
}

ROUTE_MAP = {
    "password_reset": "identity_agent",
    "software_install": "software_agent",
    "system_outage": "incident_agent",
    "access_request": "access_agent"
}


class AgentEngine:
    """Runs agent workflows with real Gemini or simulation fallback."""

    def __init__(self):
        self.client = None
        self.is_live = False
        self.project_id = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT_ID", "")
        self.location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")

        if HAS_GENAI and self.project_id:
            try:
                self.client = genai.Client(
                    vertexai=True,
                    project=self.project_id,
                    location=self.location,
                )
                self.is_live = True
            except Exception:
                self.is_live = False

    async def classify(self, query: str) -> dict:
        """Use triage agent to classify intent."""
        if self.is_live:
            try:
                agent_def = AGENTS["triage_agent"]
                response = self.client.models.generate_content(
                    model=agent_def["model"],
                    contents=f"{agent_def['instruction']}\n\nUser query: {query}"
                )
                result = json.loads(response.text.strip().strip('`').replace('json\n', ''))
                return {
                    "category": result.get("category", "password_reset"),
                    "summary": result.get("summary", query[:100]),
                    "priority": result.get("priority", "medium"),
                    "input_tokens": getattr(response.usage_metadata, 'prompt_token_count', 500),
                    "output_tokens": getattr(response.usage_metadata, 'candidates_token_count', 100),
                }
            except Exception:
                pass
        # Simulation fallback
        await asyncio.sleep(random.uniform(0.2, 0.5))
        q = query.lower()
        if any(w in q for w in ["password", "locked", "login", "forgot", "reset", "vpn"]):
            cat = "password_reset"
        elif any(w in q for w in ["install", "software", "license", "tableau", "application", "app"]):
            cat = "software_install"
        elif any(w in q for w in ["down", "outage", "error", "500", "crash", "slow", "production", "incident"]):
            cat = "system_outage"
        elif any(w in q for w in ["access", "permission", "sharepoint", "role", "grant", "database"]):
            cat = "access_request"
        else:
            cat = "password_reset"
        return {
            "category": cat,
            "summary": query[:100],
            "priority": "high" if cat == "system_outage" else "medium",
            "input_tokens": random.randint(400, 800),
            "output_tokens": random.randint(50, 150),
        }

    async def run_specialist(self, agent_name: str, query: str) -> dict:
        """Run a specialist agent to generate a response."""
        agent_def = AGENTS.get(agent_name, AGENTS["identity_agent"])
        if self.is_live:
            try:
                response = self.client.models.generate_content(
                    model=agent_def["model"],
                    contents=f"{agent_def['instruction']}\n\nUser request: {query}\n\nProvide a helpful response."
                )
                return {
                    "response": response.text,
                    "input_tokens": getattr(response.usage_metadata, 'prompt_token_count', 800),
                    "output_tokens": getattr(response.usage_metadata, 'candidates_token_count', 300),
                    "model": agent_def["model"]
                }
            except Exception:
                pass
        # Simulation fallback
        await asyncio.sleep(random.uniform(0.3, 0.7))
        responses = {
            "identity_agent": f"I've initiated a password reset for the requested account. A temporary password has been generated and an MFA verification token has been sent. The user should check their email for the reset instructions.",
            "software_agent": f"I've checked the license availability and initiated the software deployment. The package will be deployed to the target device within the estimated time.",
            "incident_agent": f"I've analyzed the service metrics and detected anomalies. A PagerDuty incident has been created with critical severity and the on-call engineer has been notified. I've also initiated a service restart.",
            "access_agent": f"I've submitted the access request through ServiceNow for approval. The IAM role will be assigned once the manager approves. Expected SLA is 4 business hours."
        }
        return {
            "response": responses.get(agent_name, "Request processed successfully."),
            "input_tokens": random.randint(600, 1500),
            "output_tokens": random.randint(200, 600),
            "model": agent_def["model"]
        }
