"""
Three sample funnels with real-world conversion benchmarks.

Sources:
  B2B SaaS:   OpenView SaaS Benchmarks 2024, Reforge trial-to-paid data
  E-Commerce: Baymard Institute checkout usability study 2024 (avg 70.19% cart abandonment)
  Mobile:     Appcues Mobile Onboarding Benchmark 2023, Mixpanel Product Benchmarks 2023
"""

from core.models import FunnelType

SAMPLE_FUNNELS: dict[FunnelType, dict] = {

    FunnelType.B2B_SAAS_TRIAL: {
        "funnel_name": "B2B SaaS — Free Trial to Paid",
        "description": (
            "14-day free trial funnel for a mid-market project management SaaS (~$49/mo). "
            "Industry median trial-to-paid is 15–25% for PLG products. "
            "This funnel sits at 1.76% overall — the onboarding wizard is killing activation."
        ),
        "raw_stages": [
            ["Landing page visit",          10_000],
            ["Trial signup started",         2_800],
            ["Email verified",               2_100],
            ["Onboarding wizard completed",  1_050],
            ["First project created",          840],
            ["Team member invited",            504],
            ["Trial → Paid converted",         176],
        ],
    },

    FunnelType.ECOMMERCE: {
        "funnel_name": "E-Commerce — Fashion Checkout",
        "description": (
            "Guest and account checkout funnel for a mid-size fashion retailer. "
            "Baymard 2024 average cart abandonment is 70.19%. "
            "This funnel is at 73.8% — slightly above average, with shipping info as the key friction."
        ),
        "raw_stages": [
            ["Product page view",    50_000],
            ["Add to cart",          15_000],
            ["Cart page view",       12_750],
            ["Checkout initiated",    7_650],
            ["Shipping info entered", 5_355],
            ["Payment entered",       3_749],
            ["Order confirmed",       3_112],
        ],
    },

    FunnelType.MOBILE_ONBOARDING: {
        "funnel_name": "Mobile App — Fitness App Onboarding",
        "description": (
            "iOS/Android onboarding funnel for a freemium fitness app. "
            "Mixpanel 2023: median D1 retention is 25%. "
            "This funnel converts only 18% to activated — notification permission is the wall."
        ),
        "raw_stages": [
            ["App install",                   100_000],
            ["App opened (Day 0)",              82_000],
            ["Onboarding screen 1 completed",   57_400],
            ["Goal and profile set",            34_440],
            ["Notification permission granted", 20_664],
            ["First workout completed",         10_332],
            ["Day 1 return (retained)",         18_000],
        ],
    },
}
