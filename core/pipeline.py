"""
Funnel analysis pipeline — three agents in sequence.

Flow:
  raw_stages → funnel_analyser  (pure Python, <5ms)
             → hypothesis_generator (Claude, ~5s)
             → experiment_designer  (Claude, ~5s)
             → executive summary    (Claude, ~3s)
             → FunnelReport

Design decisions:
- progress_callback decouples Streamlit progress bar from pipeline logic
- Each agent has a typed input/output — independently testable, replaceable
- Executive summary is a thin fourth Claude call so the summary has full context
"""

import json
import re
import os
from datetime import datetime, timezone
from anthropic import Anthropic
from agents import funnel_analyser, hypothesis_generator, experiment_designer
from core.models import FunnelType, FunnelMetrics, FunnelReport

MODEL = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5-20251001")


def run_pipeline(
    funnel_name: str,
    funnel_type: FunnelType,
    raw_stages: list[tuple[str, int]],
    progress_callback=None,
) -> FunnelReport:
    """
    progress_callback signature: (step: int, total: int, label: str) -> None
    Allows the Streamlit UI to update a progress bar without the pipeline
    knowing anything about Streamlit.
    """
    def notify(step, total, label):
        if progress_callback:
            progress_callback(step, total, label)

    notify(1, 4, "Calculating funnel metrics...")
    metrics = funnel_analyser.run(funnel_name, funnel_type, raw_stages)

    notify(2, 4, "Generating drop-off hypotheses (Claude)...")
    hypotheses = hypothesis_generator.run(metrics)

    notify(3, 4, "Designing A/B experiments (Claude)...")
    ab_tests = experiment_designer.run(hypotheses, metrics)

    notify(4, 4, "Writing executive summary (Claude)...")
    summary, top_rec = _generate_summary(metrics, hypotheses, ab_tests)

    return FunnelReport(
        funnel_metrics=metrics,
        hypotheses=hypotheses,
        ab_tests=ab_tests,
        executive_summary=summary,
        top_recommendation=top_rec,
        generated_at=datetime.now(timezone.utc),
    )


def _generate_summary(metrics, hypotheses, ab_tests) -> tuple[str, str]:
    client = Anthropic()
    top_test = ab_tests[0] if ab_tests else None
    top_categories = list(dict.fromkeys(h.category.value for h in hypotheses[:3]))

    prompt = f"""Write a 3-sentence executive summary of this funnel analysis for a VP of Product.
Be specific — reference the actual numbers. End with the single most impactful action.

Funnel: {metrics.funnel_name}
Overall conversion: {metrics.overall_conversion:.1%} ({metrics.total_users_lost:,} users lost)
Biggest drop: {metrics.biggest_drop_stage} — {metrics.biggest_drop_pct:.1%} drop-off rate
Top hypothesis categories: {', '.join(top_categories)}
Top A/B test: {top_test.test_name if top_test else 'None'} \
(ICE: {top_test.ice_score if top_test else 'N/A'}, expected lift: +{top_test.expected_lift_pct:.0f}% on {top_test.primary_metric if top_test else ''})

Return JSON with two keys:
- "summary": 3-sentence executive summary
- "top_recommendation": one sentence — the single action to take first"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group())
            return (
                data.get("summary", text[:400]),
                data.get("top_recommendation", top_test.test_name if top_test else "Review biggest drop-off stage"),
            )
        except Exception:
            pass

    fallback_rec = top_test.test_name if top_test else "Review biggest drop-off stage"
    return text[:400], fallback_rec
