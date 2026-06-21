"""
Funnel Analyser — pure Python, no LLM.

Calculates per-stage conversion rates, drop-off rates, and identifies the
biggest drop. Runs in <5ms. All downstream agents consume FunnelMetrics.
"""

from core.models import FunnelStage, FunnelMetrics, FunnelType


def run(
    funnel_name: str,
    funnel_type: FunnelType,
    raw_stages: list[tuple[str, int]],
) -> FunnelMetrics:
    if len(raw_stages) < 2:
        raise ValueError("Funnel must have at least 2 stages.")

    stages: list[FunnelStage] = []

    for i, (stage_name, users) in enumerate(raw_stages):
        if i < len(raw_stages) - 1:
            next_users = raw_stages[i + 1][1]
            drop_off_count = users - next_users
            conversion_rate = next_users / users if users > 0 else 0.0
            drop_off_rate = drop_off_count / users if users > 0 else 0.0
        else:
            drop_off_count = 0
            conversion_rate = 0.0
            drop_off_rate = 0.0

        stages.append(FunnelStage(
            stage_name=stage_name,
            users=users,
            conversion_rate=round(conversion_rate, 4),
            drop_off_rate=round(drop_off_rate, 4),
            drop_off_count=drop_off_count,
            is_biggest_drop=False,
        ))

    # Biggest drop by absolute count (exclude last stage)
    drop_candidates = [s for s in stages[:-1] if s.drop_off_count > 0]
    if drop_candidates:
        biggest = max(drop_candidates, key=lambda s: s.drop_off_count)
        biggest.is_biggest_drop = True

    top_users = raw_stages[0][1]
    bottom_users = raw_stages[-1][1]
    overall_conversion = bottom_users / top_users if top_users > 0 else 0.0
    total_lost = top_users - bottom_users
    biggest_stage = next((s for s in stages if s.is_biggest_drop), stages[0])

    return FunnelMetrics(
        funnel_type=funnel_type,
        funnel_name=funnel_name,
        stages=stages,
        overall_conversion=round(overall_conversion, 4),
        biggest_drop_stage=biggest_stage.stage_name,
        biggest_drop_pct=biggest_stage.drop_off_rate,
        total_users_lost=total_lost,
    )
