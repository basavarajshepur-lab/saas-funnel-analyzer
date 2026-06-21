# SaaS Funnel Drop-off Analyzer

**Multi-agent tool for growth PMs — identify where users drop, why it happens, and what to test first.**

![Python](https://img.shields.io/badge/Python-3.11+-blue) ![License](https://img.shields.io/badge/License-MIT-green) ![Status](https://img.shields.io/badge/Status-Production--Ready%20Demo-brightgreen) ![Claude](https://img.shields.io/badge/Powered%20by-Claude%20AI-orange)

---

## The Problem

Every growth PM inherits a funnel with a problem they can't fully explain.

You know where users drop. Google Analytics or Mixpanel will tell you that. What they won't tell you is *why* — and what to test first to fix it.

The standard approach is a Notion doc of hypotheses, a backlog of A/B tests with no clear priority, and a quarterly experiment review that never quite closes the loop.

**This tool turns raw funnel data into a prioritised A/B test backlog in under 60 seconds.**

---

## What It Does

A three-agent pipeline that takes funnel stage data and produces:

```
Funnel Data (stage names + user counts)
        │
        ▼
┌─────────────────────┐
│  Agent 1            │
│  Funnel Analyser    │  Pure Python — calculates conversion rates,
│  (pure Python)      │  drop-off rates, identifies biggest drop stage
└─────────┬───────────┘
          │  FunnelMetrics
          ▼
┌─────────────────────┐
│  Agent 2            │  2-3 hypotheses per drop-off stage
│  Hypothesis         │  Categorised: UX / Copy / Technical /
│  Generator (Claude) │  Pricing / Trust / Friction
└─────────┬───────────┘  Grounded in JTBD, Fogg BM, benchmarks
          │  list[Hypothesis]
          ▼
┌─────────────────────┐
│  Agent 3            │  One A/B test per hypothesis
│  Experiment         │  ICE scored (Impact / Confidence / Ease)
│  Designer (Claude)  │  Min sample size, duration, primary metric
└─────────┬───────────┘
          │  list[ABTest]
          ▼
    FunnelReport
    ├── Executive summary (3 sentences for a VP)
    ├── Top recommendation
    ├── Full JSON export
    └── A/B test backlog CSV
```

---

## Features

- **Funnel visualisation** — Plotly funnel chart, biggest drop highlighted in red
- **Hypothesis generation** — JTBD-anchored, friction-typed, benchmark-grounded
- **Experiment design** — ICE scoring, min sample size, 14-day runtime minimum, risk classification
- **4-tab Streamlit UI** — Funnel | Hypotheses | A/B Tests | Report
- **CSV upload** — bring your own funnel data (Stage, Users columns)
- **Export** — full JSON report + A/B test backlog as CSV
- **Three sample funnels** — B2B SaaS trial, e-commerce checkout, mobile onboarding

---

## Sample Funnels (with real-world benchmarks)

| Funnel | Key finding | Benchmark |
|--------|-------------|-----------|
| **B2B SaaS Trial** | Onboarding wizard completion at 50% — biggest drop | Reforge: PLG trial-to-paid median 15–25% |
| **E-Commerce Checkout** | Shipping info step loses 30% — cart abandonment 73.8% | Baymard 2024: avg 70.19% |
| **Mobile Onboarding** | Notification permission loses 40% — D1 retention 18% | Mixpanel 2023: median D1 25% |

---

## Quick Start

```bash
git clone https://github.com/basavarajshepur-lab/saas-funnel-analyzer
cd saas-funnel-analyzer
pip install -r requirements.txt
cp .env.example .env
# Add your ANTHROPIC_API_KEY to .env
python -m streamlit run app.py
```

---

## Bring Your Own Funnel

Upload a CSV with two columns:

```csv
Stage,Users
Landing page,10000
Signup started,2800
Email verified,2100
Onboarding complete,1050
Activated,280
```

---

## Architecture

```
saas-funnel-analyzer/
├── app.py                          # Streamlit UI — 4 tabs
├── core/
│   ├── models.py                   # Pydantic v2 data contracts
│   └── pipeline.py                 # Orchestration with progress callbacks
├── agents/
│   ├── funnel_analyser.py          # Pure Python — no LLM, <5ms
│   ├── hypothesis_generator.py     # Claude — tool-forced structured output
│   └── experiment_designer.py      # Claude — ICE-scored A/B test designs
└── data/
    └── sample_funnels.py           # 3 real-world funnel datasets
```

**Design decisions:**
- `funnel_analyser` is pure Python — the math doesn't need an LLM, and keeping it fast means the funnel chart renders immediately before any Claude calls
- Both Claude agents use `tool_choice: any` to force structured output — no regex extraction, no parse failures
- ICE score is computed by the Pydantic model, not by Claude — removes a source of arithmetic error
- `progress_callback` parameter decouples the pipeline from Streamlit, making it testable without a UI

---

## Skills Demonstrated

| Skill | Where |
|-------|-------|
| Funnel analysis | `funnel_analyser.py` — conversion rates, drop-off rates, biggest opportunity identification |
| JTBD framework | `hypothesis_generator.py` — every hypothesis anchored to a user job |
| Experimentation | `experiment_designer.py` — ICE scoring, sample sizing, primary metric discipline |
| Growth PM thinking | Hypothesis categories (UX/Copy/Technical/Pricing/Trust/Friction), Fogg BM, Baymard benchmarks |
| Multi-agent design | Three-agent sequential pipeline with typed contracts at every stage |
| Responsible AI | Structured output via tool use — deterministic, auditable, no hallucinated JSON |

---

## About

Built by [Basavaraj Shepur](https://linkedin.com/in/basavarajshepur) — Senior AI Product Manager with 19 years in financial services, specialising in AI product strategy, growth, and multi-agent systems.
