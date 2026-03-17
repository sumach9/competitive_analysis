"""
FFP Smart MVP — Pillar 2: GTM Strategy — Audience Growth Rate
=============================================================
Weight: 15% of composite score (Pre-Seed)

Path A (BrightData):  webGrowthRate, socialGrowthRate, percentiles → z-scores via invNorm
Path B (GA4 + GSC):  Month-over-month sessions / followers → z-scores via Static Benchmark Table
"""

import os
import requests
import re
from typing import Optional
from rapidfuzz import process

from config.benchmark_table import BENCHMARK_TABLE, MARKET_TYPE_LABELS


# ──────────────────────────────────────────────
# Market type: label match (RapidFuzz)
# ──────────────────────────────────────────────
def _match_market_type(market_description: str) -> str:
    """
    RapidFuzz fuzzy match of market description against benchmarks.
    Uses score >= 70 fallback to 'Other'.
    """
    if not market_description:
        return "Other"
        
    match, score, index = process.extractOne(market_description, MARKET_TYPE_LABELS)
    if score >= 70:
        return match
    return "Other"


# ──────────────────────────────────────────────
# Path B — GA4 Data API
# ──────────────────────────────────────────────
def _fetch_ga4_sessions(property_id: str, oauth_token: str) -> Optional[dict]:
    """
    Pull two months of GA4 session data via OAuth.
    Returns {"web_visitors_prev": int, "web_visitors_curr": int} or None.
    """
    if not property_id or not oauth_token:
        return None
    try:
        import datetime
        today = datetime.date.today()
        curr_start = today.replace(day=1)
        prev_end = curr_start - datetime.timedelta(days=1)
        prev_start = prev_end.replace(day=1)

        body = {
            "dateRanges": [
                {"startDate": str(prev_start), "endDate": str(prev_end)},
                {"startDate": str(curr_start), "endDate": str(today)},
            ],
            "dimensions": [{"name": "yearMonth"}],
            "metrics": [{"name": "sessions"}],
        }
        resp = requests.post(
            f"https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:runReport",
            headers={
                "Authorization": f"Bearer {oauth_token}",
                "Content-Type": "application/json",
            },
            json=body,
            timeout=15,
        )
        resp.raise_for_status()
        rows = resp.json().get("rows", [])
        sessions = [int(r["metricValues"][0]["value"]) for r in rows]
        if len(sessions) >= 2:
            return {"web_visitors_prev": sessions[0], "web_visitors_curr": sessions[1]}
        return None
    except Exception:
        return None


# ──────────────────────────────────────────────
# Signal bucket → pillar score
# ──────────────────────────────────────────────
def _signal_bucket(agr: float, bench: dict) -> tuple[str, int]:
    if agr < 0:
        return "Concerning", 15
    elif agr >= bench["benchmark_max"]:
        return "Strong", 90
    elif agr >= bench["benchmark_mean"]:
        return "Positive", 70
    elif agr >= bench["benchmark_min"]:
        return "Neutral", 50
    else:
        return "Weak", 30


