"""
FFP Smart MVP — Composite Scoring Engine
=========================================
Pillar weights (Pre-Seed):
  USP     = 0.35
  GTM     = 0.15
  PRICING = 0.20
  TECH    = 0.30

UnableToCompute pillar: excluded from sum;
remaining pillar weights renormalised to 1.0.

PartialData multiplier (×0.80) is already applied
inside the GTM pillar — pillar_score enters composite as-is.

Suitability thresholds:
  75–100 → Strong Signal   (Green)
  55–74  → Moderate Signal (Amber)
  35–54  → Weak Signal     (Orange)
  0–34   → Insufficient Signal (Red)
"""

import os
import datetime
from typing import Optional

from config.benchmark_table import PILLAR_WEIGHTS, get_suitability_label
from modules import USP, GTM_PRESEED, Pricing, Tech


# ──────────────────────────────────────────────
# Weight redistribution
# ──────────────────────────────────────────────

def _redistribute_weights(base_weights: dict[str, float], unable: set[str]) -> dict[str, float]:
    """
    Remove UnableToCompute pillars from the weight map and renormalise
    the remaining weights so they sum to exactly 1.0.
    """
    active = {k: v for k, v in base_weights.items() if k not in unable}
    total = sum(active.values())
    if total <= 0:
        return active
    return {k: v / total for k, v in active.items()}


# ──────────────────────────────────────────────
# Main entry point: compute_composite
# ──────────────────────────────────────────────

def compute_composite(
    # ── USP inputs ──
    feature_list: list[str] = None,
    unique_feature_list: list[dict] = None,
    competitors: list[dict] = None,
    tavily_api_key: str = "",
    # ── GTM inputs ──
    startup_domain: str = "",
    market_type: str = "",
    market_description: str = "",
    pitchbook_api_key: str = "",
    pitchbook_data: Optional[dict] = None,
    ga4_property_id: str = "",
    ga4_oauth_token: str = "",
    ga4_data: Optional[dict] = None,
    web_visitors_prev: Optional[int] = None,
    web_visitors_curr: Optional[int] = None,
    social_followers_prev: Optional[int] = None,
    social_followers_curr: Optional[int] = None,
    # ── Pricing inputs ──
    pricing_model_type: Optional[str] = None,
    target_customer: Optional[str] = None,
    pricing_metric: Optional[str] = None,
    price_range: Optional[str] = None,
    who_pays_vs_who_uses: Optional[str] = None,
    paying_segment: Optional[str] = None,
    pricing_evidence_links: Optional[list[str]] = None,
    analyst_notes: Optional[str] = None,
    revenue_curr_period: float = 0.0,
    geographic_focus: str = "",
    # ── Tech inputs ──
    custom_build_level: int = 0,
    patent_status: Optional[str] = None,
    patent_numbers: Optional[list[str]] = None,
    inventor_names: Optional[list[dict]] = None,
    assignee_company_name: Optional[str] = None,
    company_name: str = "",
    tech_evidence_links: Optional[list[str]] = None,
    tech_description: Optional[str] = None,
    run_patent_verification: bool = True,
    # ── Shared API key ──
    gemini_api_key: str = "",
) -> dict:
    """
    Orchestrate all four pillar modules and return a fully composed
    CompositeScore result.

    Returns
    -------
    dict with: composite_score, suitability_label, suitability_colour,
    pillars_computed, pillars_unable_to_compute,
    weight_redistribution_applied, pillar_results{}, computed_at.
    """
    feature_list = feature_list or []
    unique_feature_list = unique_feature_list or []
    competitors = competitors or []

    unable_pillars: set[str] = set()
    pillar_scores: dict[str, Optional[float]] = {}
    pillar_results: dict[str, dict] = {}

    # ── Pillar 1: USP ────────────────────────────────────────────
    usp_out = USP.compute_usp_score(
        feature_list=feature_list,
        unique_feature_list=unique_feature_list,
        competitors=competitors,
        tavily_api_key=tavily_api_key,
        gemini_api_key=gemini_api_key,
        pitchbook_api_key=pitchbook_api_key,
    )
    pillar_results["USP"] = usp_out
    usp_score = usp_out.get("pillar_score")
    if usp_score is None:
        unable_pillars.add("USP")
    pillar_scores["USP"] = usp_score

    # ── Pillar 2: GTM ────────────────────────────────────────────
    gtm_out = GTM_PRESEED.compute_preseed_gtm(
        startup_domain=startup_domain,
        market_type=market_type,
        market_description=market_description,
        pitchbook_api_key=pitchbook_api_key,
        pitchbook_data=pitchbook_data,
        ga4_property_id=ga4_property_id,
        ga4_oauth_token=ga4_oauth_token,
        ga4_data=ga4_data,
        web_visitors_prev=web_visitors_prev,
        web_visitors_curr=web_visitors_curr,
        social_followers_prev=social_followers_prev,
        social_followers_curr=social_followers_curr,
        gemini_api_key=gemini_api_key,
    )
    pillar_results["GTM"] = gtm_out
    gtm_score = gtm_out.get("gtm_pillar_score")
    if gtm_score is None:
        unable_pillars.add("GTM")
    pillar_scores["GTM"] = gtm_score

    # ── Pillar 3: Pricing ────────────────────────────────────────
    pricing_out = Pricing.score_pricing_pipeline(
        pricing_model_type=pricing_model_type,
        target_customer=target_customer,
        pricing_metric=pricing_metric,
        price_range=price_range,
        who_pays_vs_who_uses=who_pays_vs_who_uses,
        paying_segment=paying_segment,
        evidence_links=pricing_evidence_links,
        analyst_notes=analyst_notes,
        revenue_curr_period=revenue_curr_period,
        market_type=market_type,
        geographic_focus=geographic_focus,
        gemini_api_key=gemini_api_key,
    )
    pillar_results["PRICING"] = pricing_out
    pricing_score = pricing_out.get("pricing_pillar_score")
    if pricing_score is None:
        unable_pillars.add("PRICING")
    pillar_scores["PRICING"] = pricing_score

    # ── Pillar 4: Tech ────────────────────────────────────────────
    tech_out = Tech.calculate_technical_build_depth(
        custom_build_level=custom_build_level,
        patent_status=patent_status,
        patent_numbers=patent_numbers,
        inventor_names=inventor_names,
        assignee_company_name=assignee_company_name,
        company_name=company_name,
        evidence_links=tech_evidence_links,
        tech_description=tech_description,
        run_patent_verification=run_patent_verification,
    )
    pillar_results["TECH"] = tech_out
    tech_score = tech_out.get("tech_pillar_score")
    if tech_score is None:
        unable_pillars.add("TECH")
    pillar_scores["TECH"] = tech_score

    # ── Weight redistribution ─────────────────────────────────────
    weight_redistribution_applied = len(unable_pillars) > 0
    effective_weights = _redistribute_weights(PILLAR_WEIGHTS, unable_pillars)

    # ── Composite score ───────────────────────────────────────────
    composite = 0.0
    computed_pillars = []
    for pillar_key, weight in effective_weights.items():
        score = pillar_scores.get(pillar_key)
        if score is not None:
            composite += score * weight
            computed_pillars.append(pillar_key)

    composite_score = round(composite, 2)

    # ── Suitability label ─────────────────────────────────────────
    suitability_label, suitability_colour = get_suitability_label(composite_score)

    return {
        "composite_score": composite_score,
        "suitability_label": suitability_label,
        "suitability_colour": suitability_colour,
        "pillars_computed": computed_pillars,
        "pillars_unable_to_compute": list(unable_pillars),
        "weight_redistribution_applied": weight_redistribution_applied,
        "effective_weights": {k: round(v, 4) for k, v in effective_weights.items()},
        "pillar_results": pillar_results,
        "computed_at": datetime.datetime.utcnow().isoformat() + "Z",
    }


