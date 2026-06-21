"""
Pydantic v2 data contracts for the SaaS Funnel Drop-off Analyzer.
Every agent input and output is typed here. Nothing outside this file defines data shapes.
"""

from __future__ import annotations
from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field


class FunnelType(str, Enum):
    B2B_SAAS_TRIAL    = "B2B SaaS Trial Signup"
    ECOMMERCE         = "E-Commerce Checkout"
    MOBILE_ONBOARDING = "Mobile App Onboarding"
    CUSTOM            = "Custom Upload"


class HypothesisCategory(str, Enum):
    UX        = "UX"
    COPY      = "Copy"
    TECHNICAL = "Technical"
    PRICING   = "Pricing"
    TRUST     = "Trust"
    FRICTION  = "Friction"


class FunnelStage(BaseModel):
    stage_name:      str
    users:           int
    conversion_rate: float  # % who proceed to next stage
    drop_off_rate:   float  # % who leave at this stage
    drop_off_count:  int
    is_biggest_drop: bool = False


class FunnelMetrics(BaseModel):
    funnel_type:        FunnelType
    funnel_name:        str
    stages:             list[FunnelStage]
    overall_conversion: float
    biggest_drop_stage: str
    biggest_drop_pct:   float
    total_users_lost:   int


class Hypothesis(BaseModel):
    stage_name:    str
    category:      HypothesisCategory
    hypothesis:    str
    jtbd_frame:    str
    friction_type: str
    evidence_base: str
    priority_rank: int


class ABTest(BaseModel):
    hypothesis_ref:         str
    test_name:              str
    stage_name:             str
    control_description:    str
    variant_description:    str
    primary_metric:         str
    secondary_metrics:      list[str] = Field(default_factory=list)
    minimum_sample_size:    int
    expected_duration_days: int
    expected_lift_pct:      float
    ice_impact:             int
    ice_confidence:         int
    ice_ease:               int
    ice_score:              float = 0.0
    risk_level:             str
    success_criteria:       str


class FunnelReport(BaseModel):
    funnel_metrics:     FunnelMetrics
    hypotheses:         list[Hypothesis]
    ab_tests:           list[ABTest]
    executive_summary:  str
    top_recommendation: str
    generated_at:       datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