# ──────────────────────────────────────────────
# Main Entry Point
# ──────────────────────────────────────────────
def compute_preseed_gtm(
    startup_domain: str = "",
    market_type: str = "",
    market_description: str = "",
    # GA4
    ga4_property_id: str = "",
    ga4_oauth_token: str = "",
    ga4_data: Optional[dict] = None,          # inject directly or pass manual
    # Manual fallback
    web_visitors_prev: Optional[int] = None,
    web_visitors_curr: Optional[int] = None,
    # Social (manual entry)
    social_followers_prev: Optional[int] = None,
    social_followers_curr: Optional[int] = None,
    has_social_screenshot: bool = False,
) -> dict:
    """
    Compute GTM Audience Growth Rate (AGR) pillar.
    """

    compute_path = "GA4/Manual"
    web_growth_rate: Optional[float] = None
    social_growth_rate: Optional[float] = None
    status_label = "OK"
    confidence_level = "HIGH"
    benchmark_source = "Static Benchmark Table"
    flags: list[str] = []

    # Try GA4 API first
    ga4 = ga4_data
    if ga4 is None and ga4_property_id and ga4_oauth_token:
        ga4 = _fetch_ga4_sessions(ga4_property_id, ga4_oauth_token)
        if ga4:
            flags.append("WEB_DATA_GA4_API")
            benchmark_source = "GA4 API"

    # Manual fallback if GA4 OAuth declined or not provided
    if ga4 is None:
        if web_visitors_prev is not None and web_visitors_curr is not None:
            ga4 = {
                "web_visitors_prev": web_visitors_prev,
                "web_visitors_curr": web_visitors_curr,
            }
            flags.append("WEB_DATA_MANUAL")
            confidence_level = "LOW"
            benchmark_source = "Founder-submitted manual entry"
        else:
            ga4 = {}

    wv_prev = ga4.get("web_visitors_prev")
    wv_curr = ga4.get("web_visitors_curr")

    # InvalidBaselinePrevZero
    if wv_prev == 0:
        flags.append("InvalidBaselinePrevZero_web")
        wv_prev = None
    if social_followers_prev == 0:
        flags.append("InvalidBaselinePrevZero_social")
        social_followers_prev = None

    if wv_prev is not None and wv_curr is not None and wv_prev > 0:
        web_growth_rate = (wv_curr - wv_prev) / wv_prev * 100
    if social_followers_prev is not None and social_followers_curr is not None and social_followers_prev > 0:
        social_growth_rate = (social_followers_curr - social_followers_prev) / social_followers_prev * 100

    # Match market_type to benchmark table
    resolved_type = market_type if market_type in BENCHMARK_TABLE else None
    if resolved_type is None and market_description:
        resolved_type = _match_market_type(market_description)
        flags.append(f"MARKET_TYPE_LABEL_MATCHED:{resolved_type}")
    if resolved_type is None:
        resolved_type = "Other"
    matched_market_type = resolved_type

    bm = BENCHMARK_TABLE[resolved_type]

    # ── UnableToCompute guard ───────────────────────────────────
    if web_growth_rate is None and social_growth_rate is None:
        return {
            "AGR_raw": None,
            "gtm_signal_bucket": "UnableToCompute",
            "gtm_pillar_score": None,
            "compute_path": compute_path,
            "confidence_level": "LOW",
            "status_label": "UnableToCompute",
            "validation_score": 0,
            "web_growth_rate": None,
            "social_growth_rate": None,
            "benchmark_source": benchmark_source,
            "matched_market_type": matched_market_type,
            "flags": flags,
            "dashboard_note": "Unable to compute due to insufficient data-points.",
        }

    # ── PartialData: single channel ─────────────────────────────
    partial = False
    if web_growth_rate is None or social_growth_rate is None:
        partial = True
        status_label = "PartialData"
        confidence_level = "MEDIUM"

    # ── AGR_raw ─────────────────────────────────────────────────
    rates = [r for r in [web_growth_rate, social_growth_rate] if r is not None]
    AGR_raw = round(sum(rates) / len(rates), 2) if rates else None

    # ── NeedsHumanReview ───────────────────────────────────────
    if AGR_raw is not None and abs(AGR_raw) > 300:
        status_label = "NeedsHumanReview"
        confidence_level = "LOW"
        flags.append("OUTLIER_DETECTED")

    # ── Signal bucket ───────────────────────────────────────────
    bucket, raw_pillar_score = _signal_bucket(AGR_raw or 0.0, bm)

    # ── PartialData multiplier ──────────────────────────────────
    pillar_score = round(raw_pillar_score * 0.80) if partial else raw_pillar_score

    # ── Social data provenance flag ─────────────────────────────
    if social_followers_prev is None and social_followers_curr is None:
        flags.append("SOCIAL_DATA_MISSING")

    # ── Validation Score ──
    v_score = 0
    if ga4_oauth_token:
        v_score += 40
    if has_social_screenshot:
        v_score += 30
    if web_growth_rate is not None and social_growth_rate is not None:
        v_score += 20
    if AGR_raw is not None and abs(AGR_raw) <= 300:
        v_score += 10
    validation_score = min(v_score, 100)

    return {
        "AGR_raw": AGR_raw,
        "web_growth_rate": round(web_growth_rate, 2) if web_growth_rate is not None else None,
        "social_growth_rate": round(social_growth_rate, 2) if social_growth_rate is not None else None,
        "gtm_signal_bucket": bucket,
        "gtm_pillar_score": pillar_score,
        "compute_path": compute_path,
        "benchmark_source": benchmark_source,
        "matched_market_type": matched_market_type,
        "confidence_level": confidence_level,
        "status_label": status_label,
        "validation_score": validation_score,
        "flags": flags,
        "dashboard_note": None,
    }