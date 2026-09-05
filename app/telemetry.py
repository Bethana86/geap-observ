"""OpenTelemetry metric instruments for GEAP observability."""
import time
import random


class MetricInstruments:
    """Holds references to all 57 GEAP metric instruments.
    In simulation mode, records to the ObservabilityState directly.
    In production, would use real OTel SDK meters."""

    def __init__(self, state):
        self.state = state

    def record_agent_call(self, agent_name: str, duration_ms: float, input_tokens: int, output_tokens: int, model: str):
        """Record metrics for a single agent invocation."""
        s = self.state
        s.add_metric("gen_ai.agent.calls.count", 1)
        s.add_metric("gen_ai.agent.calls.count", 1, {"gen_ai.agent.name": agent_name})

        # Latency
        ttft = random.randint(80, 300)
        ttfa = random.randint(200, 700)
        s.add_metric("gen_ai.latency.ttft", ttft)
        s.add_metric("gen_ai.latency.ttfa", ttfa)

        # Tokens
        cached = random.randint(100, min(400, input_tokens))
        thinking = random.randint(100, 800)
        s.add_metric("gen_ai.tokens.input", input_tokens)
        s.add_metric("gen_ai.tokens.cached", cached)
        s.add_metric("gen_ai.tokens.output", output_tokens)
        s.add_metric("gen_ai.tokens.thinking", thinking)

        # Cost calculation
        if "pro" in model:
            cost = (input_tokens * 1.25 + output_tokens * 10.0) / 1_000_000
        else:
            cost = (input_tokens * 0.15 + output_tokens * 0.60) / 1_000_000
        s.add_metric("gen_ai.cost.per_call", round(cost, 6))

        # Routing tier
        if "pro" in model:
            s.add_metric("gen_ai.routing.tier.pro", 1)
        elif "flash" in model:
            s.add_metric("gen_ai.routing.tier.flash", 1)
        else:
            s.add_metric("gen_ai.routing.tier.flash_lite", 1)

        # Update accumulators for SLO
        s.total_input_tokens += input_tokens
        s.total_cached_tokens += cached
        s.total_output_tokens += output_tokens
        s.total_ttft_ms += ttft

        return cost, cached

    def record_handoff(self, from_agent: str, to_agent: str):
        s = self.state
        s.add_metric("gen_ai.agent.handoff.count", 1)
        s.add_metric("gen_ai.a2a.messages.count", random.randint(1, 3))
        s.add_metric("gen_ai.a2a.trace_context.propagated", 1)

    def record_tool_call(self, tool_name: str, duration_ms: float, success: bool = True):
        s = self.state
        s.add_metric("gen_ai.tool.calls.count", 1)
        s.add_metric("gen_ai.tool.calls.count", 1, {"gen_ai.tool.name": tool_name})
        s.add_metric("gen_ai.tool.execution.duration", duration_ms)
        if not success:
            s.add_metric("gen_ai.tool.errors.count", 1)
        else:
            s.add_metric("gen_ai.tool.errors.count", 0)
        s.add_metric("gen_ai.tool.cache.hit", random.randint(0, 1))

    def record_workflow_complete(self, duration_ms: float, total_cost: float, success: bool = True):
        s = self.state
        s.total_runs += 1
        if success:
            s.successful_runs += 1
        else:
            s.failed_runs += 1
        s.total_cost += total_cost
        s.total_ttlt_ms += duration_ms

        # Workflow metrics
        s.add_metric("gen_ai.workflow.duration", duration_ms)
        s.add_metric("gen_ai.workflow.success.count", 1 if success else 0)
        s.add_metric("gen_ai.workflow.errors.count", 0 if success else 1)
        s.add_metric("gen_ai.workflow.active_agents", random.randint(1, 3))
        s.add_metric("gen_ai.workflow.queue.delay", random.randint(3, 30))
        s.add_metric("gen_ai.latency.ttlt", duration_ms)

        # Scale metrics
        s.add_metric("gen_ai.scale.circuit_breaker.open", 0)
        s.add_metric("gen_ai.scale.fallback.depth", random.choice([0, 0, 1]))
        s.add_metric("gen_ai.scale.retry.count", random.randint(0, 1))
        s.add_metric("gen_ai.scale.retry_storm.indicator", round(random.uniform(1.0, 1.5), 2))
        if success:
            s.add_metric("gen_ai.scale.exit_reason.completed", 1)
        s.add_metric("gen_ai.scale.exit_reason.token_budget", 0)
        s.add_metric("gen_ai.scale.exit_reason.max_turns", 0)
        s.add_metric("gen_ai.scale.exit_reason.stuck_loop", 0)

        # System
        s.add_metric("gen_ai.system.cpu.utilization", round(random.uniform(15.0, 50.0), 1))
        s.add_metric("gen_ai.system.memory.utilization", round(random.uniform(30.0, 65.0), 1))
        s.add_metric("gen_ai.system.active.connections", random.randint(2, 20))

        # MCP
        s.add_metric("gen_ai.mcp.skill.invocations", random.randint(0, 2))

        # Govern - Identity
        s.add_metric("gen_ai.identity.attributed.count", 2)
        s.add_metric("gen_ai.identity.act_claim.delegations", random.choice([1, 1, 2]))
        s.add_metric("gen_ai.identity.unauthorized.blocked", 0)
        s.add_metric("gen_ai.security.cloud_armor.blocked", 0)
        s.add_metric("gen_ai.security.cloud_armor.violations", 0)
        s.add_metric("gen_ai.security.dlp.redactions", random.randint(0, 3))

        # Cost
        cache_ratio = round(s.total_cached_tokens / max(1, s.total_input_tokens + s.total_cached_tokens) * 100, 1)
        s.add_metric("gen_ai.cost.prefix_cache.hit_ratio", cache_ratio)
        s.add_metric("gen_ai.cost.per_resolved_task", total_cost if success else total_cost * 2)

        # Quality
        q_score = round(random.uniform(4.1, 4.9), 1) if success else round(random.uniform(1.8, 2.5), 1)
        s.quality_scores.append(q_score)
        s.add_metric("gen_ai.quality.autorater.score", q_score)
        s.add_metric("gen_ai.quality.autorater.agreement_kappa", round(random.uniform(0.62, 0.90), 2))
        s.add_metric("gen_ai.quality.groundedness", round(random.uniform(82.0, 97.0), 1))

        # Context
        s.add_metric("gen_ai.context.reasoning_drift", round(random.uniform(0.05, 0.25), 2))
        s.add_metric("gen_ai.context.rot.indicator", round(random.uniform(0.08, 0.28), 2))
        s.add_metric("gen_ai.context.window.utilization", round(random.uniform(15.0, 50.0), 1))
        s.add_metric("gen_ai.context.compaction.events", random.randint(0, 1))

    def record_threat(self, threat_kind: str):
        s = self.state
        s.threat_incidents += 1
        threat_map = {
            "prompt_injection": "gen_ai.security.model_armor.prompt_injection",
            "jailbreak": "gen_ai.security.model_armor.jailbreak",
            "pii_leak": "gen_ai.security.pii_leak.blocked",
            "confused_deputy": "gen_ai.security.confused_deputy.detected"
        }
        if threat_kind in threat_map:
            s.add_metric(threat_map[threat_kind], 1)
