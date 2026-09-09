"""Agent evaluation engine — scoring, benchmarks, and regression detection."""
import random
import time
import os
from typing import Dict, List


# Benchmark test cases (golden dataset)
BENCHMARK_SUITE = {
    "triage_routing": [
        {"query": "I forgot my VPN password", "expected_category": "password_reset"},
        {"query": "Install Visual Studio on my laptop", "expected_category": "software_install"},
        {"query": "Production API is returning 500 errors", "expected_category": "system_outage"},
        {"query": "I need access to the HR database", "expected_category": "access_request"},
        {"query": "My account is locked after too many attempts", "expected_category": "password_reset"},
        {"query": "Deploy Kubernetes update to staging", "expected_category": "system_outage"},
        {"query": "Request read permissions to finance S3 bucket", "expected_category": "access_request"},
        {"query": "Adobe Creative Suite license renewal", "expected_category": "software_install"},
        {"query": "WiFi keeps disconnecting in Building B", "expected_category": "system_outage"},
        {"query": "Reset MFA token for contractor account", "expected_category": "password_reset"},
        {"query": "Need Tableau Desktop for quarterly reporting", "expected_category": "software_install"},
        {"query": "Grant DBA access to production MySQL", "expected_category": "access_request"},
    ],
    "tool_selection": [
        {"scenario": "password_reset", "expected_tools": ["reset_ad_password", "send_mfa_token"]},
        {"scenario": "software_install", "expected_tools": ["check_license_pool", "deploy_software"]},
        {"scenario": "system_outage", "expected_tools": ["query_datadog_metrics", "create_pagerduty_incident", "restart_service_ansible"]},
        {"scenario": "access_request", "expected_tools": ["create_servicenow_approval", "assign_iam_role"]},
    ]
}


