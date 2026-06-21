"""
Hypothesis Generator — Claude call with structured tool output.

For each drop-off stage, generates 2-3 falsifiable hypotheses grounded in
JTBD theory, Fogg's Behaviour Model, and industry benchmarks.

Design decision: tool_choice forces structured output every time.
Same pattern as aml-copilot risk_analysis_agent — avoids regex extraction fragility.
"""

from anthropic import Anthropic
from core.models import FunnelMetrics, Hypothesis, HypothesisCategory

client = Anthropic()

SYSTEM_PROMPT = """You are a senior growth PM with 8 years of SaaS and B2C funnel experience.

You diagnose conversion drop-offs using:
- Jobs-to-be-Done (JTBD): what is the user trying to accomplish at this exact stage?
- Fogg Behaviour Model: does the user have Motivation, Ability, and Prompt to proceed?
- Friction types: COGNITIVE (too much to think), EMOTIONAL (anxiety/fear/distrust), PHYSICAL (too many clicks/fields), TEMPORAL (wrong timing or too slow)
- Benchmarks: Baymard checkout research, Appcues onboarding data, Nielsen UX heuristics, Reforge trial-to-paid benchmarks

Each hypothesis must be:
1. Falsifiable: "If we [change X], then [metric Y] will [direction] because [mechanism]"
2. Categorised: UX / Copy / Technical / Pricing / Trust / Friction
3. Evidence-grounded: cite a benchmark, heuristic, or research finding
4. JTBD-anchored: state what job the user is trying to do at this stage

Generate exactly 2-3 hypotheses per drop-off stage. Sort stages by absolute drop-off impact (highest first).
Within a stage, rank hypotheses 1=highest expected impact."""

RECORD_HYPOTHESES_TOOL = {
    "name": "record_hypotheses",
    "description": "Record all funnel drop-off hypotheses in structured format",
    "input_schema": {
        "type": "object",
        "properties": {
            "hypotheses": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "stage_name":    {"type": "string", "description": "Exact stage name from the funnel data"},
                        "category":      {"type": "string", "enum": ["UX", "Copy", "Technical", "Pricing", "Trust", "Friction"]},
                        "hypothesis":    {"type": "string", "description": "Falsifiable hypothesis: If we X, then Y will Z because W"},
                        "jtbd_frame":    {"type": "string", "description": "The job the user is trying to do at this stage"},
                        "friction_type": {"type": "string", "description": "COGNITIVE / EMOTIONAL / PHYSICAL / TEMPORAL"},
                        "evidence_base": {"type": "string", "description": "Benchmark or heuristic supporting this hypothesis"},
                        "priority_rank": {"type": "integer", "description": "1 = highest impact within this stage"},
                    },
                    "required": ["stage_name", "category", "hypothesis", "jtbd_frame", "friction_type", "evidence_base", "priority_rank"],
                },
            }
        },
        "required": ["hypotheses"],
    },
}


def run(metrics: FunnelMetrics) -> list[Hypothesis]:
    drop_stages = [s for s in metrics.stages[:-1] if s.drop_off_count > 0]
    drop_stages.sort(key=lambda s: s.drop_off_count, reverse=True)

    stage_context = "\n".join([
        f"- '{s.stage_name}' | Users entering: {s.users:,} | Lost: {s.drop_off_count:,} ({s.drop_off_rate:.1%})"
        f"{' | ⚠️ BIGGEST DROP — prioritise this stage' if s.is_biggest_drop else ''}"
        for s in drop_stages
    ])

    user_message = f"""Funnel: {metrics.funnel_name} ({metrics.funnel_type.value})
Overall conversion: {metrics.overall_conversion:.1%} | Total users lost: {metrics.total_users_lost:,}
Biggest single drop: '{metrics.biggest_drop_stage}' ({metrics.biggest_drop_pct:.1%} drop-off)

Drop-off stages (highest absolute impact first):
{stage_context}

Generate 2-3 hypotheses per stage. Use the record_hypotheses tool."""

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        tools=[RECORD_HYPOTHESES_TOOL],
        tool_choice={"type": "any"},
        messages=[{"role": "user", "content": user_message}],
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "record_hypotheses":
            hypotheses = []
            for h in block.input.get("hypotheses", []):
                try:
                    hypotheses.append(Hypothesis(
                        stage_name=h["stage_name"],
                        category=HypothesisCategory(h["category"]),
                        hypothesis=h["hypothesis"],
                        jtbd_frame=h["jtbd_frame"],
                        friction_type=h["friction_type"],
                        evidence_base=h["evidence_base"],
                        priority_rank=h["priority_rank"],
                    ))
                except Exception:
                    continue
            return hypotheses

    return []
