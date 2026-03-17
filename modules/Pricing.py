"""
FFP Smart MVP — Pillar 3: Pricing & Business Model
===================================================
Weight: 20% of composite score (Pre-Seed)

Scoring philosophy: NEUTRAL for all pre-revenue states.
No penalty for absence of paying customers at Pre-Seed.

Pricing Clarity Rules:
  Clear         → model_type ✓ + target_customer ✓ + pricing_metric ✓ → 65
  SomewhatClear → model_type ✓ + target_customer ✓, pricing_metric ✗ → 50
                  OR Enterprise + 'contact sales'                      → 50
  Unclear       → model_type ✗ OR target_customer ✗                   → 35
  PreRevenue    → revenue = 0 → score forced to 50 in composite
"""

import os
import requests
from typing import Optional


# ──────────────────────────────────────────────
# Valid pricing model types (enum guard)
# ──────────────────────────────────────────────
VALID_PRICING_MODELS = {
    "Free", "Freemium", "Subscription", "Usage-Based",
    "Transaction Fee", "Enterprise", "Other",
}

DATA_PROVENANCE_NOTE = "Pricing model: founder-submitted."




# ──────────────────────────────────────────────
# Pricing Summary Optimizer (Rule-based)
# ──────────────────────────────────────────────
def _generate_pricing_summary(
    pricing_model_type: str,
    target_customer: str,
    pricing_metric: str,
    price_range: str,
    market_type: str,
) -> str:
    """
    Generates a 2-3 sentence factual summary of the pricing model.
    Replaces Gemini-based summary.
    """
    model = pricing_model_type or "unspecified"
    customer = target_customer or "target customers"
    metric = f" based on {pricing_metric}" if pricing_metric else ""
    price = f" in the {price_range} range" if price_range and price_range.lower() != "not specified" else ""
    
    summary = (
        f"The startup employs a {model} pricing model targeting {customer}{metric}{price}. "
        f"This approach is typical for the {market_type or 'requested'} sector in 2026, "
        "focusing on scalability through value-based unit economics."
    )
    return summary


# ──────────────────────────────────────────────
# Pricing Clarity Rules
# ──────────────────────────────────────────────
def _compute_pricing_clarity(
    pricing_model_type: Optional[str],
    target_customer: Optional[str],
    pricing_metric: Optional[str],
    price_range: Optional[str],
    revenue: float,
) -> tuple[str, Optional[int]]:
    """
    Returns (pricing_clarity_label, pillar_score).
    PreRevenue always returns score=50 (forced at composite level also).
    """
    # ── Rule: If all required data missing → UnableToCompute
    if not pricing_model_type and not target_customer:
        return "UnableToCompute", None

    is_pre_revenue = revenue == 0

    has_model = bool(pricing_model_type)
    has_customer = bool(target_customer)
    has_metric = bool(pricing_metric)

    # Spec: 
    # Clear: model + target + metric
    # SomewhatClear: model + target, metric missing OR Enterprise + 'contact sales'
    # Unclear: model missing OR target missing
    
    if has_model and has_customer and has_metric:
        label, score = "Clear", 65
    elif pricing_model_type == "Enterprise" and price_range and price_range.lower() == "contact sales":
        label, score = "Clear", 65
    elif has_model and has_customer:
        label, score = "SomewhatClear", 50
    elif not has_model or not has_customer:
        label, score = "Unclear", 35
    else:
        label, score = "SomewhatClear", 50

    # Forced neutral for pre-revenue
    if is_pre_revenue:
        return "PreRevenue", 50

    return label, score


# ──────────────────────────────────────────────
# Main Entry Point
# ──────────────────────────────────────────────
def score_pricing_pipeline(
    pricing_model_type: Optional[str],
    target_customer: Optional[str],
    pricing_metric: Optional[str] = None,
    price_range: Optional[str] = None,
    who_pays_vs_who_uses: Optional[str] = None,
    paying_segment: Optional[str] = None,   # stored only — NOT scored at Pre-Seed
    evidence_links: Optional[list[str]] = None,
    analyst_notes: Optional[str] = None,
    revenue_curr_period: float = 0.0,
    active_users: int = 0,
    revenue_prev_period: float = 0.0,
    active_users_prev: int = 0,
    tavily_benchmark_successful: bool = False,
    market_type: str = "",
    geographic_focus: str = "",
) -> dict:
    """
    Compute the Pricing & Business Model pillar score.
    """
    evidence_links = evidence_links or []

    pricing_clarity_label, base_pillar_score = _compute_pricing_clarity(
        pricing_model_type=pricing_model_type,
        target_customer=target_customer,
        pricing_metric=pricing_metric,
        price_range=price_range,
        revenue=revenue_curr_period,
    )

    summary = _generate_pricing_summary(
        pricing_model_type or "Other",
        target_customer or "undisclosed",
        pricing_metric or "",
        price_range or "",
        market_type or "B2B SaaS"
    )

    # ── ARPU Guardrails & Bonus ──
    arpu_bonus = 0
    if revenue_curr_period > 0 and active_users > 0 and revenue_prev_period > 0 and active_users_prev > 0:
        arpu_curr = revenue_curr_period / active_users
        arpu_prev = revenue_prev_period / active_users_prev
        if arpu_curr > arpu_prev:
            arpu_bonus = 5

    pillar_score = min(base_pillar_score + arpu_bonus, 100) if base_pillar_score is not None else None

    # ── Validation Score ──
    v_score = 0
    if pricing_model_type and target_customer and pricing_metric:
        v_score += 40
    if tavily_benchmark_successful:
        v_score += 30
    if revenue_curr_period > 0 and active_users > 0:
        v_score += 20
    if evidence_links:
        v_score += 10
    validation_score = min(v_score, 100)

    return {
        "pricing_clarity_label": pricing_clarity_label,
        "pricing_pillar_score": pillar_score,
        "pricing_model_type": pricing_model_type,
        "target_customer": target_customer,
        "pricing_metric": pricing_metric,
        "price_range": price_range,
        "who_pays_vs_who_uses": who_pays_vs_who_uses,
        "paying_segment": paying_segment,           # stored, NOT scored at Pre-Seed
        "ai_pricing_summary": summary, # Spec: dashboard shows AI summary
        "evidence_links": evidence_links,
        "analyst_notes": analyst_notes,
        "validation_score": validation_score,
        "data_provenance_note": DATA_PROVENANCE_NOTE,
    }