# ──────────────────────────────────────────────
# Legacy alias kept for backward compatibility
# ──────────────────────────────────────────────

def run_scoring_pipeline(company_data: dict) -> dict:
    """
    Thin wrapper around compute_composite() that maps the legacy
    flat company_data dict to the new keyword-argument interface.
    Used by main.py / FINAL_SCORE.py.
    """
    return compute_composite(
        # USP
        feature_list=company_data.get("feature_list", []),
        unique_feature_list=company_data.get("unique_feature_list", []),
        competitors=company_data.get("competitors", []),
        tavily_api_key=os.getenv("TAVILY_API_KEY", ""),
        # GTM
        startup_domain=company_data.get("startup_domain", ""),
        market_type=company_data.get("market_type", ""),
        market_description=company_data.get("market_description", ""),
        pitchbook_api_key=os.getenv("PITCHBOOK_API_KEY", ""),
        web_visitors_prev=company_data.get("web_visitors_prev"),
        web_visitors_curr=company_data.get("web_visitors_curr"),
        social_followers_prev=company_data.get("social_followers_prev"),
        social_followers_curr=company_data.get("social_followers_curr"),
        # Pricing
        pricing_model_type=company_data.get("pricing_model_type"),
        target_customer=company_data.get("target_customer"),
        pricing_metric=company_data.get("pricing_metric"),
        price_range=company_data.get("price_range"),
        who_pays_vs_who_uses=company_data.get("who_pays_vs_who_uses"),
        paying_segment=company_data.get("paying_segment"),
        pricing_evidence_links=company_data.get("pricing_evidence_links"),
        analyst_notes=company_data.get("analyst_notes"),
        revenue_curr_period=company_data.get("total_revenue", 0.0),
        geographic_focus=company_data.get("geographic_focus", ""),
        # Tech
        custom_build_level=company_data.get("custom_build_level", 0),
        patent_status=company_data.get("patent_status"),
        patent_numbers=company_data.get("patent_numbers"),
        inventor_names=company_data.get("inventor_names"),
        assignee_company_name=company_data.get("assignee_company_name"),
        company_name=company_data.get("company_name", ""),
        tech_evidence_links=company_data.get("tech_evidence_links"),
        tech_description=company_data.get("tech_description"),
        run_patent_verification=company_data.get("run_patent_verification", True),
        # Shared
        gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
    )
