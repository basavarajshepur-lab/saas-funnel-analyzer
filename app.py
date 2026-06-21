"""
SaaS Funnel Drop-off Analyzer
Multi-agent tool for growth PMs: identify where users drop, why, and what to test.

Run: python -m streamlit run app.py
"""

from dotenv import load_dotenv
load_dotenv()

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from agents import funnel_analyser
from core.models import FunnelType, FunnelReport
from core.pipeline import run_pipeline
from data.sample_funnels import SAMPLE_FUNNELS

st.set_page_config(
    page_title="Funnel Drop-off Analyzer",
    page_icon="📉",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Session state ──────────────────────────────────────────────────────────────

if "report" not in st.session_state:
    st.session_state.report = None
if "preview_metrics" not in st.session_state:
    st.session_state.preview_metrics = None

# ── Helpers ────────────────────────────────────────────────────────────────────

def build_funnel_chart(metrics):
    colors = ["#ef4444" if s.is_biggest_drop else "#3b82f6" for s in metrics.stages]
    fig = go.Figure(go.Funnel(
        y=[s.stage_name for s in metrics.stages],
        x=[s.users for s in metrics.stages],
        textposition="inside",
        textinfo="value+percent initial",
        marker=dict(color=colors),
        connector=dict(line=dict(color="#cbd5e1", width=1)),
    ))
    fig.update_layout(
        height=460,
        margin=dict(t=10, l=0, r=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def stages_to_df(metrics) -> pd.DataFrame:
    rows = []
    for i, s in enumerate(metrics.stages):
        rows.append({
            "Stage": s.stage_name,
            "Users": f"{s.users:,}",
            "Lost": f"{s.drop_off_count:,}" if s.drop_off_count > 0 else "—",
            "Drop-off %": f"{s.drop_off_rate:.1%}" if s.drop_off_rate > 0 else "—",
            "→ Next stage": f"{s.conversion_rate:.1%}" if i < len(metrics.stages) - 1 else "—",
            "Flag": "🔴 Biggest drop" if s.is_biggest_drop else "",
        })
    return pd.DataFrame(rows)


CATEGORY_COLORS = {
    "UX": "blue",
    "Copy": "green",
    "Technical": "red",
    "Pricing": "orange",
    "Trust": "violet",
    "Friction": "gray",
}

# ── Header ─────────────────────────────────────────────────────────────────────

st.title("📉 SaaS Funnel Drop-off Analyzer")
st.caption(
    "Multi-agent tool for growth PMs — identify where users drop, why it happens, and what to test first."
)
st.divider()

# ── Tabs ───────────────────────────────────────────────────────────────────────

tab_funnel, tab_hypotheses, tab_tests, tab_report = st.tabs([
    "📊 Funnel", "💡 Hypotheses", "🧪 A/B Tests", "📋 Report"
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — FUNNEL
# ══════════════════════════════════════════════════════════════════════════════

with tab_funnel:
    raw_stages = None
    funnel_name = None
    funnel_type = None

    col_left, col_right = st.columns([1, 2])

    with col_left:
        st.subheader("Select Funnel")

        input_method = st.radio(
            "Input",
            ["Sample funnel", "Upload CSV"],
            horizontal=True,
            label_visibility="collapsed",
        )

        if input_method == "Sample funnel":
            funnel_options = {t.value: t for t in FunnelType if t != FunnelType.CUSTOM}
            selected = st.selectbox("Choose sample", options=list(funnel_options.keys()))
            funnel_type = funnel_options[selected]
            sample = SAMPLE_FUNNELS[funnel_type]
            funnel_name = sample["funnel_name"]
            raw_stages = [(s[0], s[1]) for s in sample["raw_stages"]]
            st.caption(sample["description"])

        else:
            st.caption("CSV needs two columns: **Stage** and **Users**")
            uploaded = st.file_uploader(
                "Upload CSV", type=["csv"], label_visibility="collapsed"
            )
            if uploaded:
                try:
                    df_upload = pd.read_csv(uploaded)
                    if "Stage" not in df_upload.columns or "Users" not in df_upload.columns:
                        st.error("CSV must have 'Stage' and 'Users' columns.")
                    else:
                        df_upload["Users"] = (
                            pd.to_numeric(df_upload["Users"], errors="coerce")
                            .fillna(0)
                            .astype(int)
                        )
                        raw_stages = list(zip(df_upload["Stage"].tolist(), df_upload["Users"].tolist()))
                        funnel_name = uploaded.name.replace(".csv", "").replace("_", " ").title()
                        funnel_type = FunnelType.CUSTOM
                        st.dataframe(df_upload, use_container_width=True, hide_index=True)
                except Exception as e:
                    st.error(f"Error reading CSV: {e}")

        st.divider()

        run_btn = st.button(
            "🚀 Run Full Analysis",
            type="primary",
            use_container_width=True,
            disabled=raw_stages is None,
        )

        if st.session_state.report:
            r = st.session_state.report
            st.success(
                f"✅ {len(r.hypotheses)} hypotheses · {len(r.ab_tests)} A/B tests\n\n"
                f"Switch to the other tabs to see results."
            )

    with col_right:
        # Preview funnel chart immediately (no Claude call needed)
        if raw_stages:
            preview = funnel_analyser.run(
                funnel_name or "Funnel",
                funnel_type or FunnelType.CUSTOM,
                raw_stages,
            )
            st.session_state.preview_metrics = preview

        if st.session_state.preview_metrics:
            m = st.session_state.preview_metrics
            st.plotly_chart(build_funnel_chart(m), use_container_width=True)

            k1, k2, k3 = st.columns(3)
            k1.metric("Overall Conversion", f"{m.overall_conversion:.1%}")
            k2.metric("Total Users Lost", f"{m.total_users_lost:,}")
            k3.metric("Biggest Drop Stage", m.biggest_drop_stage)

            st.dataframe(stages_to_df(m), use_container_width=True, hide_index=True)

    # Run pipeline
    if run_btn and raw_stages:
        progress_bar = st.progress(0)
        status = st.empty()

        def on_progress(step, total, label):
            progress_bar.progress(step / total)
            status.info(f"Step {step}/{total}: {label}")

        try:
            report = run_pipeline(
                funnel_name=funnel_name or "Custom Funnel",
                funnel_type=funnel_type or FunnelType.CUSTOM,
                raw_stages=raw_stages,
                progress_callback=on_progress,
            )
            st.session_state.report = report
            progress_bar.empty()
            status.empty()
            st.rerun()
        except Exception as e:
            progress_bar.empty()
            status.empty()
            st.error(f"Analysis failed: {e}")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — HYPOTHESES
# ══════════════════════════════════════════════════════════════════════════════

with tab_hypotheses:
    report: FunnelReport | None = st.session_state.report

    if not report:
        st.info("Run an analysis first — Funnel tab → 🚀 Run Full Analysis.")
    else:
        st.subheader(f"Hypotheses — {report.funnel_metrics.funnel_name}")
        st.caption(
            f"{len(report.hypotheses)} hypotheses across "
            f"{len(set(h.stage_name for h in report.hypotheses))} drop-off stages"
        )

        stage_drop = {s.stage_name: s.drop_off_count for s in report.funnel_metrics.stages}
        stage_is_biggest = {s.stage_name: s.is_biggest_drop for s in report.funnel_metrics.stages}
        stage_obj_map = {s.stage_name: s for s in report.funnel_metrics.stages}

        stage_groups: dict[str, list] = {}
        for h in report.hypotheses:
            stage_groups.setdefault(h.stage_name, []).append(h)

        sorted_stages = sorted(
            stage_groups.keys(),
            key=lambda s: stage_drop.get(s, 0),
            reverse=True,
        )

        for stage_name in sorted_stages:
            hyps = sorted(stage_groups[stage_name], key=lambda h: h.priority_rank)
            s_obj = stage_obj_map.get(stage_name)
            drop_label = (
                f"{s_obj.drop_off_count:,} users lost ({s_obj.drop_off_rate:.1%})"
                if s_obj else ""
            )
            is_biggest = stage_is_biggest.get(stage_name, False)

            with st.expander(
                f"{'🔴 ' if is_biggest else ''}{stage_name} — {drop_label}",
                expanded=is_biggest,
            ):
                for h in hyps:
                    color = CATEGORY_COLORS.get(h.category.value, "gray")
                    st.markdown(f"**:{color}[{h.category.value}]** &nbsp;&nbsp; {h.hypothesis}")
                    c1, c2 = st.columns(2)
                    c1.caption(f"📌 **JTBD:** {h.jtbd_frame}")
                    c2.caption(f"⚡ **Friction:** {h.friction_type}")
                    st.caption(f"📊 **Evidence:** {h.evidence_base}")
                    st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — A/B TESTS
# ══════════════════════════════════════════════════════════════════════════════

with tab_tests:
    report = st.session_state.report

    if not report:
        st.info("Run an analysis first — Funnel tab → 🚀 Run Full Analysis.")
    else:
        st.subheader(f"A/B Test Backlog — {report.funnel_metrics.funnel_name}")
        st.caption(f"{len(report.ab_tests)} tests · sorted by ICE score (highest priority first)")

        if report.ab_tests:
            summary_rows = [
                {
                    "Test": t.test_name,
                    "Stage": t.stage_name,
                    "ICE Score": t.ice_score,
                    "Impact": t.ice_impact,
                    "Confidence": t.ice_confidence,
                    "Ease": t.ice_ease,
                    "Expected Lift": f"+{t.expected_lift_pct:.0f}%",
                    "Risk": t.risk_level,
                    "Min Sample": f"{t.minimum_sample_size:,}",
                    "Duration (days)": t.expected_duration_days,
                }
                for t in report.ab_tests
            ]

            st.dataframe(
                pd.DataFrame(summary_rows),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "ICE Score": st.column_config.ProgressColumn(
                        min_value=0, max_value=10, format="%.1f"
                    ),
                },
            )

            st.divider()
            st.subheader("Test Details")

            for t in report.ab_tests:
                with st.expander(
                    f"**{t.test_name}** — ICE {t.ice_score}/10 · {t.stage_name}"
                ):
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown("**Control (current)**")
                        st.info(t.control_description)
                    with c2:
                        st.markdown("**Variant (proposed)**")
                        st.success(t.variant_description)

                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Primary Metric", t.primary_metric)
                    m2.metric("Min Sample / variant", f"{t.minimum_sample_size:,}")
                    m3.metric("Expected Lift", f"+{t.expected_lift_pct:.0f}%")
                    m4.metric("Risk", t.risk_level)

                    i1, i2, i3 = st.columns(3)
                    i1.metric("Impact", f"{t.ice_impact}/10")
                    i2.metric("Confidence", f"{t.ice_confidence}/10")
                    i3.metric("Ease", f"{t.ice_ease}/10")

                    st.caption(f"**Success criteria:** {t.success_criteria}")
                    if t.secondary_metrics:
                        st.caption(f"**Secondary metrics:** {', '.join(t.secondary_metrics)}")
                    st.caption(f"**Hypothesis:** {t.hypothesis_ref}")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — REPORT
# ══════════════════════════════════════════════════════════════════════════════

with tab_report:
    report = st.session_state.report

    if not report:
        st.info("Run an analysis first — Funnel tab → 🚀 Run Full Analysis.")
    else:
        st.subheader("Executive Summary")
        st.info(report.executive_summary)

        st.subheader("Top Recommendation")
        st.success(f"**Start with:** {report.top_recommendation}")

        st.divider()

        dl1, dl2 = st.columns(2)
        with dl1:
            st.download_button(
                "⬇️ Download Full Report (JSON)",
                data=report.model_dump_json(indent=2),
                file_name=f"funnel_report_{report.funnel_metrics.funnel_name.replace(' ', '_')}.json",
                mime="application/json",
                use_container_width=True,
            )
        with dl2:
            tests_csv = pd.DataFrame([
                {
                    "Test": t.test_name,
                    "Stage": t.stage_name,
                    "ICE Score": t.ice_score,
                    "Expected Lift %": t.expected_lift_pct,
                    "Risk": t.risk_level,
                    "Duration (days)": t.expected_duration_days,
                    "Min Sample": t.minimum_sample_size,
                    "Primary Metric": t.primary_metric,
                    "Control": t.control_description,
                    "Variant": t.variant_description,
                }
                for t in report.ab_tests
            ]).to_csv(index=False)
            st.download_button(
                "⬇️ Download A/B Test Backlog (CSV)",
                data=tests_csv,
                file_name="ab_test_backlog.csv",
                mime="text/csv",
                use_container_width=True,
            )

        st.divider()
        st.subheader("Stage-by-Stage Breakdown")
        st.dataframe(stages_to_df(report.funnel_metrics), use_container_width=True, hide_index=True)