class AgentEvaluator:
    """Evaluates agent performance across multiple dimensions."""

    def __init__(self, state):
        self.state = state
        self.eval_history: List[dict] = []
        self.baseline_scores: Dict[str, float] = {}

    def evaluate_response(self, agent_name: str, query: str, response: str,
                          expected_category: str = None, actual_category: str = None,
                          tools_used: list = None, expected_tools: list = None,
                          duration_ms: float = 0) -> dict:
        """Score a single agent response across all dimensions."""
        scores = {}
        s = self.state

        # 1. Routing accuracy (triage only)
        if expected_category and actual_category:
            routing_correct = expected_category == actual_category
            scores["routing_accuracy"] = 100.0 if routing_correct else 0.0
            s.add_metric("gen_ai.eval.routing_accuracy", scores["routing_accuracy"])

        # 2. Tool selection accuracy
        if expected_tools and tools_used:
            correct_tools = set(expected_tools) & set(tools_used)
            scores["tool_selection_accuracy"] = round(
                len(correct_tools) / len(expected_tools) * 100, 1)
            s.add_metric("gen_ai.eval.tool_selection_accuracy",
                         scores["tool_selection_accuracy"])

        # 3. Response quality (LLM-as-judge simulation)
        scores["relevance"] = round(random.uniform(3.8, 5.0), 1)
        scores["completeness"] = round(random.uniform(3.5, 5.0), 1)
        scores["safety"] = round(random.uniform(4.5, 5.0), 1)
        s.add_metric("gen_ai.eval.response_relevance", scores["relevance"])
        s.add_metric("gen_ai.eval.response_completeness", scores["completeness"])
        s.add_metric("gen_ai.eval.safety_score", scores["safety"])

        # 4. Hallucination check (simulated — in production use a grounding check)
        scores["hallucination_rate"] = round(random.uniform(0.0, 8.0), 1)
        s.add_metric("gen_ai.eval.hallucination_rate", scores["hallucination_rate"])

        # 5. Task accuracy (composite)
        task_score = round((scores["relevance"] + scores["completeness"]) / 2 * 20, 1)
        scores["task_accuracy"] = min(100.0, task_score)
        s.add_metric("gen_ai.eval.task_accuracy", scores["task_accuracy"])

        # 6. Per-agent quality score (attributed)
        agent_score = round(
            (scores["relevance"] + scores["completeness"] + scores["safety"]) / 3, 1)
        scores["agent_score"] = agent_score
        s.add_metric("gen_ai.eval.per_agent_score", agent_score,
                      {"gen_ai.agent.name": agent_name})

        # 7. Latency SLO compliance
        slo_ms = 5000
        scores["latency_slo_compliance"] = 100.0 if duration_ms < slo_ms else 0.0
        s.add_metric("gen_ai.eval.latency_slo_compliance",
                      scores["latency_slo_compliance"])

        # 8. First contact resolution & escalation
        scores["first_contact_resolution"] = round(random.uniform(85.0, 99.0), 1)
        scores["human_escalation_rate"] = round(random.uniform(1.0, 12.0), 1)
        scores["user_satisfaction"] = round(random.uniform(3.8, 5.0), 1)
        s.add_metric("gen_ai.eval.first_contact_resolution",
                      scores["first_contact_resolution"])
        s.add_metric("gen_ai.eval.human_escalation_rate",
                      scores["human_escalation_rate"])
        s.add_metric("gen_ai.eval.user_satisfaction",
                      scores["user_satisfaction"])

        # 9. Regression detection
        self._check_regression(agent_name, agent_score)

        # Store history
        self.eval_history.append({
            "agent": agent_name, "timestamp": time.time(),
            "scores": scores, "query": query[:100]
        })

        return scores

    def _check_regression(self, agent_name: str, current_score: float):
        """Detect quality regression vs baseline."""
        key = f"baseline_{agent_name}"
        if key not in self.baseline_scores:
            self.baseline_scores[key] = current_score
            return

        baseline = self.baseline_scores[key]
        delta = current_score - baseline
        self.state.add_metric("gen_ai.eval.benchmark.score_delta", round(delta, 2))

        if delta < -0.5:
            self.state.add_metric("gen_ai.eval.regression_detected", 1)
            self.state.alerts.append({
                "severity": "warning", "pillar": "evaluate",
                "domain": "Evaluation",
                "title": f"Quality regression: {agent_name} dropped {abs(delta):.1f} pts",
                "actual": round(current_score, 1),
                "op": "gte", "threshold": round(baseline, 1),
                "unit": "score", "time": time.strftime("%H:%M:%S")
            })

        # Update rolling baseline (80% old, 20% new)
        self.baseline_scores[key] = round((baseline * 0.8 + current_score * 0.2), 2)

    async def run_benchmark(self, engine) -> dict:
        """Run the full benchmark suite and return results."""
        results = {"triage_routing": [], "tool_selection": [], "overall": {}}

        # Test triage routing
        correct = 0
        for test in BENCHMARK_SUITE["triage_routing"]:
            classification = await engine.classify(test["query"])
            is_correct = classification["category"] == test["expected_category"]
            correct += int(is_correct)
            results["triage_routing"].append({
                "query": test["query"],
                "expected": test["expected_category"],
                "actual": classification["category"],
                "passed": is_correct
            })

        routing_pass_rate = round(
            correct / len(BENCHMARK_SUITE["triage_routing"]) * 100, 1)
        self.state.add_metric("gen_ai.eval.benchmark.pass_rate", routing_pass_rate)

        results["overall"] = {
            "routing_pass_rate": routing_pass_rate,
            "total_tests": len(BENCHMARK_SUITE["triage_routing"]),
            "passed": correct,
            "failed": len(BENCHMARK_SUITE["triage_routing"]) - correct,
            "timestamp": time.time()
        }

        return results

    def get_summary(self) -> dict:
        """Return evaluation summary."""
        if not self.eval_history:
            return {"status": "no_evaluations", "total_evaluations": 0}

        recent = self.eval_history[-20:]

        def avg(key):
            vals = [e["scores"].get(key, 0) for e in recent if key in e["scores"]]
            return round(sum(vals) / len(vals), 2) if vals else 0

        return {
            "total_evaluations": len(self.eval_history),
            "avg_task_accuracy": avg("task_accuracy"),
            "avg_routing_accuracy": avg("routing_accuracy"),
            "avg_tool_selection_accuracy": avg("tool_selection_accuracy"),
            "avg_relevance": avg("relevance"),
            "avg_completeness": avg("completeness"),
            "avg_safety": avg("safety"),
            "avg_hallucination_rate": avg("hallucination_rate"),
            "avg_user_satisfaction": avg("user_satisfaction"),
            "avg_first_contact_resolution": avg("first_contact_resolution"),
            "avg_human_escalation_rate": avg("human_escalation_rate"),
            "avg_latency_slo_compliance": avg("latency_slo_compliance"),
            "baselines": self.baseline_scores,
            "regressions_detected": sum(
                1 for e in self.eval_history
                if e["scores"].get("agent_score", 5) < 3.5),
            "recent_history": [
                {"agent": e["agent"], "score": e["scores"].get("agent_score", 0),
                 "accuracy": e["scores"].get("task_accuracy", 0),
                 "timestamp": e["timestamp"]}
                for e in self.eval_history[-10:]
            ]
        }

    def reset(self):
        """Reset all evaluation state."""
        self.eval_history.clear()
        self.baseline_scores.clear()
