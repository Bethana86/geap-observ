import asyncio
import random
import time
import uuid

async def reset_ad_password(employee_id: str) -> dict:
    """Reset Active Directory password for an employee."""
    await asyncio.sleep(random.uniform(0.1, 0.4))
    temp_pass = f"Temp{random.randint(1000,9999)}!"
    return {"status": "success", "employee_id": employee_id, "temporary_password": temp_pass, "expires_in": "24 hours", "message": f"Password reset for {employee_id}. Temporary password issued."}

async def send_mfa_token(employee_id: str, method: str = "email") -> dict:
    """Send MFA verification token to employee."""
    await asyncio.sleep(random.uniform(0.1, 0.3))
    return {"status": "sent", "employee_id": employee_id, "method": method, "token_id": uuid.uuid4().hex[:8], "expires_in": "5 minutes"}

async def deploy_software(package_name: str, device_id: str) -> dict:
    """Deploy software package via SCCM."""
    await asyncio.sleep(random.uniform(0.2, 0.5))
    return {"status": "deploying", "package": package_name, "device": device_id, "deployment_id": f"DEP-{random.randint(10000,99999)}", "eta_minutes": random.randint(5, 20), "message": f"{package_name} deployment initiated on {device_id}"}

async def check_license_pool(software_name: str) -> dict:
    """Check available licenses in the pool."""
    await asyncio.sleep(random.uniform(0.1, 0.3))
    total = random.randint(50, 500)
    used = random.randint(10, total - 5)
    return {"software": software_name, "total_licenses": total, "used": used, "available": total - used, "compliance": "ok" if (total - used) > 0 else "exceeded"}

async def create_pagerduty_incident(title: str, severity: str = "high", service: str = "production") -> dict:
    """Create a PagerDuty incident."""
    await asyncio.sleep(random.uniform(0.2, 0.4))
    return {"status": "created", "incident_id": f"PD-{random.randint(100000,999999)}", "title": title, "severity": severity, "service": service, "on_call": f"engineer-{random.randint(1,10)}@company.com", "escalation_policy": "P1 - 15min response"}

async def query_datadog_metrics(service_name: str, metric: str = "error_rate") -> dict:
    """Query Datadog for service health metrics."""
    await asyncio.sleep(random.uniform(0.1, 0.4))
    return {"service": service_name, "metric": metric, "current_value": round(random.uniform(0.1, 15.0), 2), "threshold": 5.0, "status": random.choice(["critical", "warning", "healthy"]), "last_5min_avg": round(random.uniform(0.5, 12.0), 2), "anomaly_detected": random.choice([True, False])}

async def restart_service_ansible(service_name: str, host: str = "prod-server-01") -> dict:
    """Restart a service via Ansible playbook."""
    await asyncio.sleep(random.uniform(0.3, 0.5))
    return {"status": "restarted", "service": service_name, "host": host, "playbook_id": f"ANS-{random.randint(10000,99999)}", "downtime_seconds": random.randint(3, 15), "health_check": "passing"}

async def create_servicenow_approval(request_type: str, resource: str, requester: str) -> dict:
    """Create a ServiceNow approval workflow."""
    await asyncio.sleep(random.uniform(0.2, 0.4))
    return {"status": "pending_approval", "ticket_id": f"REQ-{random.randint(100000,999999)}", "request_type": request_type, "resource": resource, "requester": requester, "approver": f"manager-{random.randint(1,5)}@company.com", "sla": "4 business hours"}

async def assign_iam_role(user_id: str, role: str, resource: str) -> dict:
    """Assign an IAM role to a user for a specific resource."""
    await asyncio.sleep(random.uniform(0.1, 0.3))
    return {"status": "assigned", "user": user_id, "role": role, "resource": resource, "effective_at": "immediately", "expires": "90 days", "audit_log_id": f"AUD-{uuid.uuid4().hex[:8]}"}

# Tool registry for lookup by name
TOOL_REGISTRY = {
    "reset_ad_password": reset_ad_password,
    "send_mfa_token": send_mfa_token,
    "deploy_software": deploy_software,
    "check_license_pool": check_license_pool,
    "create_pagerduty_incident": create_pagerduty_incident,
    "query_datadog_metrics": query_datadog_metrics,
    "restart_service_ansible": restart_service_ansible,
    "create_servicenow_approval": create_servicenow_approval,
    "assign_iam_role": assign_iam_role,
}

TOOL_LABELS = {
    "reset_ad_password": "AD Reset",
    "send_mfa_token": "MFA Token",
    "deploy_software": "SCCM Deploy",
    "check_license_pool": "License Chk",
    "create_pagerduty_incident": "PagerDuty",
    "query_datadog_metrics": "Datadog",
    "restart_service_ansible": "Ansible",
    "create_servicenow_approval": "ServiceNow",
    "assign_iam_role": "IAM Role",
}
