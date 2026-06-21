"""
Experiment Designer — Claude call with structured tool output.

Converts top hypotheses into minimum-viable A/B tests with ICE scoring.
Follows experimentation best practices: one primary metric, stated sample size,
minimum runtime for novelty effect, explicit risk classification.
"""

from anthropic import Anthropic
from core.models import FunnelMetrics, Hypothesis, ABTest

client = Anthropic()

SYSTEM_PROMPT = """You are a senior experimentation PM who has designed 200+ A/B tests at growth-stage SaaS and B2C companies.

You use ICE scoring to prioritise experiments:
- Impact (1-10): Expected effect on primary metric if variant wins. 10 = >20% relative lift. 1 = <1% lift.
- Confidence (1-10): Strength of the evidence base. 10 = multiple studies confirm. 1 = pure intuition.
- Ease (1-10): Implementation effort. 10 = 1-hour CSS/copy change. 1 = new backend service.

Experiment design rules you never break:
1. ONE primary metric per test. If you measure everything, you decide nothing.
2. Always state minimum sample size (use 95% confidence, 80% power, 5% MDE as default).
3. Minimum 14-day runtime to neutralise novelty effect, even if significance is reached sooner.
4. Name the implementation risk: LOW (CSS or copy only), MEDIUM (new UI component), HIGH (backend change or payment flow).
5. Design the minimum viable test that answers the hypothesis — not the most impressive version.
6. Be realistic on expected lift: copy changes → 5-15%, UX friction reduction → 10-25%, trust signals → 5-10%, pricing changes → 3-8%.

ice_score is computed automatically — do NOT include it in your output."""

RECORD_TESTS_TOOL = {
    "name": "record_ab_tests",
    "description": "Record A/B test designs with ICE scores",
    "input_schema": {
        "type": "object",
        "properties": {
            "tests": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "hypothesis_ref":         {"type": "string", "description": "One sentence summarising the hypothesis this test validates"},
                        "test_name":              {"type": "string", "description": "Short descriptive name for the test"},
                        "stage_name":             {"type": "string"},
                        "control_description":    {"type": "string", "description": "Current state — what users see today"},
                        "variant_description":    {"type": "string", "description": "Proposed change — what the variant shows"},
                        "primary_metric":         {"type": "string", "description": "Single metric that determines the winner"},
                        "secondary_metrics":      {"type": "array", "items": {"type": "string"}, "description": "Up to 3 guardrail or supporting metrics"},
                        "minimum_sample_size":    {"type": "integer", "description": "Min users per variant needed for statistical validity"},
                        "expected_duration_days": {"type": "integer", "description": "Minimum days to run (never below 14)"},
                        "expected_lift_pct":      {"type": "number", "description": "Expected relative % improvement in primary metric"},
                        "ice_impact":             {"type": "integer", "minimum": 1, "maximum": 10},
                        "ice_confidence":         {"type": "integer", "minimum": 1, "maximum": 10},
                        "ice_ease":               {"type": "integer", "minimum": 1, "maximum": 10},
                        "risk_level":             {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH"]},
                        "success_criteria":       {"type": "string", "description": "Precise threshold for declaring a winner"},
                    },
                    "required": [
                        "hypothesis_ref", "test_name", "stage_name",
                        "control_description", "variant_description",
                        "primary_metric", "secondary_metrics",
                        "minimum_sample_size", "expected_duration_days",
                        "expected_lift_pct", "ice_impact", "ice_confidence", "ice_ease",
                        "risk_level", "success_criteria",
                    ],
                },
            }
        },
        "required": ["tests"],
    },
}


def run(hypotheses: list[Hypothesis], metrics: FunnelMetrics) -> list[ABTest]:
    if not hypotheses:
        return []

    hyp_context = "\n\n".join([
        f"{i+1}. [{h.category.value}] Stage: {h.stage_name} (priority {h.priority_rank})\n"
        f"   Hypothesis: {h.hypothesis}\n"
        f"   JTBD: {h.jtbd_frame}\n"
        f"   Friction: {h.friction_type} | Evidence: {h.evidence_base}"
        for i, h in enumerate(hypotheses)
    ])

    user_message = f"""Funnel: {metrics.funnel_name} ({metrics.funnel_type.value})
Top-of-funnel traffic: {metrics.stages[0].users:,} users per period

Design one A/B test per hypothesis. Maximum 6 tests total.
Prioritise tests for stages with the highest absolute drop-off.

Hypotheses to test:
{hyp_context}

Use the record_ab_tests tool. Do NOT include ice_score."""

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        tools=[RECORD_TESTS_TOOL],
        tool_choice={"type": "any"},
        messages=[{"role": "user", "content": user_message}],
    )

    tests = []
    for block in response.content:
        if block.type == "tool_use" and block.name == "record_ab_tests":
            for t in block.input.get("tests", []):
                try:
                    ice_score = round((t["ice_impact"] + t["ice_confidence"] + t["ice_ease"]) / 3, 1)
                    tests.append(ABTest(
                        hypothesis_ref=t["hypothesis_ref"],
                        test_name=t["test_name"],
                        stage_name=t["stage_name"],
                        control_description=t["control_description"],
                        variant_description=t["variant_description"],
                        primary_metric=t["primary_metric"],
                        secondary_metrics=t.get("secondary_metrics", []),
                        minimum_sample_size=t["minimum_sample_size"],
                        expected_duration_days=t["expected_duration_days"],
                        expected_lift_pct=t["expected_lift_pct"],
                        ice_impact=t["ice_impact"],
                        ice_confidence=t["ice_confidence"],
                        ice_ease=t["ice_ease"],
                        ice_score=ice_score,
                        risk_level=t["risk_level"],
                        success_criteria=t["success_criteria"],
                    ))
                except Exception:
                    continue
            break

    return sorted(tests, key=lambda t: t.ice_score, reverse=True)
